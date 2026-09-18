"""
APEX-Energy: Dataset Verification & Quality Assurance Suite
============================================================
Automated tests verifying the synthetic industrial energy dataset:
1. Schema & Data Integrity
2. Renewable Generation Physical Realism
3. Industrial Machine Profile & Constraint Verification
4. Energy Balance Law Preservation (Gen + Disch + Imp == Load + Chg + Exp + Curt)
5. Hackathon Demo Scenario Coverage
"""

import os
import csv
import unittest

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_datasets", "apex_industrial_dataset.csv")
MACHINES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_datasets", "apex_machines_dataset.csv")

class TestApexDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrue(cls, os.path.exists(DATASET_PATH), f"Primary dataset not found at {DATASET_PATH}")
        cls.assertTrue(cls, os.path.exists(MACHINES_PATH), f"Machines dataset not found at {MACHINES_PATH}")
        
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cls.rows = list(reader)

        with open(MACHINES_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cls.machine_rows = list(reader)

    def test_record_count(self):
        """Verify 7 days at 5-minute resolution = 2,016 timesteps."""
        expected_steps = 7 * 24 * (60 // 5)
        self.assertEqual(len(self.rows), expected_steps, f"Expected {expected_steps} rows, found {len(self.rows)}")
        self.assertEqual(len(self.machine_rows), expected_steps)

    def test_schema_columns(self):
        """Verify presence of all required APEX industrial schema fields."""
        required_fields = [
            "timestamp", "epoch_timestamp", "hour", "day_of_week", "is_weekend", "scenario_tag",
            "ambient_temperature_c", "solar_irradiance_w_m2", "cloud_cover", "wind_speed_m_s",
            "solar_generation_kw", "wind_generation_kw", "total_renewable_kw",
            "machine_a_power_kw", "machine_a_status",
            "machine_b_power_kw", "machine_b_status",
            "machine_c_baseline_power_kw", "machine_c_baseline_status",
            "base_facility_load_kw", "baseline_total_load_kw",
            "critical_load_kw", "flexible_load_kw",
            "machine_c_flex_potential_kw", "machine_c_earliest_start", "machine_c_latest_end",
            "machine_c_required_duration_hours", "machine_c_deadline",
            "grid_status", "tariff_rate", "is_peak_tariff", "grid_export_limit_kw",
            "baseline_battery_power_kw", "baseline_battery_charge_kw", "baseline_battery_discharge_kw",
            "baseline_battery_soc", "baseline_grid_import_kw", "baseline_grid_export_kw",
            "baseline_curtailment_kw", "baseline_step_cost", "baseline_cumulative_cost",
            "energy_balance_verified"
        ]
        headers = self.rows[0].keys()
        for field in required_fields:
            self.assertIn(field, headers, f"Missing required schema field: {field}")

    def test_no_null_or_nan(self):
        """Verify no empty string or NaN values exist in any row."""
        for idx, row in enumerate(self.rows):
            for key, val in row.items():
                self.assertIsNotNone(val, f"Null found at row {idx}, key {key}")
                self.assertNotEqual(val, "", f"Empty string found at row {idx}, key {key}")
                self.assertNotEqual(val.lower(), "nan", f"NaN found at row {idx}, key {key}")

    def test_solar_physics(self):
        """Verify solar PV is 0 at night and within physical limits during the day."""
        for row in self.rows:
            hour = float(row["hour"])
            solar = float(row["solar_generation_kw"])
            self.assertGreaterEqual(solar, 0.0)
            self.assertLessEqual(solar, 105.0) # Within 100 kW rating (+ small noise)
            if hour < 5.8 or hour > 18.2:
                self.assertEqual(solar, 0.0, f"Solar power {solar} observed at night hour {hour}")

    def test_wind_physics(self):
        """Verify wind power stays within [0, 52] kW."""
        for row in self.rows:
            wind = float(row["wind_generation_kw"])
            self.assertGreaterEqual(wind, 0.0)
            self.assertLessEqual(wind, 52.0)

    def test_battery_soc_limits(self):
        """Verify battery SOC stays strictly within safe operational limits [0, 100] %."""
        for row in self.rows:
            soc = float(row["baseline_battery_soc"])
            self.assertGreaterEqual(soc, 15.0, f"SOC dropped below safety limit: {soc}%")
            self.assertLessEqual(soc, 100.0, f"SOC exceeded 100%: {soc}%")

    def test_machine_production_profiles(self):
        """Verify industrial machine profiles and load aggregation."""
        for row in self.rows:
            is_weekend = int(row["is_weekend"])
            m_a = float(row["machine_a_power_kw"])
            m_b = float(row["machine_b_power_kw"])
            m_c = float(row["machine_c_baseline_power_kw"])
            base = float(row["base_facility_load_kw"])
            total = float(row["baseline_total_load_kw"])
            hour = float(row["hour"])

            # Machine A: Critical (25 kW on weekdays, ~10 kW on weekends)
            if is_weekend:
                self.assertAlmostEqual(m_a, 10.0, delta=2.0)
                self.assertEqual(row["machine_a_status"], "IDLE")
            else:
                self.assertAlmostEqual(m_a, 25.0, delta=2.5)
                self.assertEqual(row["machine_a_status"], "RUNNING")

            # Machine C: Baseline scheduled 09:00 to 12:00 weekdays
            if not is_weekend and (9.0 <= hour < 12.0):
                self.assertAlmostEqual(m_c, 35.0, delta=2.5)
                self.assertEqual(row["machine_c_baseline_status"], "RUNNING")
            else:
                self.assertEqual(m_c, 0.0)
                self.assertEqual(row["machine_c_baseline_status"], "OFF")

            # Sum aggregation
            expected_total = round(m_a + m_b + m_c + base, 2)
            self.assertAlmostEqual(total, expected_total, delta=0.05)

    def test_strict_energy_balance(self):
        """
        Verify the First Law of Energy Conservation on EVERY SINGLE TIMESTEP:
        Generation + Battery_Discharge + Grid_Import == Total_Load + Battery_Charge + Grid_Export + Curtailment
        """
        violations = 0
        for idx, row in enumerate(self.rows):
            gen = float(row["total_renewable_kw"])
            disch = float(row["baseline_battery_discharge_kw"])
            imp = float(row["baseline_grid_import_kw"])
            load = float(row["baseline_total_load_kw"])
            chg = float(row["baseline_battery_charge_kw"])
            exp = float(row["baseline_grid_export_kw"])
            curt = float(row["baseline_curtailment_kw"])

            supply = gen + disch + imp
            demand = load + chg + exp + curt
            diff = abs(supply - demand)

            if diff > 0.01:
                violations += 1
                print(f"Row {idx} Balance Violation: Supply {supply:.3f} != Demand {demand:.3f} (Diff: {diff:.4f})")

        self.assertEqual(violations, 0, f"Encountered {violations} energy balance violations!")

    def test_scenario_diversity(self):
        """Verify that all required hackathon demo scenarios are captured in the dataset."""
        tags = set(row["scenario_tag"] for row in self.rows)
        print(f"\n[Validation] Detected Scenario Tags in Dataset ({len(tags)}):")
        for t in sorted(tags):
            print(f"  - {t}")

        # Core scenarios that must exist
        self.assertTrue(any("NORMAL" in t for t in tags), "Missing NORMAL operation scenario")
        self.assertTrue(any("SOLAR" in t or "SURPLUS" in t for t in tags), "Missing SOLAR/SURPLUS scenario")
        self.assertTrue(any("FLEXIBLE" in t for t in tags), "Missing FLEXIBLE shift opportunity scenario")
        self.assertTrue(any("CURTAILMENT" in t for t in tags), "Missing CURTAILMENT scenario")
        self.assertTrue(any("GRID_EXPORT" in t for t in tags), "Missing GRID_EXPORT scenario")
        self.assertTrue(any("GRID_FALLBACK" in t for t in tags), "Missing GRID_FALLBACK scenario")
        self.assertTrue(any("ISLANDING" in t or "OUTAGE" in t for t in tags), "Missing GRID_OUTAGE/ISLANDING scenario")

if __name__ == "__main__":
    unittest.main()
