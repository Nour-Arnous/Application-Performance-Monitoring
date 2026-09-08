"""
Celery tasks for APM monitoring.
These tasks run periodically to perform background operations.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from .models import Metric, Application, Alert
import logging

logger = logging.getLogger(__name__)


@shared_task
def calculate_averages():
    """
    Calculate average response time for each application over the last 24 hours.
    This task runs every 5 minutes.
    """
    apps = Application.objects.filter(is_active=True)
    for app in apps:
        metrics = Metric.objects.filter(
            application=app,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        )
        if metrics.exists():
            avg = metrics.aggregate(avg=Avg('response_time'))['avg']
            logger.info(f"Average for {app.name}: {avg:.2f}s")
    return f"Calculated averages for {apps.count()} apps."


@shared_task
def check_thresholds():
    """
    Check all active thresholds and create alerts if metrics exceed limits.
    This task runs every minute.
    """
    apps = Application.objects.filter(is_active=True)
    alerts_created = 0

    for app in apps:
        latest = Metric.objects.filter(application=app).order_by('-timestamp').first()
        if not latest:
            continue

        # Check response time threshold (e.g., 3 seconds)
        if latest.response_time > 3.0:
            Alert.objects.create(
                application=app,
                message=f"High response time: {latest.response_time:.2f}s",
                severity='danger',
                metric_value=latest.response_time,
                threshold=3.0
            )
            alerts_created += 1

        # Check error count threshold (e.g., 5 errors)
        if latest.error_count > 5:
            Alert.objects.create(
                application=app,
                message=f"High error count: {latest.error_count} errors",
                severity='danger',
                metric_value=latest.error_count,
                threshold=5
            )
            alerts_created += 1

    logger.info(f"Created {alerts_created} new alerts.")
    return f"Checked thresholds. Created {alerts_created} alerts."


@shared_task
def clean_old_data():
    """
    Delete metrics older than 30 days to save database space.
    This task runs daily at midnight.
    """
    cutoff = timezone.now() - timedelta(days=30)
    old_metrics = Metric.objects.filter(timestamp__lt=cutoff)
    count = old_metrics.count()
    old_metrics.delete()
    logger.info(f"Deleted {count} old metric records.")
    return f"Deleted {count} old metric records."


@shared_task
def generate_forecast_task():
    """
    Generate AI forecast for all active applications.
    This task runs every hour.
    """
    from .forecast import generate_forecast_for_app  # Local import to avoid circular dependency
    
    apps = Application.objects.filter(is_active=True)
    results = []
    for app in apps:
        result = generate_forecast_for_app(app.id)
        if result:
            results.append(f"App {app.id}: success")
        else:
            results.append(f"App {app.id}: failed (not enough data)")
    
    logger.info(f"Forecast generated for {len(apps)} apps.")
    return {"message": "Forecast task completed.", "details": results}