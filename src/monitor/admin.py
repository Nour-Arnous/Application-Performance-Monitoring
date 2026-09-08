from django.contrib import admin
from .models import Application, Metric, Alert

# Register your models here.

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['api_key', 'created_at']

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    # ✅ Changed from 'application_name' to 'application'
    list_display = ['id', 'application', 'response_time', 'request_count', 'error_count', 'timestamp']
    list_filter = ['application', 'timestamp']
    search_fields = ['application__name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'application', 'severity', 'is_read', 'created_at']
    list_filter = ['severity', 'is_read', 'created_at']
    search_fields = ['application__name', 'message']
    readonly_fields = ['created_at']
