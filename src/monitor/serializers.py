from rest_framework import serializers
from .models import Metric, Application, Alert

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'created_at', 'is_active', 'api_key']
        read_only_fields = ['owner', 'api_key']

class MetricSerializer(serializers.ModelSerializer):
    application_name = serializers.ReadOnlyField(source='application.name')

    class Meta:
        model = Metric
        fields = ['id', 'application', 'application_name', 'response_time', 'request_count', 'error_count', 'timestamp']

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['id', 'application', 'message', 'severity', 'created_at', 'is_read', 'metric_value', 'threshold']