"""
APEX-Energy: Phase 4 Strict Energy Balance & Verification Test Suite
====================================================================
Comprehensive automated verification of:
1. First Law of Energy Conservation (strict tolerance < 0.001 kW)
2. Imbalance and Energy Drift Detection
3. Physical Non-Negativity Enforcement
4. Battery Operating Limits & Electrochemical Protection
5. Grid Interconnection Physics & Islanding Isolation
6. Industrial Production Load Consistency & Machine Protection
7. Unwarranted Curtailment Detection
8. Seamless Integration with APEX Decision Engine
9. 100% Dataset Compliance Across All 2,016 Timesteps
"""

import sys
import os
import unittest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from verification import EnergyBalanceVerifier, apex_verifier
from decision_engine import apex_decision_engine


class TestApexVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = apex_verifier

    def test_clean_strict_energy_balance(self):
        """
        Tests that perfectly balanced physical energy flows pass with
        zero balance error (< 0.001 kW tolerance).
        Supply: Solar (80) + Wind (10) + Battery Discharge (0) + Grid Import (0) = 90 kW
        Demand: Load (55) + Battery Charge (25) + Grid Export (10) + Curtailment (0) = 90 kW
        """
        alloc = {
            "solar_kw": 80.0,
            "wind_kw": 10.0,
            "battery_discharge_kw": 0.0,
            "grid_import_kw": 0.0,
            "factory_total_load_kw": 55.0,
            "battery_charge_kw": 25.0,
            "grid_export_kw": 10.0,
            "curtailment_kw": 0.0
        }
        res = self.verifier.verify_timestep(alloc, battery_soc=65.0, grid_status=1)
        self.assertTrue(res["valid"])
        self.assertEqual(res["checks"]["energy_balance"], "PASS")
        self.assertAlmostEqual(res["balance_error_kw"], 0.0, delta=0.0001)
        self.assertEqual(len(res["violations"]), 0)

    # ----------------------------------------------------------------
    # TEST 2: Imbalance and Energy Drift Detection
    # ----------------------------------------------------------------
    def test_imbalance_detection(self):
        """
        The verifier must strictly reject any energy balance discrepancy
        and report the exact numerical balance error.
        """
        # Case A: Positive phantom energy (+0.5 kW unaccounted supply)
        alloc_phantom_supply = {
            "solar_kw": 80.5,
            "wind_kw": 10.0,
            "battery_discharge_kw": 0.0,
            "grid_import_kw": 0.0,
            "factory_total_load_kw": 55.0,
            "battery_charge_kw": 25.0,
            "grid_export_kw": 10.0,
            "curtailment_kw": 0.0
        }
        res_a = self.verifier.verify_timestep(alloc_phantom_supply, battery_soc=65.0)
        self.assertFalse(res_a["valid"])
        self.assertEqual(res_a["checks"]["energy_balance"], "FAIL")
        self.assertAlmostEqual(res_a["balance_error_kw"], 0.5, places=3)
        self.assertTrue(any("energy conservation violated" in v for v in res_a["violations"]))

        # Case B: Negative phantom sink (-2.0 kW unaccounted demand)
        alloc_phantom_demand = {
            "solar_kw": 80.0,
            "wind_kw": 10.0,
            "battery_discharge_kw": 0.0,
            "grid_import_kw": 0.0,
            "factory_total_load_kw": 57.0, # 2 kW higher than supply
            "battery_charge_kw": 25.0,
            "grid_export_kw": 10.0,
            "curtailment_kw": 0.0
        }
        res_b = self.verifier.verify_timestep(alloc_phantom_demand, battery_soc=65.0)
        self.assertFalse(res_b["valid"])
        self.assertEqual(res_b["checks"]["energy_balance"], "FAIL")
        self.assertAlmostEqual(res_b["balance_error_kw"], -2.0, places=3)

    # ----------------------------------------------------------------
    # TEST 3: Physical Non-Negativity Enforcement
    # ----------------------------------------------------------------
    def test_non_negative_power_enforcement(self):
        """Verifier must reject negative power flow values."""
        alloc_negative = {
            "solar_kw": 50.0,
            "wind_kw": 10.0,
            "battery_discharge_kw": 0.0,
            "grid_import_kw": 0.0,
            "factory_total_load_kw": 55.0,
            "battery_charge_kw": 10.0,
            "grid_export_kw": 0.0,
            "curtailment_kw": -5.0 # Invalid negative curtailment
        }
        res = self.verifier.verify_timestep(alloc_negative, battery_soc=60.0)
        self.assertFalse(res["valid"])
        self.assertEqual(res["checks"]["non_negative_flows"], "FAIL")
        self.assertTrue(any("Negative power flow" in v for v in res["violations"]))

    # ----------------------------------------------------------------
    # TEST 4: Battery Limits and Electrochemical Protection
    # ----------------------------------------------------------------
    def test_battery_operating_limits(self):
        """
        Verifier must reject:
        1. Simultaneous charge and discharge
        2. Charge exceeding max rating (50 kW)
        3. Discharge exceeding max rating (60 kW)
        4. Overcharge (charge when SOC > 95%)
        5. Deep discharge (discharge when SOC < 20%)
        """
        # 1. Simultaneous charge and discharge
        r1 = self.verifier.verify_battery_physics(battery_soc=50.0, battery_charge_kw=10.0, battery_discharge_kw=10.0)
        self.assertFalse(r1["valid"])
        self.assertTrue(any("Simultaneous" in v for v in r1["violations"]))

        # 2. Charge exceeds 50 kW
        r2 = self.verifier.verify_battery_physics(battery_soc=50.0, battery_charge_kw=55.0, battery_discharge_kw=0.0)
        self.assertFalse(r2["valid"])
        self.assertTrue(any("charge rate" in v.lower() for v in r2["violations"]))

        # 3. Discharge exceeds 60 kW
        r3 = self.verifier.verify_battery_physics(battery_soc=50.0, battery_charge_kw=0.0, battery_discharge_kw=65.0)
        self.assertFalse(r3["valid"])
        self.assertTrue(any("discharge rate" in v.lower() for v in r3["violations"]))

        # 4. Overcharge (SOC 96% charging)
        r4 = self.verifier.verify_battery_physics(battery_soc=96.0, battery_charge_kw=15.0, battery_discharge_kw=0.0)
        self.assertFalse(r4["valid"])
        self.assertTrue(any("maximum limit" in v.lower() for v in r4["violations"]))

        # 5. Deep discharge (SOC 19.0% discharging)
        r5 = self.verifier.verify_battery_physics(battery_soc=19.0, battery_charge_kw=0.0, battery_discharge_kw=15.0)
        self.assertFalse(r5["valid"])
        self.assertTrue(any("minimum threshold" in v.lower() for v in r5["violations"]))

    # ----------------------------------------------------------------
    # TEST 5: Grid Limits and Islanding Isolation
    # ----------------------------------------------------------------
    def test_grid_physics_and_islanding(self):
        """
        Verifier must reject:
        1. Simultaneous import and export
        2. Export exceeding contractual limit
        3. Any grid power during grid outage/islanding (grid_status == 0)
        """
        # 1. Simultaneous import and export
        r1 = self.verifier.verify_grid_physics(grid_status=1, grid_import_kw=20.0, grid_export_kw=15.0)
        self.assertFalse(r1["valid"])
        self.assertTrue(any("Simultaneous" in v for v in r1["violations"]))

        # 2. Export exceeding 50 kW limit
        r2 = self.verifier.verify_grid_physics(grid_status=1, grid_import_kw=0.0, grid_export_kw=60.0, export_limit_kw=50.0)
        self.assertFalse(r2["valid"])
        self.assertTrue(any("exceeds contractual export limit" in v for v in r2["violations"]))

        # 3. Grid outage isolation (grid_status == 0)
        r3 = self.verifier.verify_grid_physics(grid_status=0, grid_import_kw=10.0, grid_export_kw=0.0)
        self.assertFalse(r3["valid"])
        self.assertTrue(any("outage" in v.lower() for v in r3["violations"]))

    # ----------------------------------------------------------------
    # TEST 6: Production Load Integrity & Machine Protection
    # ----------------------------------------------------------------
    def test_production_load_integrity(self):
        """
        Verifier must confirm:
        Total load == Machine A (25) + Machine B (20) + Machine C (35) + Aux (10) = 90 kW
        And flag if Machine A (critical) is interrupted.
        """
        machines_active = {
            "Machine_A": {"power_kw": 25.0},
            "Machine_B": {"power_kw": 20.0},
            "Machine_C": {"power_kw": 35.0}
        }
        # Correct sum: 25 + 20 + 35 + 10 = 90 kW
        r_clean = self.verifier.verify_production_load(factory_total_load_kw=90.0, machine_decisions=machines_active)
        self.assertTrue(r_clean["valid"])

        # Mismatched sum: reported 80 kW instead of 90 kW
        r_mismatch = self.verifier.verify_production_load(factory_total_load_kw=80.0, machine_decisions=machines_active)
        self.assertFalse(r_mismatch["valid"])
        self.assertTrue(any("does not match" in v for v in r_mismatch["violations"]))

        # Machine A critical interruption
        machines_dropped_a = {
            "Machine_A": {"power_kw": 0.0},
            "Machine_B": {"power_kw": 20.0},
            "Machine_C": {"power_kw": 35.0}
        }
        r_dropped_a = self.verifier.verify_production_load(factory_total_load_kw=65.0, machine_decisions=machines_dropped_a, is_weekend=False)
        self.assertFalse(r_dropped_a["valid"])
        self.assertTrue(any("Machine A operating below required" in v for v in r_dropped_a["violations"]))

    # ----------------------------------------------------------------
    # TEST 7: Unwarranted Curtailment Detection
    # ----------------------------------------------------------------
    def test_unwarranted_curtailment(self):
        """
        Curtailment must only occur if BOTH BESS and grid export capacity are saturated.
        If battery is at 50% SOC and grid export is only 10/50 kW, curtailment is unwarranted.
        """
        r_unwarranted = self.verifier.verify_curtailment_validity(
            curtailment_kw=15.0,
            surplus_kw=50.0,
            battery_charge_kw=20.0,
            battery_soc=50.0, # Has headroom up to 95%
            grid_export_kw=15.0, # Has headroom up to 50 kW
            grid_status=1,
            export_limit_kw=50.0
        )
        self.assertFalse(r_unwarranted["valid"])
        self.assertTrue(any("Unwarranted curtailment" in v for v in r_unwarranted["violations"]))

    # ----------------------------------------------------------------
    # TEST 8: Seamless Integration with APEX Decision Engine
    # ----------------------------------------------------------------
    def test_decision_engine_verification_integration(self):
        """
        Verifies that every call to apex_decision_engine.evaluate() produces
        a verified decision with balance_error_kw == 0.0.
        """
        decision = apex_decision_engine.evaluate(
            current_timestamp="2026-06-03 12:00:00",
            current_solar_kw=95.0,
            current_wind_kw=10.0,
            battery_soc=60.0
        )
        self.assertIn("verification", decision)
        verif = decision["verification"]
        self.assertTrue(verif["valid"])
        self.assertAlmostEqual(verif["balance_error_kw"], 0.0, delta=0.0001)
        self.assertEqual(verif["checks"]["energy_balance"], "PASS")
        self.assertEqual(decision["decision_summary"]["is_verified"], True)
        self.assertEqual(decision["decision_summary"]["balance_error_kw"], 0.0)

    # ----------------------------------------------------------------
    # TEST 9: Full 7-Day 2,016-Step Dataset Verification
    # ----------------------------------------------------------------
    def test_full_dataset_verification(self):
        """
        Verifies all 2,016 timesteps of sample_datasets/apex_industrial_dataset.csv.
        Must achieve 100.0% compliance rate with zero violations.
        """
        batch_res = self.verifier.verify_timeseries_dataset(tolerance_kw=0.015)
        self.assertTrue(batch_res["valid"], f"Dataset verification failed: {batch_res.get('sample_violations')}")
        self.assertEqual(batch_res["total_timesteps"], 2016)
        self.assertEqual(batch_res["verified_timesteps"], 2016)
        self.assertEqual(batch_res["failed_timesteps"], 0)
        self.assertEqual(batch_res["compliance_rate_pct"], 100.0)
        self.assertLessEqual(batch_res["max_balance_error_kw"], 0.01)


if __name__ == "__main__":
    print("=====================================================================")
    print(" APEX-ENERGY: PHASE 4 STRICT VERIFICATION TEST SUITE")
    print("=====================================================================")
    unittest.main(verbosity=2)
