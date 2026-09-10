# Forecasting module using Prophet for response time prediction.
import logging
import pandas as pd
from prophet import Prophet
from django.core.cache import cache
from .models import Metric

logger = logging.getLogger(__name__)
def generate_forecast_for_app(app_id, periods=12, freq='5min'):
    # This function generates a Prophet forecast for response time for a specific app.
    # Since response time can never be negative, I clip any predicted negative
    # values to 0. The result is returned as a list of dictionaries with
    # ISO‑formatted dates so it's easy to use in the frontend.
    try:
        # Fetch the latest 100 historical data points
        metrics_qs = Metric.objects.filter(
            application_id=app_id
        ).order_by('-timestamp')[:100]

        if metrics_qs.count() < 10:
            logger.warning(f"Not enough data for app {app_id}: {metrics_qs.count()} points")
            return None

        # Convert queryset to list and reverse so it is in chronological order
        metrics_list = list(metrics_qs)[::-1]

        # Prepare DataFrame for Prophet
        data = [{'timestamp': m.timestamp, 'response_time': m.response_time} for m in metrics_list]
        df = pd.DataFrame(data)

        # Remove timezone information from timestamp as required by Prophet
        df['timestamp'] = df['timestamp'].dt.tz_localize(None)

        # Rename columns to Prophet required standard names ('ds' and 'y')
        df = df.rename(columns={'timestamp': 'ds', 'response_time': 'y'})

        # Train Prophet model
        model = Prophet(
            interval_width=0.95,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0
        )
        model.fit(df)

        # Make future dataframe and predict
        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)

        # Clip negative predicted values to zero (Response time cannot be negative)
        forecast['yhat'] = forecast['yhat'].clip(lower=0)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)

        # Extract only future predictions
        forecast_data = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

        # Convert DataFrame records to dict and format timestamps as ISO strings
        records = forecast_data.to_dict('records')
        result = []
        for row in records:
            result.append({
                'ds': row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                'yhat': float(row['yhat']),
                'yhat_lower': float(row['yhat_lower']),
                'yhat_upper': float(row['yhat_upper']),
            })

        # Cache the result for 1 hour (3600 seconds)
        cache_key = f'forecast_{app_id}'
        cache.set(cache_key, result, timeout=3600)

        return result

    except Exception as e:
        logger.error(f"Forecast error for app {app_id}: {str(e)}")
        return None


def get_cached_forecast(app_id):
    # Retrieve cached forecast data from Django cache
    cache_key = f'forecast_{app_id}'
    return cache.get(cache_key)