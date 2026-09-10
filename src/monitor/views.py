# Views for the monitor application.
# Includes HTML views (session-based authentication) and API views (JWT-based authentication).

import uuid
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User  # I added this to check duplicate emails
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


# =====================================================================
# HTML VIEWS (Session-based authentication)
# These views render HTML pages and use Django's session-based
# authentication (login_required decorator).
# =====================================================================

def home(request):
    """
    Home page view.
    Admins see all applications; regular users see only their own.
    I display the list of applications on the home page so users can quickly
    see which apps they have. Admins see everything, which is useful for
    monitoring the whole system at a glance.
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
    I decided to keep the dashboard focused on metrics and charts, and moved
    alerts to a separate page. This makes the dashboard cleaner and faster
    to load, especially when there are many metrics.
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
    """
    User registration view (HTML form).
    I'm using Django's built-in UserCreationForm here because it handles
    password validation and user creation automatically. However, that form
    does NOT check for duplicate emails, so I added a manual check below.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Extract the email from POST data
            email = request.POST.get('email', '').strip()

            # Check if the email is already used by another user.
            # I do this because Django's default User model doesn't enforce
            # unique emails, so we need to check manually. I use iexact to
            # make the check case-insensitive (Test@x.com == test@x.com).
            if email and User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    'A user with this email already exists. Please use a different email.'
                )
                return render(request, 'authentication/register.html', {'form': form})

            # Save the user (create the account)
            user = form.save(commit=False)
            if email:
                user.email = email
            user.save()

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
    """
    User login view.
    I'm using Django's authenticate() function to verify credentials.
    If authentication succeeds, I log the user in and redirect to the dashboard.
    If it fails, I show an error message and keep them on the login page.
    """
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
    User profile view with summary statistics.
    I show the number of applications the user owns and how many unread alerts
    they have. For admins, I show global counts instead of user-specific ones.
    This gives admins a quick overview of the entire system.
    """
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
    """
    Manage and create applications with auto-generated API Keys.
    I created this page so users can create new applications and view their
    API keys in one place. When a user creates an application, I generate
    a random UUID as the API key. This is much more secure than letting
    users choose their own keys.
    """
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
    I added pagination and filtering to make it easier for users to find
    relevant alerts. Without these features, the alerts list would become
    overwhelming as the system grows.
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
    This is a simple helper function that lets users mark alerts as read
    or unread with a single click. I redirect back to the previous page
    so the user doesn't lose their place in the list.
    """
    alert = get_object_or_404(Alert, id=alert_id)
    alert.is_read = not alert.is_read
    alert.save()

    return redirect(request.META.get('HTTP_REFERER', 'alerts_list'))


# =====================================================================
# API VIEWS (JWT & API Key based authentication)
# These views are used by developers and external agents to interact
# with the system programmatically.
# =====================================================================

