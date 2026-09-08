"""
Celery configuration for the APM project.
This module defines the Celery application instance and configures periodic tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
# This allows Celery to use the same settings as the Django project.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Create the Celery application instance.
# The name 'project' matches the Django project name.
app = Celery('project')

# Load task modules from all registered Django app configs.
# This means Celery will automatically discover tasks in each app's 'tasks.py'.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps that have a 'tasks.py' file.
app.autodiscover_tasks()

# Configure periodic tasks (Beat schedule).
# These tasks will run automatically at specified intervals.
app.conf.beat_schedule = {
    # Task 1: Calculate average response time for each application every 5 minutes.
    'calculate-averages-every-5-minutes': {
        'task': 'monitor.tasks.calculate_averages',
        'schedule': crontab(minute='*/5'),  # Runs every 5 minutes.
    },
    # Task 2: Check metric thresholds and create alerts every minute.
    'check-thresholds-every-minute': {
        'task': 'monitor.tasks.check_thresholds',
        'schedule': crontab(minute='*'),  # Runs every minute.
    },
    # Task 3: Delete old metrics older than 30 days daily at midnight.
    'clean-old-data-daily': {
        'task': 'monitor.tasks.clean_old_data',
        'schedule': crontab(hour=0, minute=0),  # Runs daily at 00:00.
    },
    # Task 4: Generate AI forecast for all applications every hour.
    'generate-forecast-hourly': {
        'task': 'monitor.tasks.generate_forecast_task',
        'schedule': crontab(minute='0'),  # Runs at the beginning of every hour.
    },
}

# Optional: Define a debug task to test if Celery is working.
@app.task(bind=True)
def debug_task(self):
    """
    A simple debug task that prints the request details.
    Useful for testing if Celery is configured correctly.
    """
    print(f'Request: {self.request!r}')