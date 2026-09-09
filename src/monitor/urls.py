from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    home, dashboard, login_view, logout_view, manage_apps, register_view, profile_view,
    ApplicationViewSet, MetricViewSet, AlertViewSet,
    alerts_list_view, toggle_alert_status
)

# API Router configuration
router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='api-applications')
router.register(r'metrics', MetricViewSet, basename='api-metrics')
router.register(r'alerts', AlertViewSet, basename='api-alerts')

# URL patterns
urlpatterns = [
    # HTML Views (Session-based)
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('apps/', manage_apps, name='manage_apps'),
    
    # API Endpoints (Prefix: /api/)
    path('api/', include(router.urls)),
    
    # Alert Management Pages
    path('alerts/', alerts_list_view, name='alerts_list'),
    path('alerts/<int:alert_id>/toggle/', toggle_alert_status, name='toggle_alert_status'),
]