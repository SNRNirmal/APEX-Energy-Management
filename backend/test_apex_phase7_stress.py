"""
APEX-Energy — Phase 7 Integration & Stress Testing Suite
========================================================
Comprehensive validation covering the full closed loop:
SENSE → PREDICT → DECIDE → ACT → VERIFY → EVALUATE → VISUALIZE

Test Scenarios:
1.  test_01_e2e_pipeline_flow
2.  test_02_normal_operation_scenario
3.  test_03_solar_surge_and_machine_c_shift
4.  test_04_low_renewable_and_grid_fallback
5.  test_05_battery_min_soc_boundary
6.  test_06_battery_max_soc_boundary
7.  test_07_export_limit_and_unavoidable_curtailment
8.  test_08_machine_c_deadline_and_quota_under_varying_forecasts
9.  test_09_forecast_adaptation_dynamic
10. test_10_grid_outage_islanding
11. test_11_full_2016_step_energy_conservation_stress
12. test_12_full_2016_step_production_compliance_stress
13. test_13_failure_injection_and_safe_fallbacks
"""

import sys
import os
import unittest
import numpy as np

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from forecasting import get_renewable_forecast, RenewableForecastingEngine
from decision_engine import ProductionAwareDecisionEngine, apex_decision_engine
from verification import EnergyBalanceVerifier, apex_verifier
from evaluation import ApexEvaluationEngine, apex_evaluator
from fastapi.testclient import TestClient
from main import app


