from rest_framework import serializers
from .models import Metric, Application, Alert


class ApplicationSerializer(serializers.ModelSerializer):
    # I added this field so that when I fetch applications, I can easily see
    # the owner's username without making an extra database query. This is
    # useful for displaying on the frontend and debugging.
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
        # I set 'owner' and 'api_key' as read-only because the owner should
        # be set automatically when the application is created (based on the
        # logged-in user or agent). The API key is generated automatically by
        # the model's save() method, so it shouldn't be modified manually.
        read_only_fields = ['owner', 'api_key']


class MetricSerializer(serializers.ModelSerializer):
    # I included this field to show the application name alongside each metric.
    # This makes it much easier to group and display data on the frontend charts
    # without needing to do extra joins or lookups in JavaScript.
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
    # I added this field so that when I display alerts on the dashboard,
    # I can show the application name without having to query the database again.
    # This also helps when I send alerts to the frontend via WebSocket.
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