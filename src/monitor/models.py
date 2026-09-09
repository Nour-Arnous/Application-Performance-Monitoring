from django.db import models
from django.contrib.auth.models import User
import secrets
from django.utils import timezone

class Application(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # API Key for agent (external applications)
    api_key = models.CharField(max_length=50, unique=True, blank=True, editable=False, null=True)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Metric(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='metrics')
    response_time = models.FloatField()
    request_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.name} - {self.response_time}s"


class Alert(models.Model):
    # Severity Choice Definitions
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('WARNING', 'Warning'),
        ('INFO', 'Info'),
    ]

    application = models.ForeignKey('Application', on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='WARNING')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.application.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"