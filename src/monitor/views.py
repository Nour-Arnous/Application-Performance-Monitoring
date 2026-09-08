from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import Metric, Application, Alert
from .serializers import MetricSerializer, ApplicationSerializer, AlertSerializer
from .permissions import IsOwnerOrReadOnly, IsAgentOrAuthenticated
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.decorators import action
from .forecast import generate_forecast_for_app, get_cached_forecast
import schedule
import time
from threading import Thread
from django.utils import timezone
from datetime import timedelta

# ============================================================
# HTML Views (Session-based authentication)
# ============================================================

def home(request):
    """Home page view."""
    return render(request, 'monitor/home.html')

@login_required
def dashboard(request):
    """
    Dashboard view - shows metrics and alerts for the logged-in user only.
    """
    user_apps = Application.objects.filter(owner=request.user)
    metrics = Metric.objects.filter(application__in=user_apps).order_by('-timestamp')[:30]
    alerts = Alert.objects.filter(application__in=user_apps, is_read=False)
    context = {
        'applications': user_apps,
        'metrics': metrics,
        'alerts': alerts,
    }
    return render(request, 'monitor/dashboard.html', context)

def register_view(request):
    """User registration view using Django's UserCreationForm."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Registration successful, {user.username}. Please log in.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    return render(request, 'authentication/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome, {username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'authentication/login.html')
    return render(request, 'authentication/login.html')

def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    """
    User profile view showing statistics for the logged-in user.
    """
    applications_count = Application.objects.filter(owner=request.user).count()
    alerts_unread = Alert.objects.filter(application__owner=request.user, is_read=False).count()
    context = {
        'applications_count': applications_count,
        'alerts_unread': alerts_unread,
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def manage_apps(request):
    """
    Display all applications owned by the logged-in user,
    along with their ID and API Key for easy copy-pasting.
    """
    user_apps = Application.objects.filter(owner=request.user)
    context = {
        'applications': user_apps,
    }
    return render(request, 'monitor/manage_apps.html', context)

# ============================================================
# API Views (JWT-based authentication)
# ============================================================

class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing applications.
    Users can only see and modify their own applications.
    """
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Application.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def forecast(self, request, pk=None):
        """Generate or retrieve forecast for an application."""
        app = self.get_object()
        
        # Try to get cached forecast
        forecast = get_cached_forecast(app.id)
        
        if not forecast:
            # Generate new forecast
            forecast = generate_forecast_for_app(app.id)
            if not forecast:
                return Response(
                    {"error": "Not enough data to generate forecast."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response({
            "application_id": app.id,
            "application_name": app.name,
            "forecast": forecast
        })

class MetricViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing metrics.
    Accessible via JWT (authenticated user) or API Key (agent).
    """
    serializer_class = MetricSerializer
    permission_classes = [IsAgentOrAuthenticated]

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            user_apps = Application.objects.filter(owner=self.request.user)
            return Metric.objects.filter(application__in=user_apps)
        elif hasattr(self.request, '_agent_app'):
            return Metric.objects.filter(application=self.request._agent_app)
        return Metric.objects.none()
    
        # Time filter
        hours_param = self.request.query_params.get('hours', None)
        if hours_param:
            try:
                hours = int(hours_param)
                if hours <= 0:
                    raise ValidationError("Hours must be a positive integer.")
                cutoff_time = timezone.now() - timedelta(hours=hours)
                queryset = queryset.filter(timestamp__gte=cutoff_time)
            except ValueError:
                raise ValidationError("Invalid hours parameter. Must be an integer.")

        # The last first 
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        # Get application ID from request data
        app_id = self.request.data.get('application')
        if not app_id:
            raise ValidationError({"application": "This field is required."})
        
        # Check if the application belongs to the authenticated user or agent
        if self.request.user and self.request.user.is_authenticated:
            app = Application.objects.get(id=app_id, owner=self.request.user)
        elif hasattr(self.request, '_agent_app'):
            app = self.request._agent_app
        else:
            raise PermissionError("You don't have permission to add metrics to this application.")
        
        # Save the metric
        metric = serializer.save(application=app)
        
        # Send metric via WebSocket for real-time updates
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "metrics_group",
                {
                    'type': 'metric_update',
                    'data': MetricSerializer(metric).data
                }
            )
        except Exception as e:
            # WebSocket might not be configured, but API should still work
            pass


class AlertViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing alerts.
    Users can only see alerts for their own applications.
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(application__owner=self.request.user)

    def perform_create(self, serializer):
        app_id = self.request.data.get('application')
        if app_id:
            app = Application.objects.get(id=app_id, owner=self.request.user)
            serializer.save(application=app)

# For forecast
def schedule_forecast_updates():
    """Run forecast updates every hour."""
    from .models import Application
    
    def update_all_forecasts():
        for app in Application.objects.all():
            generate_forecast_for_app(app.id)
    
    schedule.every(1).hours.do(update_all_forecasts)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start in background thread when server starts
def start_forecast_scheduler():
    thread = Thread(target=schedule_forecast_updates, daemon=True)
    thread.start()