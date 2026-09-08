from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission: Allow read-only access for all users,
    but only the owner can modify the object.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner == request.user

class IsAgentOrAuthenticated(BasePermission):
    """
    Custom permission: Allow access either via JWT (authenticated user)
    or via API Key (agent).
    """
    def has_permission(self, request, view):
        # Check if user is authenticated via JWT
        if request.user and request.user.is_authenticated:
            return True
        
        # Check for API Key in headers
        api_key = request.headers.get('X-API-Key')
        if api_key:
            from .models import Application
            try:
                app = Application.objects.get(api_key=api_key, is_active=True)
                request._agent_app = app  # Store for later use
                return True
            except Application.DoesNotExist:
                return False
        return False