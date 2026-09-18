"""
APEX-Energy: Renewable Generation Forecasting Engine
====================================================
Phase 2: Renewable Generation Forecasting Integration.

Predicts short-term future renewable generation (Solar PV and Wind)
utilizing the Phase 1 synthetic industrial dataset.

Core Capabilities:
1. Chronological Time-Series Separation (Train: Days 0-4, Test: Days 5-6, zero leakage).
2. Feature Engineering: Diurnal cyclics, ambient weather, and autoregressive lag features.
3. Model Training & Comparison:
   - Persistence Baseline (y_{t+h} = y_t)
   - Gradient Boosting Regressor (sklearn.ensemble)
   - Multi-Layer Perceptron (sklearn.neural_network.MLPRegressor)
4. Evaluation Metrics: MAE and RMSE.
5. Rolling Multi-Step Horizon (30 - 180 minutes ahead at 5-minute resolution).
6. Renewable-Rich Window Detection: Identifies upcoming solar surges for Phase 3 decision making.
7. Physical Sanity Constraints: Strict non-negative clamping and nighttime zeroing.
"""

import os
import csv
import math
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

class RenewableForecastingEngine:
    def __init__(self, dataset_path=None, seed=42):
        self.seed = seed
        self.dataset_path = dataset_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_datasets",
            "apex_industrial_dataset.csv"
        )
        self.solar_model = None
        self.wind_model = None
        self.mlp_solar_model = None
        self.is_trained = False
        
        # Metrics storage
        self.metrics = {}
        
        # Physical constraints
        self.SOLAR_MAX_CAPACITY = 100.0 # kW
        self.WIND_MAX_CAPACITY = 50.0   # kW
        
        # Pre-train on initialization
        self.train_models()

    def _load_dataset(self):
        """Loads Phase 1 industrial dataset records."""
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"APEX dataset not found at {self.dataset_path}. Run generate_apex_dataset.py first.")
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _extract_features_and_targets(self, rows, lag_steps=12):
        """
        Constructs time-series features with strict chronological lag constraints.
        lag_steps = 12 represents 1 hour of 5-minute past history.
        No future values leak into feature vectors.
        """
        timestamps = [r["timestamp"] for r in rows]
        solar = np.array([float(r["solar_generation_kw"]) for r in rows])
        wind = np.array([float(r["wind_generation_kw"]) for r in rows])
        hour = np.array([float(r["hour"]) for r in rows])
        temp = np.array([float(r["ambient_temperature_c"]) for r in rows])
        cloud = np.array([float(r["cloud_cover"]) for r in rows])
        wind_speed = np.array([float(r["wind_speed_m_s"]) for r in rows])
        is_weekend = np.array([float(r["is_weekend"]) for r in rows])

        X = []
        y_solar = []
        y_wind = []
        valid_timestamps = []

        for i in range(lag_steps, len(rows)):
            # 1. Cyclical hour features
            h_rad = 2.0 * math.pi * hour[i] / 24.0
            sin_h = math.sin(h_rad)
            cos_h = math.cos(h_rad)

            # 2. Ambient weather context
            t_val = temp[i]
            c_val = cloud[i]
            w_val = wind_speed[i]
            wk_val = is_weekend[i]

            # 3. Autoregressive lags (strictly past values: i-1, i-2, i-3, i-6, i-12)
            # Corresponding to t-5m, t-10m, t-15m, t-30m, t-60m
            s_lags = [solar[i - 1], solar[i - 2], solar[i - 3], solar[i - 6], solar[i - 12]]
            w_lags = [wind[i - 1], wind[i - 2], wind[i - 3], wind[i - 6], wind[i - 12]]

            feat = [hour[i], sin_h, cos_h, t_val, c_val, w_val, wk_val] + s_lags + w_lags
            X.append(feat)
            y_solar.append(solar[i])
            y_wind.append(wind[i])
            valid_timestamps.append(timestamps[i])

        return np.array(X), np.array(y_solar), np.array(y_wind), valid_timestamps, solar, wind, rows

    def train_models(self, train_ratio=0.75):
        """
        Performs chronological train/test split and trains forecasting models.
        Train set: Days 0 to 4 (approx 75% of dataset).
        Test set: Days 5 to 6 (remaining 25% of dataset).
        """
        rows = self._load_dataset()
        X, y_solar, y_wind, timestamps, raw_solar, raw_wind, raw_rows = self._extract_features_and_targets(rows)
        
        # Cache for multi-step rolling forecast
        self._raw_rows = raw_rows
        self._raw_solar = raw_solar
        self._raw_wind = raw_wind

        # Strict Chronological Split (No random shuffling!)
        split_idx = int(len(X) * train_ratio)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_solar_train, y_solar_test = y_solar[:split_idx], y_solar[split_idx:]
        y_wind_train, y_wind_test = y_wind[:split_idx], y_wind[split_idx:]

        # ----------------------------------------------------
        # 1. Baseline Model: Naive Persistence (y_{t} ≈ y_{t-1})
        # ----------------------------------------------------
        solar_lag1_test = X_test[:, 7] # solar lag 1 index
        wind_lag1_test = X_test[:, 12] # wind lag 1 index

        base_solar_mae = float(mean_absolute_error(y_solar_test, solar_lag1_test))
        base_solar_rmse = float(np.sqrt(mean_squared_error(y_solar_test, solar_lag1_test)))
        base_wind_mae = float(mean_absolute_error(y_wind_test, wind_lag1_test))
        base_wind_rmse = float(np.sqrt(mean_squared_error(y_wind_test, wind_lag1_test)))

        # ----------------------------------------------------
        # 2. Gradient Boosting Models
        # ----------------------------------------------------
        self.solar_model = GradientBoostingRegressor(n_estimators=60, max_depth=4, random_state=self.seed)
        self.solar_model.fit(X_train, y_solar_train)
        pred_gb_solar = np.clip(self.solar_model.predict(X_test), 0.0, self.SOLAR_MAX_CAPACITY)
        
        # Enforce nighttime zeroing in test predictions
        for idx in range(len(pred_gb_solar)):
            h = X_test[idx, 0]
            if h < 5.8 or h > 18.2:
                pred_gb_solar[idx] = 0.0

        gb_solar_mae = float(mean_absolute_error(y_solar_test, pred_gb_solar))
        gb_solar_rmse = float(np.sqrt(mean_squared_error(y_solar_test, pred_gb_solar)))

        self.wind_model = GradientBoostingRegressor(n_estimators=60, max_depth=4, random_state=self.seed)
        self.wind_model.fit(X_train, y_wind_train)
        pred_gb_wind = np.clip(self.wind_model.predict(X_test), 0.0, self.WIND_MAX_CAPACITY)
        gb_wind_mae = float(mean_absolute_error(y_wind_test, pred_gb_wind))
        gb_wind_rmse = float(np.sqrt(mean_squared_error(y_wind_test, pred_gb_wind)))

        # ----------------------------------------------------
        # 3. Multi-Layer Perceptron (MLP) Model
        # ----------------------------------------------------
        self.mlp_solar_model = MLPRegressor(hidden_layer_sizes=(64, 32), activation='relu', max_iter=250, random_state=self.seed)
        self.mlp_solar_model.fit(X_train, y_solar_train)
        pred_mlp_solar = np.clip(self.mlp_solar_model.predict(X_test), 0.0, self.SOLAR_MAX_CAPACITY)
        for idx in range(len(pred_mlp_solar)):
            h = X_test[idx, 0]
            if h < 5.8 or h > 18.2:
                pred_mlp_solar[idx] = 0.0

        mlp_solar_mae = float(mean_absolute_error(y_solar_test, pred_mlp_solar))
        mlp_solar_rmse = float(np.sqrt(mean_squared_error(y_solar_test, pred_mlp_solar)))

        self.metrics = {
            "solar": {
                "baseline_mae": round(base_solar_mae, 3),
                "baseline_rmse": round(base_solar_rmse, 3),
                "gb_mae": round(gb_solar_mae, 3),
                "gb_rmse": round(gb_solar_rmse, 3),
                "mlp_mae": round(mlp_solar_mae, 3),
                "mlp_rmse": round(mlp_solar_rmse, 3)
            },
            "wind": {
                "baseline_mae": round(base_wind_mae, 3),
                "baseline_rmse": round(base_wind_rmse, 3),
                "gb_mae": round(gb_wind_mae, 3),
                "gb_rmse": round(gb_wind_rmse, 3)
            }
        }
        self.is_trained = True
        return self.metrics

    def predict_multi_step(self, current_time_str: str = None, horizon_minutes: int = 180, step_minutes: int = 5):
        """
        Generates a rolling autoregressive forecast over a short-term horizon (e.g. 30 to 180 minutes).
        At each step t+k, predicted values are fed back into lag features.
        
        current_time_str: Timestamp string e.g. "2026-06-03 10:00:00". If None, defaults to Day 2 10:00 AM (Wednesday flex shift window).
        """
        if not self.is_trained:
            self.train_models()

        # Find row index matching timestamp or default to Day 2 10:00:00 (Wednesday flex opportunity)
        target_idx = 696 # Day 2 10:00 AM default
        if current_time_str:
            for idx, r in enumerate(self._raw_rows):
                if r["timestamp"] == current_time_str:
                    target_idx = idx
                    break

        if target_idx < 12:
            target_idx = 12 # Ensure at least 1 hour of past lags available

        curr_row = self._raw_rows[target_idx]
        curr_hour = float(curr_row["hour"])
        curr_temp = float(curr_row["ambient_temperature_c"])
        curr_cloud = float(curr_row["cloud_cover"])
        curr_wind_spd = float(curr_row["wind_speed_m_s"])
        curr_weekend = float(curr_row["is_weekend"])

        # History arrays for rolling autoregressive lags
        curr_solar_history = list(self._raw_solar[target_idx - 12 : target_idx])
        curr_wind_history = list(self._raw_wind[target_idx - 12 : target_idx])

        horizon_steps = int(horizon_minutes / step_minutes)
        predictions = []

        for step in range(horizon_steps):
            step_offset_min = (step + 1) * step_minutes
            step_hour = (curr_hour + step_offset_min / 60.0) % 24.0
            h_rad = 2.0 * math.pi * step_hour / 24.0
            
            # Step timestamp string
            base_dt = datetime.strptime(curr_row["timestamp"], "%Y-%m-%d %H:%M:%S")
            step_dt = base_dt + timedelta(minutes=step_offset_min)
            step_ts = step_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Lag features from autoregressive history
            s_lags = [
                curr_solar_history[-1], curr_solar_history[-2], curr_solar_history[-3],
                curr_solar_history[-6], curr_solar_history[-12]
            ]
            w_lags = [
                curr_wind_history[-1], curr_wind_history[-2], curr_wind_history[-3],
                curr_wind_history[-6], curr_wind_history[-12]
            ]

            # Temperature and ambient diurnal extrapolation
            step_temp = curr_temp + 2.0 * math.sin(2.0 * math.pi * (step_hour - 9.0) / 24.0)
            step_cloud = curr_cloud
            step_wind_spd = curr_wind_spd

            input_feat = np.array([[
                step_hour, math.sin(h_rad), math.cos(h_rad),
                step_temp, step_cloud, step_wind_spd, curr_weekend
            ] + s_lags + w_lags])

            # Solar Prediction with physical sanity checks
            pred_s = float(self.solar_model.predict(input_feat)[0])
            pred_s = max(0.0, min(self.SOLAR_MAX_CAPACITY, pred_s))
            if step_hour < 5.8 or step_hour > 18.2:
                pred_s = 0.0 # Physical nighttime clamp

            # Wind Prediction with physical sanity checks
            pred_w = float(self.wind_model.predict(input_feat)[0])
            pred_w = max(0.0, min(self.WIND_MAX_CAPACITY, pred_w))

            # Push predicted outputs into history for subsequent autoregressive lags
            curr_solar_history.append(pred_s)
            curr_wind_history.append(pred_w)

            total_renewable = round(pred_s + pred_w, 2)

            predictions.append({
                "step": step + 1,
                "time_offset_min": step_offset_min,
                "timestamp": step_ts,
                "solar_generation_kw": round(pred_s, 2),
                "wind_generation_kw": round(pred_w, 2),
                "total_renewable_kw": total_renewable
            })

        # ----------------------------------------------------
        # Renewable-Rich Window Detection
        # ----------------------------------------------------
        # Threshold: 50.0 kW (representing high solar capacity factor > 50%)
        THRESHOLD_KW = 50.0
        rich_steps = [p for p in predictions if p["solar_generation_kw"] >= THRESHOLD_KW]

        if rich_steps:
            window_start = rich_steps[0]["timestamp"].split()[1]
            window_end = rich_steps[-1]["timestamp"].split()[1]
            peak_solar = max(p["solar_generation_kw"] for p in rich_steps)
            avg_solar = sum(p["solar_generation_kw"] for p in rich_steps) / len(rich_steps)
            window_info = {
                "is_renewable_rich": True,
                "start_time": window_start,
                "end_time": window_end,
                "duration_minutes": len(rich_steps) * step_minutes,
                "peak_solar_kw": round(peak_solar, 2),
                "average_solar_kw": round(avg_solar, 2),
                "threshold_kw": THRESHOLD_KW,
                "reason": f"Predicted solar generation exceeds {THRESHOLD_KW} kW threshold across {len(rich_steps) * step_minutes} minutes.",
                "recommendation": "High solar generation surge predicted. Prime window for shifting flexible production (Machine C)."
            }
        else:
            window_info = {
                "is_renewable_rich": False,
                "start_time": None,
                "end_time": None,
                "duration_minutes": 0,
                "peak_solar_kw": round(max([p["solar_generation_kw"] for p in predictions], default=0.0), 2),
                "average_solar_kw": round(sum(p["solar_generation_kw"] for p in predictions) / max(1, len(predictions)), 2),
                "threshold_kw": THRESHOLD_KW,
                "reason": f"Predicted solar generation remains below {THRESHOLD_KW} kW throughout horizon.",
                "recommendation": "Maintain normal baseline production schedule; insufficient renewable surge for shifting."
            }

        return {
            "forecast_generated_at": curr_row["timestamp"],
            "horizon_minutes": horizon_minutes,
            "step_interval_minutes": step_minutes,
            "total_steps": horizon_steps,
            "predictions": predictions,
            "renewable_rich_window": window_info,
            "model_metadata": {
                "model_name": "GradientBoostingRegressor",
                "solar_mae_kw": self.metrics["solar"]["gb_mae"],
                "solar_rmse_kw": self.metrics["solar"]["gb_rmse"],
                "wind_mae_kw": self.metrics["wind"]["gb_mae"],
                "wind_rmse_kw": self.metrics["wind"]["gb_rmse"]
            }
        }

