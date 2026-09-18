"""
APEX-Energy: Phase 3 Decision Engine Test Suite
================================================
Comprehensive verification of:
- Test 1: Critical Machine Protection (Machine A uninterruptible/non-shiftable)
- Test 2: Flexible Machine Constraint Validation (Machine C window, duration, deadline)
- Test 3: Dynamic Renewable-Rich Scheduling (Derived candidate selection vs baseline)
- Test 4: Dynamic Adaptability to Changing Forecast Conditions
- Test 5: Decision Hierarchy (Surplus -> BESS Charge -> Grid Export -> Curtailment)
- Test 6: Deficit Hierarchy & BESS Depletion Protection
- Test 7: Explainability and Structured Contract Integrity
"""

import sys
import os
import unittest
from datetime import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from decision_engine import ProductionConstraintChecker, ProductionAwareDecisionEngine


class TestApexDecisionEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ProductionAwareDecisionEngine()
        cls.checker = ProductionConstraintChecker()

    # ----------------------------------------------------------------
    # TEST 1: Critical Machine Protection (Machine A)
    # ----------------------------------------------------------------
    def test_critical_machine_protection(self):
        """
        Machine A is a critical continuous load (25 kW).
        It must NOT be arbitrarily shifted or interrupted.
        """
        # Constraint checker rejects shifting Machine A
        shift_attempt = self.checker.validate_schedule("Machine_A", start_hour=8.0, end_hour=16.0)
        self.assertFalse(shift_attempt["valid"])
        self.assertEqual(shift_attempt["checks"]["criticality_protection"], "FAIL")
        self.assertTrue(any("CRITICAL" in v for v in shift_attempt["violations"]))

        # Valid continuous schedule passes
        valid_continuous = self.checker.validate_schedule("Machine_A", start_hour=0.0, end_hour=24.0)
        self.assertTrue(valid_continuous["valid"])
        self.assertEqual(valid_continuous["checks"]["criticality_protection"], "PASS")

        # In real-time decision evaluation, Machine A must always be RUNNING (25 kW) on weekdays
        decision = self.engine.evaluate(
            current_timestamp="2026-06-03 11:00:00",
            current_solar_kw=50.0,
            current_wind_kw=10.0,
            battery_soc=60.0,
            is_weekend=False
        )
        m_a = decision["machine_decisions"]["Machine_A"]
        self.assertEqual(m_a["action"], "RUN")
        self.assertEqual(m_a["power_kw"], 25.0)
        self.assertEqual(m_a["constraints"], "PASS")
        self.assertIn("CRITICAL", m_a["reason"])

    # ----------------------------------------------------------------
    # TEST 2: Flexible Machine Feasibility (Machine C Constraints)
    # ----------------------------------------------------------------
    def test_flexible_machine_constraints(self):
        """
        Machine C requires:
        - 3.0 hours continuous runtime
        - Operating window: 08:00 - 17:00
        - Hard deadline: 17:00
        """
        # Case A: Valid schedule within bounds (09:00 - 12:00 baseline)
        v_baseline = self.checker.validate_schedule("Machine_C", start_hour=9.0, end_hour=12.0)
        self.assertTrue(v_baseline["valid"])
        self.assertEqual(v_baseline["checks"]["operating_window"], "PASS")
        self.assertEqual(v_baseline["checks"]["required_duration"], "PASS")
        self.assertEqual(v_baseline["checks"]["deadline_compliance"], "PASS")

        # Case B: Valid APEX shifted candidate (12:00 - 15:00)
        v_shifted = self.checker.validate_schedule("Machine_C", start_hour=12.0, end_hour=15.0)
        self.assertTrue(v_shifted["valid"])

        # Case C: Valid late candidate ending right at deadline (14:00 - 17:00)
        v_deadline = self.checker.validate_schedule("Machine_C", start_hour=14.0, end_hour=17.0)
        self.assertTrue(v_deadline["valid"])

        # Case D: VIOLATION - Exceeding deadline (15:00 - 18:00)
        v_over_deadline = self.checker.validate_schedule("Machine_C", start_hour=15.0, end_hour=18.0)
        self.assertFalse(v_over_deadline["valid"])
        self.assertEqual(v_over_deadline["checks"]["deadline_compliance"], "FAIL")
        self.assertTrue(any("deadline" in v.lower() for v in v_over_deadline["violations"]))

        # Case E: VIOLATION - Starting before operating window (07:00 - 10:00)
        v_too_early = self.checker.validate_schedule("Machine_C", start_hour=7.0, end_hour=10.0)
        self.assertFalse(v_too_early["valid"])
        self.assertEqual(v_too_early["checks"]["operating_window"], "FAIL")

        # Case F: VIOLATION - Insufficient or excessive duration (2 hours instead of 3)
        v_wrong_duration = self.checker.validate_schedule("Machine_C", start_hour=10.0, end_hour=12.0)
        self.assertFalse(v_wrong_duration["valid"])
        self.assertEqual(v_wrong_duration["checks"]["required_duration"], "FAIL")

    # ----------------------------------------------------------------
    # TEST 3: Dynamic Renewable-Rich Scheduling
    # ----------------------------------------------------------------
    def test_renewable_rich_candidate_selection(self):
        """
        Given typical high midday solar generation, the candidate scoring algorithm
        must evaluate all feasible windows and dynamically prefer a midday renewable-rich
        window over the morning baseline (09:00 - 12:00).
        Selection is strictly derived from scores, never hardcoded.
        """
        scoring = self.engine.score_candidate_schedules(machine_id="Machine_C")
        self.assertIn("candidate_rankings", scoring)
        self.assertGreater(len(scoring["candidate_rankings"]), 5)

        rankings = scoring["candidate_rankings"]
        optimal = rankings[0]
        baseline = next(c for c in rankings if c["is_baseline_schedule"])

        # Optimal candidate score must exceed baseline score
        self.assertGreater(optimal["composite_score"], baseline["composite_score"])
        # Renewable coverage of optimal must be higher or equal
        self.assertGreaterEqual(optimal["renewable_coverage_pct"], baseline["renewable_coverage_pct"])
        # Optimal candidate must respect all constraints
        self.assertTrue(optimal["constraint_validation"]["valid"])
        self.assertLessEqual(optimal["end_hour"], 17.0)

        # Confirm shift recommended
        self.assertTrue(scoring["is_shift_recommended"])
        self.assertNotEqual(optimal["candidate_id"], baseline["candidate_id"])

    # ----------------------------------------------------------------
    # TEST 4: Dynamic Adaptability to Forecast Changes
    # ----------------------------------------------------------------
    def test_dynamic_adaptability_when_forecast_changes(self):
        """
        If weather conditions change such that renewables are high in the MORNING
        and low at MIDDAY (e.g. heavy afternoon storm), the engine must dynamically
        select the morning window and NOT the midday window.
        """
        # Synthetic forecast: High morning wind/solar (08:00 - 11:30), storm at midday
        morning_rich_forecast = []
        base_dt = datetime(2026, 6, 3, 8, 0, 0)
        for step in range(108): # 9 hours at 5-min intervals: 08:00 to 17:00
            t = base_dt + step * (base_dt.resolution * 300) # +5 mins
            cur_h = t.hour + t.minute / 60.0
            
            # High generation from 08:00 to 11:00 (120 kW), storm after 11:00 (10 kW)
            if 8.0 <= cur_h <= 11.0:
                gen_kw = 125.0
            else:
                gen_kw = 12.0
            
            morning_rich_forecast.append({
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                "total_renewable_kw": gen_kw
            })

        scoring = self.engine.score_candidate_schedules(
            machine_id="Machine_C",
            forecast_predictions=morning_rich_forecast
        )

        optimal = scoring["candidate_rankings"][0]
        # Should dynamically pick the morning window (start hour between 8.0 and 8.5)
        self.assertLessEqual(optimal["start_hour"], 8.5)
        self.assertEqual(optimal["start_time"], "08:00")
        self.assertIn("WINDOW_0800", optimal["candidate_id"])

    # ----------------------------------------------------------------
    # TEST 5: Decision Hierarchy (Surplus -> BESS -> Grid Export -> Curtailment)
    # ----------------------------------------------------------------
    def test_decision_hierarchy_surplus_bess_export_curtailment(self):
        """
        Tests the 4-tier surplus hierarchy:
        Local Load -> BESS Charge -> Grid Export -> Unavoidable Curtailment.
        """
        # Factory demand: Machine A (25) + Machine B (20) + Machine C idle (0) + Aux (10) = 55 kW
        # Renewable: 165 kW (Surplus = 110 kW)
        # BESS SOC: 50% (can absorb up to 50 kW max charge)
        # Export limit: 40 kW
        # Unavoidable Curtailment should be: 110 - 50 (BESS) - 40 (Export) = 20 kW
        decision = self.engine.evaluate(
            current_timestamp="2026-06-03 10:00:00",
            current_solar_kw=150.0,
            current_wind_kw=15.0,
            battery_soc=50.0,
            grid_status=1,
            export_limit_kw=40.0
        )
        
        summary = decision["decision_summary"]
        self.assertEqual(summary["battery_action"], "CHARGE")
        self.assertEqual(summary["battery_power_target_kw"], 50.0) # BESS capped at 50 kW max
        self.assertEqual(summary["grid_action"], "EXPORT")
        self.assertEqual(summary["grid_power_target_kw"], -40.0)   # Grid export capped at 40 kW limit
        self.assertEqual(summary["curtailment_kw"], 20.0)         # 20 kW curtailment

        # Verify curtailment explanation exists
        curtail_reasons = [e for e in decision["explanations"] if "Curtailing" in e]
        self.assertTrue(len(curtail_reasons) > 0)
        self.assertIn("20.0 kW", curtail_reasons[0])

    # ----------------------------------------------------------------
    # TEST 6: Deficit Hierarchy & BESS Depletion Protection
    # ----------------------------------------------------------------
    def test_deficit_hierarchy_and_bess_protection(self):
        """
        Tests deficit handling:
        1. When BESS has charge (SOC > 20%), discharges to reduce grid import.
        2. When BESS is depleted (SOC <= 20%), BESS stands by to protect battery health
           and grid covers the gap.
        """
        # Case A: Deficit with healthy BESS (SOC 60%)
        # Factory demand: 55 kW (Machine A 25, B 20, Aux 10). Renewable: 15 kW -> Deficit = 40 kW
        dec_healthy = self.engine.evaluate(
            current_timestamp="2026-06-03 10:00:00",
            current_solar_kw=10.0,
            current_wind_kw=5.0,
            battery_soc=60.0
        )
        self.assertEqual(dec_healthy["decision_summary"]["battery_action"], "DISCHARGE")
        self.assertEqual(dec_healthy["decision_summary"]["battery_power_target_kw"], -40.0)
        self.assertEqual(dec_healthy["decision_summary"]["grid_action"], "STANDBY")
        self.assertEqual(dec_healthy["decision_summary"]["grid_power_target_kw"], 0.0)

        # Case B: Deficit with depleted BESS (SOC 19.5% <= 20%)
        dec_depleted = self.engine.evaluate(
            current_timestamp="2026-06-03 10:00:00",
            current_solar_kw=10.0,
            current_wind_kw=5.0,
            battery_soc=19.5
        )
        self.assertEqual(dec_depleted["decision_summary"]["battery_action"], "STANDBY_DEPLETED")
        self.assertEqual(dec_depleted["decision_summary"]["battery_power_target_kw"], 0.0)
        self.assertEqual(dec_depleted["decision_summary"]["grid_action"], "IMPORT")
        self.assertEqual(dec_depleted["decision_summary"]["grid_power_target_kw"], 40.0)

    # ----------------------------------------------------------------
    # TEST 7: Explainability & Structured Contract
    # ----------------------------------------------------------------
    def test_explainability_and_contract_integrity(self):
        """
        Verifies that every evaluation returns the complete, structured Phase 3 contract
        with human-readable, non-empty explainability logs.
        """
        decision = self.engine.evaluate(
            current_timestamp="2026-06-03 12:30:00",
            current_solar_kw=90.0,
            current_wind_kw=10.0,
            battery_soc=75.0
        )

        # Contract keys check
        required_keys = [
            "timestamp", "decision_summary", "machine_decisions",
            "energy_allocation", "schedule_optimization", "renewable_forecast_window",
            "explanations"
        ]
        for k in required_keys:
            self.assertIn(k, decision, f"Missing required contract key: {k}")

        # Explanations check
        explanations = decision["explanations"]
        self.assertIsInstance(explanations, list)
        self.assertGreaterEqual(len(explanations), 3)
        for exp in explanations:
            self.assertIsInstance(exp, str)
            self.assertGreater(len(exp), 10)


if __name__ == "__main__":
    print("=====================================================================")
    print(" APEX-ENERGY: PHASE 3 PRODUCTION-AWARE DECISION ENGINE TEST SUITE")
    print("=====================================================================")
    unittest.main(verbosity=2)
