import numpy as np
import time
import math
import random
import os
import csv
from datetime import datetime
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.neural_network import MLPRegressor

def load_csv_dataset(filename):
    paths = [
        f"e:/scada/sample_datasets/{filename}",
        f"sample_datasets/{filename}",
        f"../sample_datasets/{filename}",
        f"backend/sample_datasets/{filename}",
        f"e:/scada/scadapro/scada/sample_datasets/{filename}"
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                reader = csv.DictReader(f)
                return list(reader)
    raise FileNotFoundError(f"Could not locate dataset file: {filename}")

def datetime_to_hour(dt_str):
    try:
        dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    except Exception:
        return 12.0

class LSTMLoadForecaster:
    """
    Diurnal Load demand forecaster.
    Implements a sliding-window Auto-Regressive neural model (acting as an LSTM sequence predictor)
    utilizing MLPRegressor to forecast load values.
    """
    def __init__(self):
        self.model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation='tanh',
            max_iter=100,
            random_state=42
        )
        self.window_size = 6
        self._pretrain()

    def _pretrain(self):
        """
        Train the load forecasting neural network on historical load profiles.
        """
        try:
            rows = load_csv_dataset("load_dataset.csv")
            base_load = [float(row["Load_Demand"]) for row in rows]
        except Exception as e:
            print(f"[AI Pretrain Warning] Load CSV fail, fallback synthetic: {e}")
            hours = np.arange(24 * 7)
            diurnal_factor = np.exp(-((hours % 24 - 8.0) / 2.0) ** 2) + 1.55 * np.exp(-((hours % 24 - 19.0) / 3.0) ** 2)
            base_load = list(25.0 + 20.0 * diurnal_factor + np.random.normal(0, 1, len(hours)))
        
        # Prepare sliding window datasets
        X, y = [], []
        for i in range(len(base_load) - self.window_size):
            X.append(base_load[i : i + self.window_size])
            y.append(base_load[i + self.window_size])
        
        X = np.array(X)
        y = np.array(y)
        
        self.model.fit(X, y)
        self.last_load_window = list(base_load[-self.window_size:])

    def predict_next_24h(self, current_load: float) -> list:
        """
        Performs 24-step iterative forecasting using the trained auto-regressive model.
        """
        window = list(self.last_load_window)
        # Shift in the current actual value
        window.pop(0)
        window.append(current_load)
        
        predictions = []
        for step in range(24):
            input_seq = np.array(window).reshape(1, -1)
            pred = self.model.predict(input_seq)[0]
            # Add stochastic variance
            pred += np.random.normal(0, 0.5)
            pred = max(5.0, pred)
            
            predictions.append(pred)
            window.pop(0)
            window.append(pred)
            
        self.last_load_window = window
        return [round(p, 2) for p in predictions]


