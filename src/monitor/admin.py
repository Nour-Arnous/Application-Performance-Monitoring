from django.contrib import admin
from .models import Metric

# Register your models here.

admin.site.site_header = 'Application Performance Monitoring - APM'

class MetricAdmin(admin.ModelAdmin):
    list_display = ('application_name', 'response_time', 'request_count', 'error_count', 'timestamp')
    search_fields = ['application_name']
    list_filter = ('application_name', 'response_time', 'request_count', 'error_count')

admin.site.register(Metric, MetricAdmin)