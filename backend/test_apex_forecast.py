"""
APEX-Energy: Phase 2 Forecasting Test & Verification Suite
==========================================================
Verifies:
1. Phase 1 Dataset Loading & Target Integrity
2. Strict Chronological Train/Test Split (No Data Leakage)
3. Model Training (Gradient Boosting & MLP)
4. Prediction Physical Sanity (Non-negative, Nighttime zeroing, Capacity limits)
5. Evaluation Metrics (MAE & RMSE for Solar and Wind)
6. Renewable-Rich Window Detection (Surge identification)
7. Determinism & Reproducibility
8. Clean Phase 3 Function Contract
"""

import os
import unittest
import numpy as np
from forecasting import RenewableForecastingEngine, get_renewable_forecast

class TestApexForecasting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RenewableForecastingEngine(seed=42)

    def test_dataset_loading_and_targets(self):
        """Verify Phase 1 dataset loads with valid targets."""
        self.assertTrue(os.path.exists(self.engine.dataset_path))
        rows = self.engine._load_dataset()
        self.assertEqual(len(rows), 2016, "Expected 2016 rows from Phase 1 dataset")
        
        # Verify target fields exist and have no NaNs
        for r in rows:
            self.assertIn("solar_generation_kw", r)
            self.assertIn("wind_generation_kw", r)
            self.assertFalse(np.isnan(float(r["solar_generation_kw"])))
            self.assertFalse(np.isnan(float(r["wind_generation_kw"])))

    def test_chronological_split_no_leakage(self):
        """Verify chronological ordering is preserved and train comes strictly before test."""
        rows = self.engine._load_dataset()
        X, y_s, y_w, timestamps, _, _, _ = self.engine._extract_features_and_targets(rows)
        
        split_idx = int(len(X) * 0.75)
        train_timestamps = timestamps[:split_idx]
        test_timestamps = timestamps[split_idx:]
        
        # Verify split points
        self.assertGreater(len(train_timestamps), 1000)
        self.assertGreater(len(test_timestamps), 300)
        
        # Verify latest training timestamp is strictly earlier than earliest test timestamp
        self.assertLess(train_timestamps[-1], test_timestamps[0], 
                        f"Data leakage! Train end {train_timestamps[-1]} >= Test start {test_timestamps[0]}")

    def test_model_training_and_metrics(self):
        """Verify models train and produce valid MAE and RMSE metrics."""
        metrics = self.engine.metrics
        self.assertIn("solar", metrics)
        self.assertIn("wind", metrics)
        
        # Solar metrics
        s_m = metrics["solar"]
        self.assertGreater(s_m["baseline_mae"], 0.0)
        self.assertGreater(s_m["gb_mae"], 0.0)
        self.assertGreater(s_m["mlp_mae"], 0.0)
        
        # Gradient Boosting must outperform naive persistence baseline
        self.assertLess(s_m["gb_mae"], s_m["baseline_mae"], 
                        f"GB Solar MAE ({s_m['gb_mae']}) should improve over baseline ({s_m['baseline_mae']})")
        self.assertLess(s_m["gb_rmse"], s_m["baseline_rmse"], 
                        f"GB Solar RMSE ({s_m['gb_rmse']}) should improve over baseline ({s_m['baseline_rmse']})")

        # Wind metrics
        w_m = metrics["wind"]
        self.assertLess(w_m["gb_mae"], w_m["baseline_mae"])

    def test_physical_sanity_constraints(self):
        """Verify predictions never produce negative generation or exceed physical capacities."""
        res = self.engine.predict_multi_step("2026-06-03 10:00:00", horizon_minutes=180)
        for p in res["predictions"]:
            solar = p["solar_generation_kw"]
            wind = p["wind_generation_kw"]
            self.assertGreaterEqual(solar, 0.0, f"Negative solar power: {solar}")
            self.assertLessEqual(solar, 100.0, f"Solar exceeds maximum capacity (100 kW): {solar}")
            self.assertGreaterEqual(wind, 0.0, f"Negative wind power: {wind}")
            self.assertLessEqual(wind, 50.0, f"Wind exceeds maximum capacity (50 kW): {wind}")

        # Test nighttime prediction at 23:00
        res_night = self.engine.predict_multi_step("2026-06-03 23:00:00", horizon_minutes=60)
        for p in res_night["predictions"]:
            self.assertEqual(p["solar_generation_kw"], 0.0, "Nighttime solar must strictly be 0.0 kW")

    def test_renewable_rich_window_detection(self):
        """Verify solar surge during midday is detected as a renewable-rich window."""
        # Query at 10:00 AM on Day 2 (Wednesday surge opportunity)
        res = self.engine.predict_multi_step("2026-06-03 10:00:00", horizon_minutes=180)
        window = res["renewable_rich_window"]
        
        self.assertTrue(window["is_renewable_rich"], "Expected renewable-rich window to be detected")
        self.assertGreater(window["duration_minutes"], 60, "Expected window to span at least 1 hour")
        self.assertGreaterEqual(window["peak_solar_kw"], 50.0, "Peak solar must exceed 50 kW")
        self.assertIn("recommendation", window)

    def test_phase3_contract(self):
        """Verify clean function contract for Phase 3 decision engine."""
        res = get_renewable_forecast("2026-06-03 10:00:00", horizon_minutes=120)
        self.assertIn("forecast_generated_at", res)
        self.assertIn("horizon_minutes", res)
        self.assertIn("predictions", res)
        self.assertIn("renewable_rich_window", res)
        self.assertEqual(len(res["predictions"]), 24) # 120 mins / 5 min = 24 steps

    def test_reproducibility(self):
        """Verify that identical random seeds produce identical forecasts."""
        engine_a = RenewableForecastingEngine(seed=42)
        res_a = engine_a.predict_multi_step("2026-06-03 10:00:00", horizon_minutes=60)
        
        engine_b = RenewableForecastingEngine(seed=42)
        res_b = engine_b.predict_multi_step("2026-06-03 10:00:00", horizon_minutes=60)
        
        for pa, pb in zip(res_a["predictions"], res_b["predictions"]):
            self.assertEqual(pa["solar_generation_kw"], pb["solar_generation_kw"])
            self.assertEqual(pa["wind_generation_kw"], pb["wind_generation_kw"])

if __name__ == "__main__":
    unittest.main()
