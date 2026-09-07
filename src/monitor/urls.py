from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  home, dashboard, login_view, logout_view, register_view, profile_view, MetricViewSet

router = DefaultRouter()
router.register(r'metrics', MetricViewSet)

urlpatterns = [
    path('', home, name='home'),  
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('api/', include(router.urls)),
]