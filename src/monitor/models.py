from django.db import models
from django.contrib.auth.models import User
import secrets
from django.utils import timezone


class Application(models.Model):
    """
    Application model represents a monitored application.
    Each application belongs to a user (owner) and has a unique API key
    that agents use to send metrics.
    """
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # API Key for the agent (external applications).
    # I generate it automatically in save() if it's not set.
    api_key = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
        null=True
    )

    def save(self, *args, **kwargs):
        """Auto-generate a secure API key the first time the app is saved."""
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Metric(models.Model):
    """
    Metric model stores a single performance measurement for an application.
    This includes response time, request count, and error count.
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    response_time = models.FloatField()
    request_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.name} - {self.response_time}s"


class Alert(models.Model):
    """
    Alert model stores notifications that are created automatically
    by Celery when a metric exceeds a threshold.
    """
    # Severity choices must match the values used in tasks.py and the templates.
    # I use 'danger' instead of 'critical' to align with Bootstrap's alert classes.
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
        ('success', 'Success'),
    ]

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    message = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='warning'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    # These two fields store the actual value that triggered the alert
    # and the threshold that was exceeded. They are used by the Celery
    # task 'check_thresholds' and displayed on the alerts page.
    metric_value = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.application.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"