# Singleton instance for real-time SCADA and API serving
renewable_forecaster = RenewableForecastingEngine()

def get_renewable_forecast(current_timestamp: str = None, horizon_minutes: int = 180):
    """Clean function contract for Phase 3 Decision Engine consumption."""
    return renewable_forecaster.predict_multi_step(current_timestamp, horizon_minutes)

if __name__ == "__main__":
    print("[Forecaster] Initializing and evaluating models on Phase 1 dataset...")
    engine = RenewableForecastingEngine()
    print("\nModel Evaluation Metrics:")
    for target, metric_dict in engine.metrics.items():
        print(f"  Target: {target.upper()}")
        for k, v in metric_dict.items():
            print(f"    {k:15s}: {v:6.3f} kW")

    print("\nTesting Rolling Forecast at Day 2 10:00:00 (Flexible Shift Opportunity)...")
    res = engine.predict_multi_step("2026-06-03 10:00:00", horizon_minutes=180)
    print(f"Forecast Horizon: {res['horizon_minutes']} minutes ({res['total_steps']} steps)")
    print(f"Renewable Rich Window: {res['renewable_rich_window']['is_renewable_rich']}")
    if res['renewable_rich_window']['is_renewable_rich']:
        w = res['renewable_rich_window']
        print(f"  Window Time: {w['start_time']} - {w['end_time']} ({w['duration_minutes']} mins)")
        print(f"  Peak Solar: {w['peak_solar_kw']} kW | Avg Solar: {w['average_solar_kw']} kW")
        print(f"  Reason: {w['reason']}")
