# I import the Celery app from celery.py and rename it to celery_app
# so that it becomes available at the project level. This is the
# standard way to set up Celery with Django.
#  Without this, Celery would not be able to discover the tasks when Django starts.
from .celery import app as celery_app
# I define __all__ to specify the public interface of this package.
# This ensures that if someone imports from this module using
# "from project import *", only celery_app will be exposed.
# It also helps to keep the code clean and document what is actually intended to be used from this package.
__all__ = ('celery_app',)