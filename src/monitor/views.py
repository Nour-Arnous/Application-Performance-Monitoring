from django.shortcuts import render
from .models import Metric

# Create your views here.

def home(request):
    all_metrics = Metric.objects.all().order_by('-timestamp')
    return render(request, 'monitor/home.html', {'metrics': all_metrics})