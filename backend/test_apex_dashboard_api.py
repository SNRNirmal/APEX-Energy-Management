"""
APEX-Energy — Phase 6 Integration Test Suite
============================================
Validates all backend API endpoints and data contracts consumed by the Phase 6
SCADA-style Energy Management Dashboard (ApexDashboard.jsx).

Endpoints Tested:
1. GET /api/scenario/details (day_index=0..6, 24h trajectory, representative decisions)
2. GET /api/evaluation/compare (Phase 5 7-day cumulative benchmark)
3. GET /api/evaluation/kpis (Phase 5 summary cards)
4. GET /api/forecast/renewable (Phase 2 renewable forecasting)
5. GET /api/decision/evaluate (Phase 3 production-aware decision engine)
6. GET /api/verification/status (Phase 4 real-time physics verification)
7. GET /api/verification/dataset (Phase 4 full 2,016-step dataset verification)
"""

import sys
import os
import unittest

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app


class TestApexDashboardAPI(unittest.TestCase):
    """Integration test suite for Phase 6 Dashboard API contract."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_scenario_details_default(self):
        """Test GET /api/scenario/details returns default Day 1 trajectory and summary."""
        res = self.client.get("/api/scenario/details")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("day_index", data)
        self.assertEqual(data["day_index"], 0)
        self.assertIn("scenario_title", data)
        self.assertIn("scenario_tag", data)
        self.assertIn("time_series_curve", data)
        self.assertIn("baseline_summary", data)
        self.assertIn("apex_summary", data)
        self.assertIn("representative_decision", data)
        
        # 48 30-min points across 24h
        traj = data["time_series_curve"]
        self.assertEqual(len(traj), 48)
        self.assertEqual(traj[0]["time"], "00:00")
        self.assertIn("solar_kw", traj[0])
        self.assertIn("wind_kw", traj[0])
        self.assertIn("total_renewable_kw", traj[0])
        self.assertIn("baseline_load_kw", traj[0])
        self.assertIn("grid_import_kw", traj[0])

    def test_02_scenario_details_solar_surge(self):
        """Test GET /api/scenario/details?day_index=1 returns Day 2 Solar Surge details."""
        res = self.client.get("/api/scenario/details?day_index=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(data["day_index"], 1)
        self.assertIn("Solar Surge", data["scenario_title"])
        
        # Representative decision must include Machine C recommendation
        rep_dec = data["representative_decision"]
        self.assertIn("decision_summary", rep_dec)
        self.assertIn("machine_decisions", rep_dec)
        self.assertIn("schedule_optimization", rep_dec)
        self.assertTrue(rep_dec["schedule_optimization"]["is_shift_recommended"])

    def test_03_scenario_details_grid_outage(self):
        """Test GET /api/scenario/details?day_index=6 returns Day 7 Grid Outage scenario."""
        res = self.client.get("/api/scenario/details?day_index=6")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(data["day_index"], 6)
        self.assertIn("Grid Outage", data["scenario_title"])

    def test_04_evaluation_compare_contract(self):
        """Test GET /api/evaluation/compare returns complete Phase 5 benchmark results."""
        res = self.client.get("/api/evaluation/compare")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("cumulative_kpi_comparison", data)
        self.assertIn("daily_scenario_breakdown", data)
        self.assertIn("key_takeaways", data)
        
        kpis = data["cumulative_kpi_comparison"]
        # Verify specific validated values
        self.assertAlmostEqual(kpis["net_cost"]["delta"], 89.55, places=2)
        self.assertAlmostEqual(kpis["renewable_curtailment"]["delta"], 23.78, places=1)
        self.assertEqual(data["apex_full"]["production_compliance"]["all_constraints_respected"], True)

    def test_05_evaluation_kpis_endpoint(self):
        """Test GET /api/evaluation/kpis returns summary KPI cards."""
        res = self.client.get("/api/evaluation/kpis")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("cumulative_kpi_comparison", data)
        self.assertIn("key_takeaways", data)
        self.assertIn("dataset_info", data)

    def test_06_forecast_renewable_endpoint(self):
        """Test GET /api/forecast/renewable returns short-term horizon & rich window."""
        res = self.client.get("/api/forecast/renewable?horizon_minutes=180")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("horizon_minutes", data)
        self.assertIn("renewable_rich_window", data)
        self.assertIn("predictions", data)
        self.assertEqual(len(data["predictions"]), 36)

    def test_07_decision_evaluate_endpoint(self):
        """Test GET /api/decision/evaluate returns structured Phase 3 decision."""
        res = self.client.get(
            "/api/decision/evaluate",
            params={
                "solar_kw": 45.0,
                "wind_kw": 18.0,
                "battery_soc": 55.0,
                "grid_status": 1,
                "export_limit_kw": 50.0,
                "tariff_rate": 4.50
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("decision_summary", data)
        self.assertIn("machine_decisions", data)
        self.assertIn("energy_allocation", data)
        self.assertIn("verification", data)
        self.assertIn("schedule_optimization", data)

    def test_08_verification_status_endpoint(self):
        """Test GET /api/verification/status validates current live telemetry state."""
        res = self.client.get("/api/verification/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("valid", data)
        self.assertIn("balance_error_kw", data)
        self.assertIn("supply_total_kw", data)
        self.assertIn("demand_total_kw", data)
        self.assertIn("checks", data)


if __name__ == "__main__":
    unittest.main()
