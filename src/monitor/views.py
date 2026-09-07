from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Metric, Application, Alert
from rest_framework import viewsets
from .serializers import MetricSerializer
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated


def home(request):
    return render(request, 'monitor/home.html')

@login_required
def dashboard(request):
    all_metrics = Metric.objects.all().order_by('-timestamp')
    return render(request, 'monitor/dashboard.html', {'metrics': all_metrics})



def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Correct register, {user.username} Please log in now.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f' {field}: {error}')
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
            messages.success(request, f'Hello, {username}, You log in successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Username or Password are not correct.')
    return render(request, 'authentication/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully')
    return redirect('home')

@login_required
def profile_view(request):
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



# === API ViewSet ===

class MetricViewSet(viewsets.ModelViewSet):
    queryset = Metric.objects.all().order_by('-timestamp')
    serializer_class = MetricSerializer
    permission_classes = [AllowAny]