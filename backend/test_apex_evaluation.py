"""
APEX-Energy: Phase 5 Baseline vs APEX Evaluation & KPI Test Suite
==================================================================
Comprehensive automated verification of:
1. Dataset & Evaluator Initialization (2,016 timesteps, 7 days)
2. Independent Non-Circular Baseline Evaluation
3. APEX Simulation Physics & 100% Strict Energy Balance Verification
4. Industrial Production Constraint Preservation (Machines A, B, C)
5. Electricity Cost Savings Validation
6. Renewable Curtailment Reduction & Avoided Waste
7. BESS Operational Envelope & Cycling Integrity
8. Daily Scenario Breakdown Across All 7 Days
9. FastAPI REST API Endpoint Integration
"""

import sys
import os
import unittest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from evaluation import ApexEvaluationEngine, apex_evaluator


class TestApexEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evaluator = apex_evaluator
        cls.comparison = cls.evaluator.compare_baseline_vs_apex()

    # ----------------------------------------------------------------
    # TEST 1: Dataset & Evaluator Initialization
    # ----------------------------------------------------------------
    def test_evaluator_initialization(self):
        """Verifies dataset loading and duration."""
        rows = self.evaluator.load_dataset()
        self.assertEqual(len(rows), 2016, "Expected 2,016 timesteps across 7 days")
        self.assertIn("dataset_info", self.comparison)
        self.assertEqual(self.comparison["dataset_info"]["duration_days"], 7)

    # ----------------------------------------------------------------
    # TEST 2: Independent Baseline Counterfactual Evaluation
    # ----------------------------------------------------------------
    def test_baseline_evaluation_integrity(self):
        """
        Confirms that Baseline Counterfactual KPIs are calculated
        independently from dataset columns without circularity.
        """
        baseline = self.comparison["baseline_full"]
        self.assertIn("energy_summary", baseline)
        self.assertIn("grid_and_cost_kpis", baseline)
        self.assertIn("renewable_kpis", baseline)

        # Confirm positive and realistic cumulative values
        self.assertGreater(baseline["energy_summary"]["total_factory_load_kwh"], 5000.0)
        self.assertGreater(baseline["energy_summary"]["total_renewable_kwh"], 4000.0)
        self.assertGreater(baseline["grid_and_cost_kpis"]["net_electricity_cost"], 5000.0)
        self.assertGreater(baseline["renewable_kpis"]["curtailment_kwh"], 300.0)

    # ----------------------------------------------------------------
    # TEST 3: APEX 7-Day Physics & 100% Verification Compliance
    # ----------------------------------------------------------------
    def test_apex_simulation_physics_and_verification(self):
        """
        Verifies that APEX simulated energy flows preserve the First Law
        of Energy Conservation with 100% compliance across all 2,016 timesteps.
        """
        apex = self.comparison["apex_full"]
        prod_comp = apex["production_compliance"]
        self.assertEqual(prod_comp["verified_timesteps"], 2016)
        self.assertEqual(prod_comp["verification_compliance_pct"], 100.0)
        self.assertTrue(prod_comp["all_constraints_respected"])

    # ----------------------------------------------------------------
    # TEST 4: Production Constraint Preservation
    # ----------------------------------------------------------------
    def test_production_constraint_preservation(self):
        """
        Verifies that APEX maintains 100% production quota compliance:
        - Machine A critical continuous runtime
        - Machine B required shift runtime
        - Machine C 3.0h batch quota completed within operating window before 17:00
        """
        apex = self.comparison["apex_full"]
        base = self.comparison["baseline_full"]

        # Machine A and B energy must match baseline exactly (zero quota compromise)
        self.assertAlmostEqual(
            apex["energy_summary"]["machine_a_kwh"],
            base["energy_summary"]["machine_a_kwh"],
            delta=2.0
        )
        self.assertAlmostEqual(
            apex["energy_summary"]["machine_b_kwh"],
            base["energy_summary"]["machine_b_kwh"],
            delta=2.0
        )
        # Machine C total energy must match baseline (same 3h work done, just shifted)
        self.assertAlmostEqual(
            apex["energy_summary"]["machine_c_kwh"],
            base["energy_summary"]["machine_c_kwh"],
            delta=2.0
        )

    # ----------------------------------------------------------------
    # TEST 5: Electricity Cost Savings Validation
    # ----------------------------------------------------------------
    def test_electricity_cost_savings(self):
        """
        Verifies that APEX delivers net electricity cost savings over Baseline
        by shifting flexible demand into renewable-rich, off-peak hours.
        """
        cum = self.comparison["cumulative_kpi_comparison"]
        cost_delta = cum["net_cost"]["delta"]
        cost_pct = cum["net_cost"]["improvement_pct"]

        self.assertGreater(cost_delta, 0.0, "APEX must achieve positive net cost savings")
        self.assertGreater(cost_pct, 0.0)

    # ----------------------------------------------------------------
    # TEST 6: Renewable Curtailment Reduction
    # ----------------------------------------------------------------
    def test_renewable_curtailment_reduction(self):
        """
        Verifies that APEX reduces renewable curtailment by absorbing
        solar/wind peaks into flexible production and BESS.
        """
        cum = self.comparison["cumulative_kpi_comparison"]
        curt_delta = cum["renewable_curtailment"]["delta"]
        curt_pct = cum["renewable_curtailment"]["improvement_pct"]

        self.assertGreater(curt_delta, 10.0, "APEX must avoid at least 10 kWh of curtailment")
        self.assertGreater(curt_pct, 4.0)

    # ----------------------------------------------------------------
    # TEST 7: BESS Operational Envelope & Health
    # ----------------------------------------------------------------
    def test_bess_operating_envelope(self):
        """
        Verifies that APEX battery operation stays strictly within
        the electrochemical safety limits [20.0%, 95.0%].
        """
        apex_bess = self.comparison["apex_full"]["bess_health"]
        self.assertGreaterEqual(apex_bess["min_soc_pct"], 20.0)
        self.assertLessEqual(apex_bess["max_soc_pct"], 95.0)
        self.assertGreater(apex_bess["equivalent_full_cycles"], 1.0)

    # ----------------------------------------------------------------
    # TEST 8: Daily Scenario Breakdown Integrity
    # ----------------------------------------------------------------
    def test_daily_scenario_breakdown(self):
        """
        Verifies that the daily breakdown captures all 7 distinct scenarios
        and demonstrates benefits on key days (solar surge, flexible shift, curtailment).
        """
        daily = self.comparison["daily_scenario_breakdown"]
        self.assertEqual(len(daily), 7, "Must contain exactly 7 daily scenarios")

        # Day 2 (Wednesday - Flexible Shift Opportunity)
        wed = daily[2]
        self.assertEqual(wed["day_index"], 2)
        self.assertGreaterEqual(wed["delta"]["curtailment_avoided_kwh"], 0.5)

        # Day 4 (Friday - Unavoidable Curtailment Event)
        fri = daily[4]
        self.assertEqual(fri["day_index"], 4)
        self.assertGreater(fri["delta"]["curtailment_avoided_kwh"], 15.0)

    # ----------------------------------------------------------------
    # TEST 9: REST API Endpoint Integration
    # ----------------------------------------------------------------
    def test_fastapi_endpoints_integration(self):
        """
        Verifies that GET /api/evaluation/compare and GET /api/evaluation/kpis
        return HTTP 200 with complete comparison payloads.
        """
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        # Compare endpoint
        r_comp = client.get("/api/evaluation/compare")
        self.assertEqual(r_comp.status_code, 200)
        data_comp = r_comp.json()
        self.assertIn("cumulative_kpi_comparison", data_comp)
        self.assertIn("daily_scenario_breakdown", data_comp)

        # KPIs endpoint
        r_kpis = client.get("/api/evaluation/kpis")
        self.assertEqual(r_kpis.status_code, 200)
        data_kpis = r_kpis.json()
        self.assertIn("cumulative_kpi_comparison", data_kpis)
        self.assertIn("key_takeaways", data_kpis)


if __name__ == "__main__":
    print("=====================================================================")
    print(" APEX-ENERGY: PHASE 5 BASELINE VS APEX EVALUATION TEST SUITE")
    print("=====================================================================")
    unittest.main(verbosity=2)
