import uuid
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.decorators import action

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Metric, Application, Alert
from .serializers import MetricSerializer, ApplicationSerializer, AlertSerializer
from .permissions import IsOwnerOrReadOnly, IsAgentOrAuthenticated
from .forecast import generate_forecast_for_app, get_cached_forecast

from django.core.paginator import Paginator


# ============================================================
# HTML Views (Session-based authentication)
# ============================================================

def home(request):
    """
    Home page view.
    Admins see all applications; regular users see only their own.
    """
    user_apps = []
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            user_apps = Application.objects.all()
        else:
            user_apps = Application.objects.filter(owner=request.user)
            
    return render(request, 'monitor/home.html', {'applications': user_apps})

@login_required
def dashboard(request):
    """
    Dashboard view showing core application performance metrics and charts.
    Alerts logic removed to streamline the dashboard layout.
    """
    if request.user.is_staff or request.user.is_superuser:
        user_apps = Application.objects.all()
        metrics = Metric.objects.all().order_by('-timestamp')[:30]
    else:
        user_apps = Application.objects.filter(owner=request.user)
        metrics = Metric.objects.filter(application__in=user_apps).order_by('-timestamp')[:30]

    context = {
        'applications': user_apps,
        'metrics': metrics,
        'apps_count': user_apps.count(),
    }
    return render(request, 'monitor/dashboard.html', context)

def register_view(request):
    """User registration view."""
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
    """User login view."""
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
    """User profile view with summary statistics."""
    if request.user.is_staff or request.user.is_superuser:
        applications_count = Application.objects.all().count()
        alerts_unread = Alert.objects.filter(is_read=False).count()
    else:
        applications_count = Application.objects.filter(owner=request.user).count()
        alerts_unread = Alert.objects.filter(
            application__owner=request.user,
            is_read=False
        ).count()
    
    context = {
        'applications_count': applications_count,
        'alerts_unread': alerts_unread,
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def manage_apps(request):
    """Manage and create applications with auto-generated API Keys."""
    if request.method == 'POST':
        app_name = request.POST.get('name')
        description = request.POST.get('description', '')

        if app_name:
            generated_api_key = uuid.uuid4().hex
            Application.objects.create(
                owner=request.user,
                name=app_name,
                description=description,
                api_key=generated_api_key
            )
            messages.success(request, f"Application '{app_name}' created successfully!")
            return redirect('manage_apps')
        else:
            messages.error(request, "Application name is required.")

    if request.user.is_staff or request.user.is_superuser:
        user_apps = Application.objects.all()
    else:
        user_apps = Application.objects.filter(owner=request.user)

    context = {
        'applications': user_apps,
    }
    return render(request, 'monitor/manage_apps.html', context)


@login_required
def alerts_list_view(request):
    """
    Display a paginated list of alerts with filtering capabilities
    by severity, read status, and application.
    """
    # Fetch base queryset according to user roles
    if request.user.is_staff or request.user.is_superuser:
        alerts = Alert.objects.select_related('application').all()
    else:
        alerts = Alert.objects.select_related('application').filter(application__owner=request.user)

    # Get filter values from GET parameters
    severity_filter = request.GET.get('severity', '')
    status_filter = request.GET.get('status', '')
    app_filter = request.GET.get('app_id', '')

    # Apply filters
    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)

    if status_filter == 'unread':
        alerts = alerts.filter(is_read=False)
    elif status_filter == 'read':
        alerts = alerts.filter(is_read=True)

    if app_filter:
        alerts = alerts.filter(application_id=app_filter)

    # Paginate results (10 alerts per page)
    paginator = Paginator(alerts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'applications': Application.objects.filter(owner=request.user) if not request.user.is_staff else Application.objects.all(),
        'selected_severity': severity_filter,
        'selected_status': status_filter,
        'selected_app': app_filter,
    }
    return render(request, 'monitor/alerts_list.html', context)


@login_required
def toggle_alert_status(request, alert_id):
    """
    Toggle the read/unread status of an alert.
    """
    alert = get_object_or_404(Alert, id=alert_id)
    alert.is_read = not alert.is_read
    alert.save()
    
    return redirect(request.META.get('HTTP_REFERER', 'alerts_list'))


# ============================================================
# API Views (JWT & API Key based authentication)
# ============================================================

class ApplicationViewSet(viewsets.ModelViewSet):
    """API ViewSet for managing Applications."""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Application.objects.all()
        return Application.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def forecast(self, request, pk=None):
        """Generate or retrieve cached forecast for an application."""
        app = self.get_object()
        
        forecast = get_cached_forecast(app.id)
        if not forecast:
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
    """API ViewSet for managing metrics via JWT or API Key."""
    serializer_class = MetricSerializer
    permission_classes = [IsAgentOrAuthenticated]

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            if self.request.user.is_staff or self.request.user.is_superuser:
                queryset = Metric.objects.all()
            else:
                user_apps = Application.objects.filter(owner=self.request.user)
                queryset = Metric.objects.filter(application__in=user_apps)
        elif hasattr(self.request, '_agent_app'):
            queryset = Metric.objects.filter(application=self.request._agent_app)
        else:
            return Metric.objects.none()

        hours_param = self.request.query_params.get('hours', None)
        if hours_param is not None:
            try:
                hours = int(hours_param)
                if hours > 0:
                    cutoff_time = timezone.now() - timedelta(hours=hours)
                    queryset = queryset.filter(timestamp__gte=cutoff_time)
            except ValueError:
                pass

        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        app_id = self.request.data.get('application')
        if not app_id:
            raise ValidationError({"application": "This field is required."})
        
        try:
            if self.request.user and self.request.user.is_authenticated:
                app = Application.objects.get(id=app_id, owner=self.request.user)
            elif hasattr(self.request, '_agent_app'):
                app = self.request._agent_app
            else:
                raise PermissionDenied("Authentication credentials were not provided.")
        except Application.DoesNotExist:
            raise ValidationError({"application": "Application not found or access denied."})
        
        metric = serializer.save(application=app)
        
        # Broadcast metric update via WebSocket channels
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "metrics_group",
                {
                    'type': 'metric_update',
                    'data': MetricSerializer(metric).data
                }
            )
        except Exception:
            pass


class AlertViewSet(viewsets.ModelViewSet):
    """API ViewSet for managing system alerts."""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Alert.objects.all()
        return Alert.objects.filter(application__owner=self.request.user)

    def perform_create(self, serializer):
        app_id = self.request.data.get('application')
        if not app_id:
            raise ValidationError({"application": "This field is required."})
            
        try:
            app = Application.objects.get(id=app_id, owner=self.request.user)
            serializer.save(application=app)
        except Application.DoesNotExist:
            raise ValidationError({"application": "Application not found or access denied."})