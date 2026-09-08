from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    home, dashboard, login_view, logout_view, manage_apps, register_view, profile_view,
    ApplicationViewSet, MetricViewSet, AlertViewSet
)

# API Router
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
    
    # API Views (JWT-based)
    path('api/', include(router.urls)),
]