class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing Applications.
    I used a ModelViewSet here because it automatically provides all the
    standard CRUD operations (Create, Read, Update, Delete) for applications.
    I customized the queryset so that admins see everything and regular users
    only see their own applications.
    """
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # Admins can see all applications for monitoring purposes
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Application.objects.all()
        # Regular users can only see and modify their own applications
        return Application.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # I automatically set the owner to the currently logged-in user.
        # This prevents users from creating applications owned by someone else.
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def forecast(self, request, pk=None):
        """
        Generate or retrieve cached forecast for an application.
        I check the cache first to avoid regenerating the forecast if it's
        already available. If not, I generate it and return the result.
        This makes the endpoint faster and reduces server load.
        """
        app = self.get_object()

        forecast = get_cached_forecast(app.id)
        if not forecast:
            forecast = generate_forecast_for_app(app.id)
            if not forecast:
                return Response(
                    {"error": "Not enough data to generate forecast!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response({
            "application_id": app.id,
            "application_name": app.name,
            "forecast": forecast
        })


class MetricViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing metrics via JWT or API Key.
    This is one of the most important parts of the system. It accepts metrics
    from both authenticated users (via JWT) and external agents (via API Key).
    I also added time filtering so users can retrieve metrics from specific
    time ranges (e.g., last 24 hours).
    """
    serializer_class = MetricSerializer
    permission_classes = [IsAgentOrAuthenticated]

    def get_queryset(self):
        """
        Determine the queryset based on user role and authentication method.
        Admins see all metrics, regular users see their own app metrics,
        and agents see only their app's metrics.
        """
        # Case 1: Authenticated user (JWT)
        if self.request.user and self.request.user.is_authenticated:
            if self.request.user.is_staff or self.request.user.is_superuser:
                queryset = Metric.objects.all()
            else:
                user_apps = Application.objects.filter(owner=self.request.user)
                queryset = Metric.objects.filter(application__in=user_apps)
        # Case 2: Agent (API Key)
        elif hasattr(self.request, '_agent_app'):
            queryset = Metric.objects.filter(application=self.request._agent_app)
        # Case 3: No valid authentication
        else:
            return Metric.objects.none()

        # Apply time filter if 'hours' parameter is provided
        hours_param = self.request.query_params.get('hours', None)
        if hours_param is not None:
            try:
                hours = int(hours_param)
                if hours > 0:
                    cutoff_time = timezone.now() - timedelta(hours=hours)
                    queryset = queryset.filter(timestamp__gte=cutoff_time)
                # If hours == 0, no filter is applied (show all data)
            except ValueError:
                # Ignore invalid parameter values
                pass

        # Return newest metrics first
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        """
        Create a new metric.

        IMPORTANT FIX:
        - If the request comes from an Agent (authenticated via API Key), I
          IGNORE the 'application' field sent by the client and use the
          application that owns the API Key instead. This prevents an agent
          from accidentally (or maliciously) sending data to a wrong
          application.
        - If the request comes from a JWT user, I validate that the application
          ID sent belongs to that user.
        """
        # ==============================================================
        # Case 1: Authenticated user via JWT
        # ==============================================================
        if self.request.user and self.request.user.is_authenticated:
            app_id = self.request.data.get('application')
            if not app_id:
                raise ValidationError({"application": "This field is required."})
            try:
                app = Application.objects.get(id=app_id, owner=self.request.user)
            except Application.DoesNotExist:
                raise ValidationError(
                    {"application": "Application not found or access denied."})

        # ==============================================================
        # Case 2: Agent authenticated via API Key
        # The application is determined EXCLUSIVELY by the API Key.
        # The client's 'application' field is completely ignored.
        # ==============================================================
        elif hasattr(self.request, '_agent_app'):
            app = self.request._agent_app  # Set by permissions.py

        # ==============================================================
        # Case 3: No valid authentication
        # ==============================================================
        else:
            raise PermissionDenied("Authentication credentials were not provided.")

        # Save the metric with the resolved application
        metric = serializer.save(application=app)

        # Broadcast the new metric via WebSocket for real-time updates.
        # I wrapped this in a try/except so the API doesn't fail if WebSocket
        # is not available (e.g., when running without Daphne).
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
            # WebSocket might not be configured, but the API should still work
            pass


class AlertViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing system alerts.
    Admins can see and create alerts for any application.
    Regular users can only see and create alerts for their own applications.
    """
    # I added this queryset attribute because DRF's router needs it
    # to infer the basename. Without it, we may get an ImproperlyConfigured error.
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Admins see all alerts; regular users only see their own."""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Alert.objects.all()
        return Alert.objects.filter(application__owner=self.request.user)

    def perform_create(self, serializer):
        """
        Create a new alert.
        Admins can create alerts for ANY application.
        Regular users can only create alerts for applications they own.
        """
        app_id = self.request.data.get('application')
        if not app_id:
            raise ValidationError({"application": "This field is required."})

        try:
            # Admins bypass the ownership check
            if self.request.user.is_staff or self.request.user.is_superuser:
                app = Application.objects.get(id=app_id)
            else:
                app = Application.objects.get(id=app_id, owner=self.request.user)
            serializer.save(application=app)
        except Application.DoesNotExist:
            raise ValidationError({"application": "Application not found or access denied."})