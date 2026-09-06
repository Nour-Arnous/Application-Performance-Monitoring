from rest_framework import serializers
from .models import Metric

class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = ['id', 'application_name', 'response_time', 'request_count', 'error_count', 'timestamp']