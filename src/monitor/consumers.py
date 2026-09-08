import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MetricConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time metric updates.
    Handles connections and sends metric data to connected clients.
    """
    async def connect(self):
        # Add this connection to the metrics group
        await self.channel_layer.group_add("metrics_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove this connection from the metrics group
        await self.channel_layer.group_discard("metrics_group", self.channel_name)

    async def metric_update(self, event):
        """
        Called when a new metric is created.
        Sends the metric data to the WebSocket client.
        """
        await self.send(text_data=json.dumps(event['data']))