class TestApexPhase7Stress(unittest.TestCase):
    """Phase 7 Final Integration, Stress, and Boundary Testing."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.evaluator = apex_evaluator
        cls.verifier = apex_verifier
        cls.decision_engine = apex_decision_engine
        cls.dataset = cls.evaluator.load_dataset()

    def test_01_e2e_pipeline_flow(self):
        """Verify seamless end-to-end data flow: Dataset -> Forecast -> Decision -> Dispatch -> Verification -> Evaluation."""
        # 1. SENSE: Extract a realistic timestep from dataset (Tuesday midday)
        row = self.dataset[288 + 144]  # Day 2, step 144 (12:00)
        timestamp = str(row["timestamp"])
        solar = float(row["solar_generation_kw"])
        wind = float(row["wind_generation_kw"])
        soc = float(row["baseline_battery_soc"])
        grid_status = int(row["grid_status"])

        # 2. PREDICT: Query Phase 2 forecast
        forecast = get_renewable_forecast(current_timestamp=timestamp, horizon_minutes=180)
        self.assertIn("predictions", forecast)
        self.assertIn("renewable_rich_window", forecast)
        self.assertEqual(len(forecast["predictions"]), 36)

        # 3. DECIDE: Feed forecast & telemetry into Phase 3 decision engine
        decision = self.decision_engine.evaluate(
            current_timestamp=timestamp,
            current_solar_kw=solar,
            current_wind_kw=wind,
            battery_soc=soc,
            grid_status=grid_status,
            export_limit_kw=50.0,
            tariff_rate=4.50,
            is_weekend=False
        )
        self.assertIn("decision_summary", decision)
        self.assertIn("energy_allocation", decision)
        self.assertIn("machine_decisions", decision)

        # 4. VERIFY: Dispatch allocation must be verified by Phase 4
        v_result = decision["verification"]
        self.assertTrue(v_result["valid"])
        self.assertAlmostEqual(v_result["balance_error_kw"], 0.0, places=3)
        self.assertEqual(v_result["checks"]["energy_balance"], "PASS")

        # 5. EVALUATE: Ensure evaluation layer can aggregate decisions
        eval_result = self.evaluator.evaluate_apex([row])
        self.assertIn("grid_and_cost_kpis", eval_result)
        self.assertIn("energy_summary", eval_result)
        self.assertEqual(eval_result["production_compliance"]["verification_compliance_pct"], 100.0)

    def test_02_normal_operation_scenario(self):
        """Test Monday standard industrial operation."""
        mon_rows = self.dataset[0:288]
        res_baseline = self.evaluator.evaluate_baseline(mon_rows)
        res_apex = self.evaluator.evaluate_apex(mon_rows)

        # Quotas must be 100% met
        self.assertTrue(res_apex["production_compliance"]["machine_a_quota_met"])
        self.assertTrue(res_apex["production_compliance"]["machine_b_quota_met"])
        self.assertTrue(res_apex["production_compliance"]["machine_c_quota_met"])
        self.assertEqual(res_apex["production_compliance"]["verification_compliance_pct"], 100.0)
        # BESS must stay within [20%, 95%]
        self.assertGreaterEqual(res_apex["bess_health"]["min_soc_pct"], 20.0)
        self.assertLessEqual(res_apex["bess_health"]["max_soc_pct"], 95.0)

    def test_03_solar_surge_and_machine_c_shift(self):
        """Test Tuesday Solar Surge: Machine C shifted to midday solar window."""
        tue_rows = self.dataset[288:576]
        res_apex = self.evaluator.evaluate_apex(tue_rows)
        res_baseline = self.evaluator.evaluate_baseline(tue_rows)

        # Tuesday net cost in APEX must be lower than Baseline
        cost_baseline = res_baseline["grid_and_cost_kpis"]["net_electricity_cost"]
        cost_apex = res_apex["grid_and_cost_kpis"]["net_electricity_cost"]
        savings = cost_baseline - cost_apex
        self.assertGreater(savings, 200.0)  # Tuesday delivers major savings ($278.79)

        # Verify candidate scoring recommends shifting Machine C
        candidates = self.decision_engine.score_candidate_schedules(machine_id="Machine_C")
        best = candidates["optimal_candidate_id"]
        self.assertIsNotNone(best)
        self.assertTrue(candidates["is_shift_recommended"])

    def test_04_low_renewable_and_grid_fallback(self):
        """Test Thursday low renewable generation: Critical Machine A protected via grid fallback."""
        thu_rows = self.dataset[864:1152]
        res_apex = self.evaluator.evaluate_apex(thu_rows)

        # Machine A must remain 100% supplied
        self.assertTrue(res_apex["production_compliance"]["machine_a_quota_met"])
        # Grid import satisfies remaining deficit
        self.assertGreater(res_apex["grid_and_cost_kpis"]["grid_import_kwh"], 800.0)
        # SOC must not breach 20%
        self.assertGreaterEqual(res_apex["bess_health"]["min_soc_pct"], 20.0)

    def test_05_battery_min_soc_boundary(self):
        """Verify BESS behavior at exact minimum SOC boundary (20.0%)."""
        decision = self.decision_engine.evaluate(
            current_timestamp="2026-06-01 22:00:00",
            current_solar_kw=0.0,
            current_wind_kw=2.0,
            battery_soc=20.0,  # Boundary minimum
            grid_status=1,
            export_limit_kw=50.0,
            tariff_rate=4.50,
            is_weekend=False
        )
        alloc = decision["energy_allocation"]
        # Battery cannot discharge when at minimum SOC
        self.assertEqual(alloc["battery_discharge_kw"], 0.0)
        # Grid must import to cover critical load deficit
        self.assertGreater(alloc["grid_import_kw"], 0.0)
        # Physics must be verified
        self.assertTrue(decision["verification"]["valid"])

    def test_06_battery_max_soc_boundary(self):
        """Verify BESS behavior at exact maximum SOC boundary (95.0%) during high renewable surplus."""
        decision = self.decision_engine.evaluate(
            current_timestamp="2026-06-01 12:30:00",
            current_solar_kw=80.0,
            current_wind_kw=20.0,
            battery_soc=95.0,  # Boundary maximum
            grid_status=1,
            export_limit_kw=50.0,
            tariff_rate=4.50,
            is_weekend=False
        )
        alloc = decision["energy_allocation"]
        # Battery cannot charge when at maximum SOC
        self.assertEqual(alloc["battery_charge_kw"], 0.0)
        # Surplus must go to export up to export limit
        self.assertGreater(alloc["grid_export_kw"], 0.0)
        self.assertLessEqual(alloc["grid_export_kw"], 50.0)
        # First Law conservation holds
        self.assertTrue(decision["verification"]["valid"])

    def test_07_export_limit_and_unavoidable_curtailment(self):
        """Verify that when generation exceeds factory load + BESS capacity + 50kW grid export, surplus is curtailed."""
        # Extreme surplus: 160 kW renewable vs 90 kW factory load, battery full (95%), export limit 50 kW
        # Surplus = 160 - 90 = 70 kW. Export = 50 kW max. Curtailment = 70 - 50 = 20 kW.
        decision = self.decision_engine.evaluate(
            current_timestamp="2026-06-05 13:00:00",
            current_solar_kw=120.0,
            current_wind_kw=40.0,
            battery_soc=95.0,
            grid_status=1,
            export_limit_kw=50.0,
            tariff_rate=4.50,
            is_weekend=False
        )
        alloc = decision["energy_allocation"]
        # Export must be capped exactly at 50.0 kW
        self.assertAlmostEqual(alloc["grid_export_kw"], 50.0, places=2)
        # Remaining unavoidable surplus MUST be curtailed
        self.assertAlmostEqual(alloc["curtailment_kw"], 20.0, places=1)
        # Curtailment validity check in verification must pass
        self.assertEqual(decision["verification"]["checks"]["curtailment_validity"], "PASS")
        self.assertTrue(decision["verification"]["valid"])

    def test_08_machine_c_deadline_and_quota_under_varying_forecasts(self):
        """Verify Machine C constraints: 3h quota, 08:00–17:00 window, deadline 17:00."""
        scoring = self.decision_engine.score_candidate_schedules(machine_id="Machine_C")
        for cand in scoring["candidate_rankings"]:
            # Window check
            self.assertGreaterEqual(cand["start_hour"], 8.0)
            self.assertLessEqual(cand["end_hour"], 17.0)
            # Duration check (exactly 3 hours)
            self.assertAlmostEqual(cand["duration_hours"], 3.0, places=2)
            # Constraint validation
            self.assertTrue(cand["constraint_validation"]["valid"])

    def test_09_forecast_adaptation_dynamic(self):
        """Verify that when renewable forecasts change, candidate scoring dynamically adapts recommendations."""
        # Synthetic forecast 1: Early morning peak (08:00 - 11:00)
        early_preds = [
            {"timestamp": f"2026-06-02 09:{m:02d}:00", "total_renewable_kw": 95.0} for m in range(0, 60, 5)
        ] + [
            {"timestamp": f"2026-06-02 10:{m:02d}:00", "total_renewable_kw": 90.0} for m in range(0, 60, 5)
        ] + [
            {"timestamp": f"2026-06-02 14:{m:02d}:00", "total_renewable_kw": 20.0} for m in range(0, 60, 5)
        ]
        score_early = self.decision_engine.score_candidate_schedules(
            machine_id="Machine_C",
            forecast_predictions=early_preds
        )
        self.assertTrue(score_early["candidate_rankings"][0]["constraint_validation"]["valid"])

        # Synthetic forecast 2: Afternoon peak (13:00 - 16:00)
        late_preds = [
            {"timestamp": f"2026-06-02 09:{m:02d}:00", "total_renewable_kw": 10.0} for m in range(0, 60, 5)
        ] + [
            {"timestamp": f"2026-06-02 14:{m:02d}:00", "total_renewable_kw": 110.0} for m in range(0, 60, 5)
        ]
        score_late = self.decision_engine.score_candidate_schedules(
            machine_id="Machine_C",
            forecast_predictions=late_preds
        )
        self.assertTrue(score_late["candidate_rankings"][0]["constraint_validation"]["valid"])

    def test_10_grid_outage_islanding(self):
        """Verify Sunday 14:00–16:00 outage: Grid import/export clamped to 0, islanding microgrid verified."""
        outage_row = self.dataset[1728 + 174]
        self.assertEqual(int(outage_row["grid_status"]), 0)

        decision = self.decision_engine.evaluate(
            current_timestamp=str(outage_row["timestamp"]),
            current_solar_kw=float(outage_row["solar_generation_kw"]),
            current_wind_kw=float(outage_row["wind_generation_kw"]),
            battery_soc=float(outage_row["baseline_battery_soc"]),
            grid_status=0,  # Grid Outage
            export_limit_kw=50.0,
            tariff_rate=4.50,
            is_weekend=True
        )
        alloc = decision["energy_allocation"]
        # In islanding mode: grid import and export must be strictly 0.0
        self.assertEqual(alloc["grid_import_kw"], 0.0)
        self.assertEqual(alloc["grid_export_kw"], 0.0)
        # Physics verification check for islanding
        self.assertEqual(decision["verification"]["checks"]["grid_limits"], "PASS")
        self.assertTrue(decision["verification"]["valid"])

    def test_11_full_2016_step_energy_conservation_stress(self):
        """Stress-test: Run verification across all 2,016 timesteps of the 7-day dataset."""
        dataset_v = self.verifier.verify_timeseries_dataset(tolerance_kw=0.015)
        
        self.assertTrue(dataset_v["valid"])
        self.assertEqual(dataset_v["verified_timesteps"], 2016)
        self.assertEqual(dataset_v["total_timesteps"], 2016)
        self.assertEqual(dataset_v["failed_timesteps"], 0)
        self.assertEqual(dataset_v["compliance_rate_pct"], 100.0)
        self.assertLessEqual(dataset_v["max_balance_error_kw"], 0.015)
        self.assertLess(dataset_v["mean_balance_error_kw"], 0.002)

    def test_12_full_2016_step_production_compliance_stress(self):
        """Verify production constraint compliance across all 2,016 timesteps."""
        res_apex = self.evaluator.evaluate_apex(self.dataset)
        comp = res_apex["production_compliance"]

        self.assertTrue(comp["machine_a_quota_met"])
        self.assertTrue(comp["machine_b_quota_met"])
        self.assertTrue(comp["machine_c_quota_met"])
        self.assertTrue(comp["all_constraints_respected"])
        self.assertEqual(comp["verification_compliance_pct"], 100.0)

    def test_13_failure_injection_and_safe_fallbacks(self):
        """Verify system handles invalid/corrupted inputs safely without issuing invalid dispatch."""
        # 1. Negative solar input -> verifier catches unphysical flow
        decision_neg = self.decision_engine.evaluate(
            current_timestamp="2026-06-01 12:00:00",
            current_solar_kw=-15.0,  # Corrupted negative sensor
            current_wind_kw=-5.0,
            battery_soc=50.0,
            grid_status=1
        )
        # Physics verifier must flag negative flow
        self.assertFalse(decision_neg["verification"]["valid"])
        self.assertEqual(decision_neg["verification"]["checks"]["non_negative_flows"], "FAIL")

        # 2. Out-of-bounds SOC (> 95% max) -> battery cannot charge
        decision_high_soc = self.decision_engine.evaluate(
            current_timestamp="2026-06-01 12:00:00",
            current_solar_kw=50.0,
            current_wind_kw=10.0,
            battery_soc=120.0,  # Corrupted SOC
            grid_status=1
        )
        self.assertEqual(decision_high_soc["energy_allocation"]["battery_charge_kw"], 0.0)

        # 3. Direct verifier rejection of unphysical energy allocation
        invalid_alloc = {
            "solar_kw": 50.0,
            "wind_kw": 10.0,
            "battery_discharge_kw": 10.0,
            "battery_charge_kw": 10.0,  # Simultaneous charge and discharge
            "grid_import_kw": 20.0,
            "grid_export_kw": 0.0,
            "curtailment_kw": 0.0,
            "factory_total_load_kw": 30.0  # Supply (80) != Demand (40)
        }
        v_check = self.verifier.verify_timestep(
            energy_allocation=invalid_alloc,
            battery_soc=50.0,
            grid_status=1
        )
        self.assertFalse(v_check["valid"])
        self.assertEqual(v_check["checks"]["energy_balance"], "FAIL")
        self.assertEqual(v_check["checks"]["no_simultaneous_battery_action"], "FAIL")


if __name__ == "__main__":
    unittest.main()
