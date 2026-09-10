# Celery tasks for APM monitoring.
# These tasks run periodically to perform background operations.
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from .models import Metric, Application, Alert
import logging

logger = logging.getLogger(__name__)
@shared_task
def calculate_averages():
    # I wrote this task to automatically calculate the average response time
    # for each active application over the last 24 hours. The result is logged
    # so I can monitor performance trends over time. I chose 24 hours because
    # it gives a good balance between recent data and meaningful averages.
    # Running it every 5 minutes ensures the data stays fresh without overloading the database
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
    # This is my alerting system. It runs every minute and checks the latest
    # metric for each active application. If the response time exceeds 3 seconds
    # or the error count goes above 5, it automatically creates an alert.
    # I chose these thresholds because they are common indicators of performance
    # issues in web applications. The alerts are stored in the database so they
    # can be displayed on the dashboard and reviewed by the user.
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
    # I added this task to prevent the database from growing too large over time.
    # Metrics older than 30 days are no longer needed for real-time monitoring
    # or forecasting, so I delete them automatically every night. This keeps
    # the database size manageable and query performance fast.
    cutoff = timezone.now() - timedelta(days=30)
    old_metrics = Metric.objects.filter(timestamp__lt=cutoff)
    count = old_metrics.count()
    old_metrics.delete()
    logger.info(f"Deleted {count} old metric records.")
    return f"Deleted {count} old metric records."


@shared_task
def generate_forecast_task():
    # This task generates a Prophet forecast for every active application
    # once every hour. I decided to run it hourly so that the forecast data
    # stays up-to-date without putting too much load on the server (Prophet
    # can be computationally expensive). I imported forecast locally to avoid
    # circular dependency issues between tasks.py and forecast.py.
    from .forecast import generate_forecast_for_app  # Local import to avoid circular dependency
    
    apps = Application.objects.filter(is_active=True)
    results = []
    for app in apps:
        result = generate_forecast_for_app(app.id)
        if result:
            results.append(f"App {app.id}: success")
        else:
            # This usually means there isn't enough historical data yet
            results.append(f"App {app.id}: failed (not enough data)")
    
    logger.info(f"Forecast generated for {len(apps)} apps.")
    return {"message": "Forecast task completed.", "details": results}