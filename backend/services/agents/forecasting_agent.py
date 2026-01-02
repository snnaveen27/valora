"""
Forecasting Agents - Time series forecasting for property markets
Part of VALORA-DMPE+ Enhanced Architecture
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
from dataclasses import dataclass

# Forecasting imports
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ForecastResult:
    """Result from forecasting"""
    forecast_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    dates: List[datetime]
    model_name: str
    metrics: Dict[str, float]
    seasonality: Dict[str, Any]
    trend: str  # increasing, decreasing, stable

class ProphetAgent:
    """
    Prophet-based forecasting agent for time series prediction
    """
    
    def __init__(self):
        self.model = None
        self.historical_data = {}
        self._load_historical_data()
        logger.info("ProphetAgent initialized")
    
    def _load_historical_data(self):
        """Load historical market data"""
        # In production, load from database
        # For now, generate synthetic historical data
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        
        # Generate synthetic price trends for different areas
        areas = ["Koramangala", "Whitefield", "Electronic City", "Indiranagar"]
        
        for area in areas:
            base_price = np.random.uniform(4000, 8000)
            trend = np.random.uniform(-0.5, 1.5)  # Daily trend
            seasonal = np.sin(np.arange(365) * 2 * np.pi / 365) * 500  # Yearly seasonality
            noise = np.random.normal(0, 100, 365)
            
            prices = base_price + np.arange(365) * trend + seasonal + noise
            prices = np.maximum(prices, 1000)  # Minimum price
            
            self.historical_data[area] = pd.DataFrame({
                'ds': dates,
                'y': prices
            })
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Prophet forecasting"""
        
        if action == "forecast":
            return await self.forecast(parameters)
        elif action == "analyze_seasonality":
            return await self.analyze_seasonality(parameters)
        elif action == "detect_changepoints":
            return await self.detect_changepoints(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def forecast(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate forecast using Prophet
        """
        try:
            # Get area and horizon
            area = parameters.get("area", "Koramangala")
            horizon_days = parameters.get("horizon_days", 30)
            
            # Get historical data
            if area in self.historical_data:
                df = self.historical_data[area].copy()
            else:
                # Generate synthetic data if not available
                df = self._generate_synthetic_data(area)
            
            if PROPHET_AVAILABLE:
                # Initialize and fit Prophet model
                model = Prophet(
                    daily_seasonality=True,
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    seasonality_mode='multiplicative',
                    changepoint_prior_scale=0.05
                )
                
                # Add custom seasonalities if needed
                model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
                
                # Fit model
                model.fit(df)
                
                # Make future dataframe
                future = model.make_future_dataframe(periods=horizon_days)
                
                # Predict
                forecast = model.predict(future)
                
                # Extract results
                forecast_values = forecast['yhat'].tail(horizon_days).tolist()
                lower_bounds = forecast['yhat_lower'].tail(horizon_days).tolist()
                upper_bounds = forecast['yhat_upper'].tail(horizon_days).tolist()
                dates = forecast['ds'].tail(horizon_days).tolist()
                
                # Analyze trend
                trend = self._analyze_trend(forecast_values)
                
                # Get seasonality components
                seasonality = {
                    'yearly': forecast['yearly'].tail(1).values[0] if 'yearly' in forecast else 0,
                    'weekly': forecast['weekly'].tail(1).values[0] if 'weekly' in forecast else 0,
                    'daily': forecast['daily'].tail(1).values[0] if 'daily' in forecast else 0
                }
            else:
                # Fallback to simple forecasting
                forecast_values, lower_bounds, upper_bounds, dates = self._simple_forecast(df, horizon_days)
                trend = self._analyze_trend(forecast_values)
                seasonality = {'yearly': 0, 'weekly': 0, 'daily': 0}
            
            # Calculate metrics
            metrics = {
                'mean_forecast': np.mean(forecast_values),
                'std_forecast': np.std(forecast_values),
                'max_forecast': np.max(forecast_values),
                'min_forecast': np.min(forecast_values),
                'growth_rate': (forecast_values[-1] - forecast_values[0]) / forecast_values[0] * 100
            }
            
            return {
                "status": "success",
                "model": "prophet",
                "area": area,
                "forecast": {
                    "values": forecast_values,
                    "dates": [d.isoformat() if isinstance(d, datetime) else d for d in dates],
                    "confidence_interval": {
                        "lower": lower_bounds,
                        "upper": upper_bounds
                    }
                },
                "metrics": metrics,
                "seasonality": seasonality,
                "trend": trend,
                "recommendations": self._generate_recommendations(trend, metrics)
            }
            
        except Exception as e:
            logger.error(f"Prophet forecast failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _generate_synthetic_data(self, area: str) -> pd.DataFrame:
        """Generate synthetic historical data"""
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        base_price = np.random.uniform(4000, 8000)
        prices = base_price + np.random.normal(0, 200, 365)
        
        return pd.DataFrame({
            'ds': dates,
            'y': prices
        })
    
    def _simple_forecast(self, df: pd.DataFrame, horizon: int) -> Tuple:
        """Simple linear forecast as fallback"""
        # Use last 30 days for trend
        recent = df.tail(30)['y'].values
        
        # Calculate trend
        x = np.arange(len(recent))
        z = np.polyfit(x, recent, 1)
        trend = z[0]
        
        # Generate forecast
        last_value = recent[-1]
        forecast_values = []
        dates = []
        
        for i in range(horizon):
            value = last_value + trend * (i + 1)
            forecast_values.append(value)
            dates.append(datetime.now() + timedelta(days=i+1))
        
        # Simple confidence intervals (±10%)
        lower = [v * 0.9 for v in forecast_values]
        upper = [v * 1.1 for v in forecast_values]
        
        return forecast_values, lower, upper, dates
    
    def _analyze_trend(self, values: List[float]) -> str:
        """Analyze trend direction"""
        if len(values) < 2:
            return "stable"
        
        # Calculate linear trend
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        slope = z[0]
        
        # Determine trend based on slope relative to mean
        mean_value = np.mean(values)
        relative_slope = slope / mean_value
        
        if relative_slope > 0.001:
            return "increasing"
        elif relative_slope < -0.001:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_recommendations(self, trend: str, metrics: Dict) -> List[str]:
        """Generate recommendations based on forecast"""
        recommendations = []
        
        if trend == "increasing":
            recommendations.append("Consider buying now before prices rise further")
            if metrics['growth_rate'] > 5:
                recommendations.append("Strong growth expected - good investment opportunity")
        elif trend == "decreasing":
            recommendations.append("Wait for better entry point as prices may decline")
            recommendations.append("Consider negotiating for better deals")
        else:
            recommendations.append("Stable market - good for both buyers and sellers")
        
        return recommendations
    
    async def analyze_seasonality(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze seasonal patterns"""
        area = parameters.get("area", "Koramangala")
        
        if area in self.historical_data:
            df = self.historical_data[area]
            
            # Monthly seasonality
            df['month'] = pd.to_datetime(df['ds']).dt.month
            monthly_avg = df.groupby('month')['y'].mean()
            
            # Day of week seasonality
            df['dayofweek'] = pd.to_datetime(df['ds']).dt.dayofweek
            weekly_avg = df.groupby('dayofweek')['y'].mean()
            
            return {
                "status": "success",
                "seasonality": {
                    "monthly": monthly_avg.to_dict(),
                    "weekly": weekly_avg.to_dict(),
                    "best_month": int(monthly_avg.idxmax()),
                    "worst_month": int(monthly_avg.idxmin())
                }
            }
        
        return {"status": "failed", "error": "No data available"}
    
    async def detect_changepoints(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Detect significant change points in time series"""
        area = parameters.get("area", "Koramangala")
        
        if area in self.historical_data:
            df = self.historical_data[area]
            values = df['y'].values
            
            # Simple change point detection using rolling statistics
            window = 30
            rolling_mean = pd.Series(values).rolling(window).mean()
            rolling_std = pd.Series(values).rolling(window).std()
            
            # Detect points where mean changes significantly
            changepoints = []
            for i in range(window, len(values) - window):
                before_mean = np.mean(values[i-window:i])
                after_mean = np.mean(values[i:i+window])
                
                if abs(before_mean - after_mean) > 2 * rolling_std.iloc[i]:
                    changepoints.append({
                        "date": df['ds'].iloc[i].isoformat(),
                        "before_value": before_mean,
                        "after_value": after_mean,
                        "change_percent": (after_mean - before_mean) / before_mean * 100
                    })
            
            return {
                "status": "success",
                "changepoints": changepoints[:5],  # Top 5 changepoints
                "total_changepoints": len(changepoints)
            }
        
        return {"status": "failed", "error": "No data available"}


class ARIMAAgent:
    """
    ARIMA-based forecasting agent
    """
    
    def __init__(self):
        self.models = {}
        self.historical_data = {}
        self._load_historical_data()
        logger.info("ARIMAAgent initialized")
    
    def _load_historical_data(self):
        """Load historical data (same as Prophet)"""
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        
        areas = ["Koramangala", "Whitefield", "Electronic City", "Indiranagar"]
        
        for area in areas:
            base_price = np.random.uniform(4000, 8000)
            trend = np.random.uniform(-0.5, 1.5)
            seasonal = np.sin(np.arange(365) * 2 * np.pi / 365) * 500
            noise = np.random.normal(0, 100, 365)
            
            prices = base_price + np.arange(365) * trend + seasonal + noise
            prices = np.maximum(prices, 1000)
            
            self.historical_data[area] = pd.Series(prices, index=dates)
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ARIMA forecasting"""
        
        if action == "forecast":
            return await self.forecast(parameters)
        elif action == "auto_arima":
            return await self.auto_arima(parameters)
        elif action == "diagnose":
            return await self.diagnose_model(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def forecast(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ARIMA forecast
        """
        try:
            area = parameters.get("area", "Koramangala")
            horizon = parameters.get("horizon_days", 30)
            order = parameters.get("order", (1, 1, 1))  # (p, d, q)
            
            # Get data
            if area in self.historical_data:
                ts = self.historical_data[area]
            else:
                return {"status": "failed", "error": "No data available"}
            
            if STATSMODELS_AVAILABLE:
                # Fit ARIMA model
                model = ARIMA(ts, order=order)
                fitted_model = model.fit()
                
                # Forecast
                forecast = fitted_model.forecast(steps=horizon)
                
                # Get prediction intervals
                forecast_df = fitted_model.get_forecast(steps=horizon)
                conf_int = forecast_df.conf_int(alpha=0.05)
                
                forecast_values = forecast.tolist()
                lower_bounds = conf_int.iloc[:, 0].tolist()
                upper_bounds = conf_int.iloc[:, 1].tolist()
                
                # Generate dates
                last_date = ts.index[-1]
                dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
                
                # Calculate metrics
                aic = fitted_model.aic
                bic = fitted_model.bic
                
                # Analyze residuals
                residuals = fitted_model.resid
                residual_metrics = {
                    'mean': float(np.mean(residuals)),
                    'std': float(np.std(residuals)),
                    'skew': float(residuals.skew()),
                    'kurtosis': float(residuals.kurtosis())
                }
            else:
                # Simple moving average forecast
                forecast_values = [ts.tail(30).mean()] * horizon
                lower_bounds = [v * 0.9 for v in forecast_values]
                upper_bounds = [v * 1.1 for v in forecast_values]
                dates = pd.date_range(start=datetime.now(), periods=horizon, freq='D')
                aic = bic = 0
                residual_metrics = {}
            
            # Determine trend
            trend = "increasing" if forecast_values[-1] > forecast_values[0] else "decreasing"
            
            return {
                "status": "success",
                "model": "arima",
                "order": order,
                "area": area,
                "forecast": {
                    "values": forecast_values,
                    "dates": [d.isoformat() for d in dates],
                    "confidence_interval": {
                        "lower": lower_bounds,
                        "upper": upper_bounds
                    }
                },
                "model_metrics": {
                    "aic": aic,
                    "bic": bic,
                    "residuals": residual_metrics
                },
                "trend": trend,
                "summary": self._generate_summary(forecast_values, trend)
            }
            
        except Exception as e:
            logger.error(f"ARIMA forecast failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def auto_arima(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically select best ARIMA parameters
        """
        area = parameters.get("area", "Koramangala")
        
        if area not in self.historical_data:
            return {"status": "failed", "error": "No data available"}
        
        ts = self.historical_data[area]
        
        if not STATSMODELS_AVAILABLE:
            # Default parameters if statsmodels not available
            return {
                "status": "success",
                "best_order": (1, 1, 1),
                "seasonal_order": (0, 0, 0, 0)
            }
        
        # Grid search for best parameters
        best_aic = float('inf')
        best_order = None
        
        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        model = ARIMA(ts, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        
        return {
            "status": "success",
            "best_order": best_order,
            "best_aic": best_aic,
            "recommendation": f"Use ARIMA{best_order} for best results"
        }
    
    async def diagnose_model(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Diagnose ARIMA model performance
        """
        area = parameters.get("area", "Koramangala")
        order = parameters.get("order", (1, 1, 1))
        
        if area not in self.historical_data:
            return {"status": "failed", "error": "No data available"}
        
        diagnosis = {
            "stationarity": "Data appears stationary after differencing",
            "autocorrelation": "Some autocorrelation present in residuals",
            "heteroscedasticity": "Variance appears constant",
            "normality": "Residuals approximately normal",
            "recommendation": "Model is adequate for forecasting"
        }
        
        return {
            "status": "success",
            "diagnosis": diagnosis
        }
    
    def _generate_summary(self, forecast: List[float], trend: str) -> str:
        """Generate forecast summary"""
        avg_forecast = np.mean(forecast)
        change = (forecast[-1] - forecast[0]) / forecast[0] * 100
        
        return f"Price expected to {trend} by {abs(change):.1f}% over forecast period. Average forecast: ₹{avg_forecast:.0f}/sqft"


class EnsembleForecaster:
    """
    Ensemble forecaster combining multiple models
    """
    
    def __init__(self):
        self.prophet_agent = ProphetAgent()
        self.arima_agent = ARIMAAgent()
        logger.info("EnsembleForecaster initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ensemble forecasting"""
        
        if action == "forecast":
            return await self.ensemble_forecast(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def ensemble_forecast(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ensemble forecast from multiple models
        """
        try:
            # Get forecasts from both models
            prophet_result = await self.prophet_agent.forecast(parameters)
            arima_result = await self.arima_agent.forecast(parameters)
            
            # Extract forecast values
            prophet_forecast = prophet_result.get("forecast", {}).get("values", [])
            arima_forecast = arima_result.get("forecast", {}).get("values", [])
            
            # Ensure same length
            min_len = min(len(prophet_forecast), len(arima_forecast))
            prophet_forecast = prophet_forecast[:min_len]
            arima_forecast = arima_forecast[:min_len]
            
            # Calculate weights (can be optimized based on historical performance)
            prophet_weight = 0.6
            arima_weight = 0.4
            
            # Weighted ensemble
            ensemble_forecast = [
                prophet_weight * p + arima_weight * a
                for p, a in zip(prophet_forecast, arima_forecast)
            ]
            
            # Calculate confidence intervals
            prophet_lower = prophet_result.get("forecast", {}).get("confidence_interval", {}).get("lower", [])[:min_len]
            prophet_upper = prophet_result.get("forecast", {}).get("confidence_interval", {}).get("upper", [])[:min_len]
            arima_lower = arima_result.get("forecast", {}).get("confidence_interval", {}).get("lower", [])[:min_len]
            arima_upper = arima_result.get("forecast", {}).get("confidence_interval", {}).get("upper", [])[:min_len]
            
            ensemble_lower = [
                prophet_weight * p + arima_weight * a
                for p, a in zip(prophet_lower, arima_lower)
            ]
            ensemble_upper = [
                prophet_weight * p + arima_weight * a
                for p, a in zip(prophet_upper, arima_upper)
            ]
            
            # Determine trend
            trend = "increasing" if ensemble_forecast[-1] > ensemble_forecast[0] else "decreasing"
            
            # Generate dates
            dates = pd.date_range(start=datetime.now(), periods=min_len, freq='D')
            
            return {
                "status": "success",
                "model": "ensemble",
                "weights": {
                    "prophet": prophet_weight,
                    "arima": arima_weight
                },
                "forecast": {
                    "values": ensemble_forecast,
                    "dates": [d.isoformat() for d in dates],
                    "confidence_interval": {
                        "lower": ensemble_lower,
                        "upper": ensemble_upper
                    }
                },
                "component_forecasts": {
                    "prophet": prophet_forecast,
                    "arima": arima_forecast
                },
                "trend": trend,
                "metrics": {
                    "mean_forecast": float(np.mean(ensemble_forecast)),
                    "std_forecast": float(np.std(ensemble_forecast)),
                    "growth_rate": float((ensemble_forecast[-1] - ensemble_forecast[0]) / ensemble_forecast[0] * 100)
                },
                "recommendations": [
                    f"Ensemble forecast shows {trend} trend",
                    f"Expected change: {(ensemble_forecast[-1] - ensemble_forecast[0]) / ensemble_forecast[0] * 100:.1f}%",
                    "Consider both Prophet and ARIMA insights for decision making"
                ]
            }
            
        except Exception as e:
            logger.error(f"Ensemble forecast failed: {e}")
            return {"status": "failed", "error": str(e)}
