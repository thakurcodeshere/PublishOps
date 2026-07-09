"""Trend forecaster service (Tier A) containing time-series projection models for predictive trends."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

# Try importing scipy/pandas/prophet, with safe fallbacks
try:
    import pandas as pd
    import numpy as np
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    # Safe fallback if pandas/numpy/prophet are not installed
    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False

logger = logging.getLogger(__name__)


class TrendForecaster:
    """Predicts future trend performance using time-series forecasting models."""

    def __init__(self) -> None:
        self.model = None

    def _local_math_forecast(self, values: list[float], steps: int) -> list[float]:
        """Simple double exponential smoothing (Holt's Linear Trend) fallback forecast."""
        if not values:
            return [0.0] * steps
        if len(values) < 3:
            return [values[-1]] * steps

        # Simple linear projection
        # Y_t = a + b * t
        n = len(values)
        x = list(range(n))
        y = values
        
        # Calculate slope (b) and intercept (a)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        slope = num / den if den != 0 else 0.0
        intercept = mean_y - slope * mean_x

        # Generate future predictions
        predictions = []
        for step in range(1, steps + 1):
            pred = intercept + slope * (n + step)
            # Bound prediction between 0 and 100 (Google Trends standard scale)
            predictions.append(max(0.0, min(100.0, float(pred))))
        return predictions

    def forecast(self, dates: list[datetime], values: list[float], steps_days: int = 30) -> list[float]:
        """Forecast the trend values for the next N days.
        
        Args:
            dates: Historical dates.
            values: Historical Google Trends values (0-100).
            steps_days: Number of days to forecast into the future.
            
        Returns:
            A list of forecasted values.
        """
        if not dates or not values or len(dates) != len(values):
            return [0.0] * steps_days

        if HAS_PROPHET:
            try:
                # Prepare DataFrame for Prophet: requires columns 'ds' and 'y'
                df = pd.DataFrame({
                    "ds": [d.replace(tzinfo=None) for d in dates],
                    "y": values
                })
                # Silence Prophet logging
                logging.getLogger("prophet").setLevel(logging.ERROR)
                
                m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                m.fit(df)
                
                future = m.make_future_dataframe(periods=steps_days)
                forecast_df = m.predict(future)
                
                # Extract the last steps_days predictions
                predictions = forecast_df["yhat"].tail(steps_days).tolist()
                return [max(0.0, min(100.0, float(p))) for p in predictions]
            except Exception as e:
                logger.warning(f"Prophet forecast failed, falling back to local math: {e}")
                
        return self._local_math_forecast(values, steps_days)
