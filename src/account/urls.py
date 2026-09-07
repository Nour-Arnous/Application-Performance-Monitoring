from django.urls import path
from .views import RegisterView, LoginView, ProfileView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='api_register'),
    path('login/', LoginView.as_view(), name='api_login'),
    path('profile/', ProfileView.as_view(), name='api_profile'),
    path('logout/', LogoutView.as_view(), name='api_logout'),
]