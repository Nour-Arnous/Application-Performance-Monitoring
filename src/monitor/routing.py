from django.urls import re_path
from . import consumers

# WebSocket URL patterns
websocket_urlpatterns = [
    # I set up this route to handle real‑time WebSocket connections.
    # The path 'ws/metrics/' is where the frontend JavaScript connects.
    # When a user opens the dashboard, the browser creates a WebSocket
    # connection here to receive live metric updates without refreshing
    # the page. The `as_asgi()` method is required to convert the
    # consumer class into an ASGI application that Django Channels can use.
    re_path(r'ws/metrics/$', consumers.MetricConsumer.as_asgi()),
]