class XGBoostRenewableForecaster:
    """
    Solar and Wind power generation forecaster utilizing GradientBoosting Regressors.
    """
    def __init__(self):
        self.solar_model = GradientBoostingRegressor(n_estimators=30, random_state=42)
        self.wind_model = GradientBoostingRegressor(n_estimators=30, random_state=42)
        self._pretrain()

    def _pretrain(self):
        # Solar Model: Inputs [Irradiance, Temperature, Humidity, Hour]
        X_solar = []
        y_solar = []
        try:
            rows = load_csv_dataset("solar_dataset.csv")
            for row in rows:
                p = float(row["Solar_Power"])
                t = float(row["Solar_Temperature"])
                hour = datetime_to_hour(row["timestamp"])
                # Synthesize Irradiance: ~12.0 * Power
                irrad = p * 12.0
                # Synthesize Humidity (approx)
                humid = max(20.0, min(95.0, 80.0 - 1.5 * t + random.uniform(-3, 3)))
                X_solar.append([irrad, t, humid, hour])
                y_solar.append(p)
        except Exception as e:
            print(f"[AI Pretrain Warning] Solar CSV pretrain fail: {e}")
            # Fallback synthetic training
            for _ in range(300):
                hour = random.uniform(0, 24)
                cloud = random.uniform(0, 1)
                t = random.uniform(15, 38)
                p = 0.0
                if 6.0 <= hour <= 18.0:
                    p = 100.0 * math.sin(math.pi * (hour - 6.0) / 12.0) * (1.0 - cloud) * (1.0 - 0.004 * (t - 25.0))
                    p = max(0.0, p)
                irrad = p * 12.0
                humid = max(20.0, min(95.0, 80.0 - 1.5 * t))
                X_solar.append([irrad, t, humid, hour])
                y_solar.append(p)

        # Wind Model: Inputs [Wind Speed, Wind Direction, Temperature]
        X_wind = []
        y_wind = []
        try:
            rows = load_csv_dataset("wind_dataset.csv")
            for row in rows:
                p = float(row["Wind_Power"])
                speed = float(row["Wind_Speed"])
                hour = datetime_to_hour(row["timestamp"])
                # Synthesize Wind Direction & Temperature
                direction = (hour * 15.0) % 360.0
                t = max(10.0, min(42.0, 25.0 + 5.0 * math.sin(math.pi * (hour - 8.0) / 12.0)))
                X_wind.append([speed, direction, t])
                y_wind.append(p)
        except Exception as e:
            print(f"[AI Pretrain Warning] Wind CSV pretrain fail: {e}")
            # Fallback synthetic training
            for _ in range(300):
                hour = random.uniform(0, 24)
                speed = random.uniform(0, 25)
                t = random.uniform(15, 38)
                p = 0.0
                if 3.0 <= speed < 12.0:
                    p = 50.0 * ((speed - 3.0) / 9.0) ** 3
                elif 12.0 <= speed <= 25.0:
                    p = 50.0 + random.uniform(-0.5, 0.5)
                direction = (hour * 15.0) % 360.0
                X_wind.append([speed, direction, t])
                y_wind.append(p)

        self.solar_model.fit(X_solar, y_solar)
        self.wind_model.fit(X_wind, y_wind)

    def predict_solar(self, x1: float, x2: float, x3: float, hour: float = None) -> float:
        if hour is None:
            # Old signature: predict_solar(hour, cloud_cover, temp)
            h = x1
            cloud = x2
            temp = x3
            irrad = 0.0
            if 6.0 <= h <= 18.0:
                irrad = 1000.0 * math.sin(math.pi * (h - 6.0) / 12.0) * (1.0 - cloud)
            humid = max(20.0, min(95.0, 80.0 - 1.5 * temp))
        else:
            # New signature: predict_solar(irradiance, temp, humidity, hour)
            irrad = x1
            temp = x2
            humid = x3
            h = hour

        pred = self.solar_model.predict([[irrad, temp, humid, h]])[0]
        return round(max(0.0, pred), 2)

    def predict_wind(self, x1: float, x2: float, x3: float, temp: float = None) -> float:
        if temp is None:
            # Old signature: predict_wind(hour, wind_speed, temp)
            h = x1
            speed = x2
            t = x3
            direction = (h * 15.0) % 360.0
        else:
            # New signature: predict_wind(wind_speed, wind_direction, temp)
            speed = x1
            direction = x2
            t = temp

        pred = self.wind_model.predict([[speed, direction, t]])[0]
        return round(max(0.0, pred), 2)


class BatterySOCPredictor:
    """
    Predicts next step SOC of battery based on current SOC, voltage, current, and temperature.
    """
    def __init__(self):
        self.model = GradientBoostingRegressor(n_estimators=30, random_state=42)
        self._pretrain()

    def _pretrain(self):
        X = []
        y = []
        try:
            rows = load_csv_dataset("battery_dataset.csv")
            for i in range(len(rows) - 1):
                soc = float(rows[i]["Battery_SOC"])
                volt = float(rows[i]["Battery_Voltage"])
                curr = float(rows[i]["Battery_Current"])
                temp = float(rows[i]["Battery_Temperature"])
                next_soc = float(rows[i+1]["Battery_SOC"])
                X.append([soc, volt, curr, temp])
                y.append(next_soc)
        except Exception as e:
            print(f"[AI Pretrain Warning] Battery CSV pretrain fail: {e}")
            # Fallback
            for _ in range(300):
                soc = random.uniform(20, 100)
                volt = 320.0 + 95.0 * (soc / 100.0)
                curr = random.uniform(-40, 40)
                temp = random.uniform(15, 45)
                next_soc = max(0.0, min(soc + (curr * 0.95) / 2.0, 100.0))
                X.append([soc, volt, curr, temp])
                y.append(next_soc)

        self.model.fit(X, y)

    def predict_next_soc(self, soc: float, voltage: float, current: float, temp: float) -> float:
        pred = self.model.predict([[soc, voltage, current, temp]])[0]
        return round(max(0.0, min(pred, 100.0)), 2)


