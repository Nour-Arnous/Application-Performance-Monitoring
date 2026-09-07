from django.db import models
from django.contrib.auth.models import User

class Metric(models.Model):
    application_name = models.CharField(max_length=100)
    response_time = models.FloatField()
    request_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application_name} - {self.response_time} seconds"



class Application(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('info', 'informantion'),
        ('warning', 'warnings'),
        ('danger', 'dangers'),
        ('success', 'success'),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    metric_value = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_severity_display()} - {self.application.name}"