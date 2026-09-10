# ASGI config for project project.

# This is the entry point for ASGI (Asynchronous Server Gateway Interface) 
# servers like Daphne. Unlike WSGI (which is synchronous), ASGI supports
# asynchronous protocols like WebSocket, which I use for real-time updates in this project.
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from monitor.routing import websocket_urlpatterns

# I set the Django settings module so that ASGI can access all the
# project settings (like database connections, app configurations, etc.)
# This is the same as what I do in wsgi.py, but for asynchronous mode.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# This is the main application object that ASGI servers (like Daphne)
# will call to handle incoming requests. It's a ProtocolTypeRouter which
# routes different types of protocols to different handlers.
application = ProtocolTypeRouter({
    # For regular HTTP requests, I use Django's standard ASGI application.
    # This handles all normal web requests like views, APIs, static files, etc.
    "http": get_asgi_application(),

    # For WebSocket connections, I use a custom routing system.
    # I wrap it with AuthMiddlewareStack so that I can access the logged-in
    # user's information inside the WebSocket consumer. This is important
    # for authentication and authorization of WebSocket connections.
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns) # I defined these routes in monitor/routing.py
    ),
})