from django.shortcuts import render
from .models import Metric
from rest_framework import viewsets
from .serializers import MetricSerializer

# Create your views here.

def home(request):
    all_metrics = Metric.objects.all().order_by('-timestamp')
    return render(request, 'monitor/home.html', {'metrics': all_metrics})

class MetricViewSet(viewsets.ModelViewSet):
    queryset = Metric.objects.all().order_by('-timestamp')
    serializer_class = MetricSerializer