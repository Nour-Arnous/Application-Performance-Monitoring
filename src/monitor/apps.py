from django.apps import AppConfig

class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    
    def ready(self):
        from .views import start_forecast_scheduler
        start_forecast_scheduler()