from rest_framework import serializers
from .models import Metric, Application, Alert


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Application model.
    Exposes application metadata and owner username as read-only.
    """
    owner_username = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Application
        fields = [
            'id', 
            'name', 
            'description', 
            'owner', 
            'owner_username', 
            'created_at', 
            'is_active', 
            'api_key'
        ]
        read_only_fields = ['owner', 'api_key']


class MetricSerializer(serializers.ModelSerializer):
    """
    Serializer for the Metric model.
    Includes application_name to easily aggregate data on frontend charts.
    """
    application_name = serializers.ReadOnlyField(source='application.name')

    class Meta:
        model = Metric
        fields = [
            'id', 
            'application', 
            'application_name',  
            'response_time', 
            'request_count', 
            'error_count', 
            'timestamp'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """
    Serializer for the Alert model.
    Includes application_name so alerts can be displayed with app context.
    """
    application_name = serializers.ReadOnlyField(source='application.name')

    class Meta:
        model = Alert
        fields = [
            'id', 
            'application', 
            'application_name', 
            'message', 
            'severity', 
            'created_at', 
            'is_read', 
            'metric_value', 
            'threshold'
        ]