class AnomalyDetector:
    """
    SCADA Data Anomaly Detector utilizing Isolation Forest.
    Analyzes telemetry patterns and flags anomalies (voltage spikes, cell imbalances, sensor dropouts).
    """
    def __init__(self):
        self.detector = IsolationForest(contamination=0.03, random_state=42)
        self._pretrain()

    def _pretrain(self):
        # Train on normal system operating limits
        # Features: [Grid_Voltage, Load_Current, Battery_Temperature, Inverter_Efficiency]
        n_samples = 500
        normal_data = []
        for _ in range(n_samples):
            # Normal grid connected state
            grid_v = random.uniform(380, 420)
            load_c = random.uniform(10, 180)
            batt_t = random.uniform(15, 55)
            inv_eff = random.uniform(84.0, 99.5)
            normal_data.append([grid_v, load_c, batt_t, inv_eff])
            
            # Grid outage state (also normal operation, not a diagnostic anomaly)
            grid_v_out = 0.0
            load_c_out = random.uniform(10, 180)
            batt_t_out = random.uniform(15, 55)
            inv_eff_out = random.uniform(84.0, 99.5)
            normal_data.append([grid_v_out, load_c_out, batt_t_out, inv_eff_out])
            
        self.detector.fit(normal_data)

    def is_anomalous(self, grid_v: float, load_c: float, batt_t: float, inv_eff: float) -> tuple:
        """
        Returns (is_anomalous: bool, anomaly_score: float)
        anomaly_score closer to -1 means highly anomalous.
        """
        feature_vector = np.array([[grid_v, load_c, batt_t, inv_eff]])
        pred = self.detector.predict(feature_vector)[0]
        score = self.detector.decision_function(feature_vector)[0]
        return (pred == -1, round(float(score), 4))


class PredictiveMaintenanceSuite:
    """
    Evaluates health scores, predicts failures, and estimates Remaining Useful Life (RUL)
    of critical hardware assets: battery banks, PCS inverters, and cabinet cooling fans.
    """
    def __init__(self):
        pass

    def compute_asset_health(self, telemetry: dict) -> dict:
        """
        Calculates health scores (0-100%) and Remaining Useful Life (RUL) in hours.
        """
        # 1. Inverter Health (PCS)
        # Affected by heatsink temperature over time and conversion losses
        inv_temp = 40.0 + abs(telemetry.get("Inverter_Output_Power", 0)) * 0.15
        temp_stress = max(0.0, (inv_temp - 50.0) / 30.0) # 0 to 1 scaling up to 80C
        inv_health = max(5.0, 98.2 - temp_stress * 1.5)
        # RUL: Nominal 12000 hours degraded by thermal stress
        inv_rul = 12000.0 * (inv_health / 100.0) * (0.8 if inv_temp > 60.0 else 1.0)
        
        # 2. Battery BESS Health
        # SOH is derived in simulator, cycles accelerate aging
        soc = telemetry.get("Battery_SOC", 50.0)
        batt_temp = telemetry.get("Battery_Temperature", 25.0)
        soh = telemetry.get("Battery_SOH", 99.8)
        # Degradation acceleration under high temperatures
        thermal_degrade = math.exp(0.04 * (batt_temp - 25.0)) if batt_temp > 25.0 else 1.0
        batt_health = max(30.0, soh)
        batt_rul = 6000.0 * (batt_health / 100.0) / thermal_degrade

        # 3. Cooling Fan Health
        # High ambient temperature increases friction degradation
        ambient = telemetry.get("ambient_temp", 25.0)
        fan_stress = max(0.0, (ambient - 25.0) / 20.0)
        fan_health = max(10.0, 95.0 - fan_stress * 5.0)
        fan_rul = 8000.0 * (fan_health / 100.0)

        # 4. Communication Stability Health
        # Random dropouts or active failures decrease stability
        comm_error = 0.0
        if telemetry.get("Inverter_Status", "RUNNING") == "FAULTED":
            comm_error += 25.0
        if telemetry.get("Grid_Status", 1) == 0:
            comm_error += 10.0
        comm_health = max(10.0, 100.0 - comm_error - random.uniform(0, 2))
        comm_rul = 24000.0 * (comm_health / 100.0)

        # Decide maintenance prediction status
        maintenance_needed = []
        if inv_health < 80.0: maintenance_needed.append("PCS Inverter Thermal Service")
        if batt_health < 85.0: maintenance_needed.append("BESS Capacity Rebalancing")
        if fan_health < 75.0: maintenance_needed.append("Cabinet Vent Fan Replacement")
        if comm_health < 80.0: maintenance_needed.append("RTU Gateway Diagnostics")
        
        return {
            "inverter": {
                "health_score": round(inv_health, 1),
                "rul_hours": round(inv_rul, 0),
                "maintenance_required": inv_health < 80.0
            },
            "battery": {
                "health_score": round(batt_health, 2),
                "rul_hours": round(batt_rul, 0),
                "maintenance_required": batt_health < 85.0
            },
            "fan": {
                "health_score": round(fan_health, 1),
                "rul_hours": round(fan_rul, 0),
                "maintenance_required": fan_health < 75.0
            },
            "communication": {
                "health_score": round(comm_health, 1),
                "rul_hours": round(comm_rul, 0),
                "maintenance_required": comm_health < 80.0
            },
            "next_scheduled_maintenance": maintenance_needed[0] if maintenance_needed else "System Nominal (No Action Required)"
        }


# Global Singletons
load_forecaster = LSTMLoadForecaster()
renewable_forecaster = XGBoostRenewableForecaster()
battery_forecaster = BatterySOCPredictor()
anomaly_detector = AnomalyDetector()
maintenance_suite = PredictiveMaintenanceSuite()
