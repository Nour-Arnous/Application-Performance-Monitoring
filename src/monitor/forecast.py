"""
Forecasting module using Prophet for response time prediction.
"""
import pandas as pd
from prophet import Prophet
from django.core.cache import cache
from .models import Metric, Application
import logging

logger = logging.getLogger(__name__)

def generate_forecast_for_app(app_id, periods=12, freq='5min'):
    """
    Generate forecast for a specific application.
    Returns forecast data as a list of dicts.
    """
    try:
        # Fetch historical data (last 100 points)
        metrics = Metric.objects.filter(
            application_id=app_id
        ).order_by('timestamp')[:100]
        
        if metrics.count() < 10:
            logger.warning(f"Not enough data for app {app_id}: {metrics.count()} points")
            return None
        
        # Prepare data for Prophet
        df = pd.DataFrame(list(metrics.values('timestamp', 'response_time')))
        
        # ✅ Remove timezone information from timestamp
        df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        
        # Rename columns to Prophet format
        df = df.rename(columns={'timestamp': 'ds', 'response_time': 'y'})
        
        # Train model
        model = Prophet(
            interval_width=0.95,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0
        )
        model.fit(df)
        
        # Make future predictions
        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)
        
        # Extract only future predictions
        forecast_data = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
        result = forecast_data.to_dict('records')
        
        # Cache the result
        cache_key = f'forecast_{app_id}'
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
        
        return result
        
    except Exception as e:
        logger.error(f"Forecast error for app {app_id}: {str(e)}")
        return None

def get_cached_forecast(app_id):
    """Retrieve cached forecast data."""
    cache_key = f'forecast_{app_id}'
    return cache.get(cache_key)