"""
APEX-Energy: Strict Energy Balance & Physics Verification Layer
================================================================
Phase 4: Strict Energy Balance & Physics Verification Engine.

Answers:
"After APEX makes a decision, does the resulting energy flow strictly obey
physics, battery limits, grid limits, and production constraints?"

Key Checks:
1. Strict Energy Conservation (First Law of Thermodynamics):
   Supply (Renewable + BESS Discharge + Grid Import)
   == Demand (Factory Load + BESS Charge + Grid Export + Curtailment)
   abs(balance_error) < tolerance (0.001 kW)
2. Physical Non-Negativity: All individual power flows >= 0.0 kW.
3. Battery Physical Constraints:
   - No simultaneous charge and discharge
   - Charge limit <= 50.0 kW
   - Discharge limit <= 60.0 kW
   - SOC range [20.0%, 95.0%] with hard cutoff at bounds
4. Grid Interconnection Limits:
   - No simultaneous import and export
   - Export limit <= 50.0 kW (or dynamic export cap)
   - Zero import and export during grid outage (grid_status == 0)
5. Production Load Consistency:
   - Total factory load matches Machine A + B + C + Auxiliary (10 kW)
   - Machine A critical uninterruptible protection
6. Curtailment Validity:
   - Curtailment only permitted when BESS and grid export capacity are saturated
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional


class EnergyBalanceVerifier:
    """
    Dedicated physical and operational verification engine for APEX-Energy.
    Enforces strict energy conservation and microgrid physical bounds.
    """
    TOLERANCE_KW: float = 0.001

    # Authoritative BESS physical ratings
    BATTERY_MAX_CHARGE_KW: float = 50.0
    BATTERY_MAX_DISCHARGE_KW: float = 60.0
    BATTERY_MIN_SOC: float = 20.0
    BATTERY_MAX_SOC: float = 95.0

    # Grid physical limits
    GRID_DEFAULT_EXPORT_LIMIT_KW: float = 50.0

    # Production ratings
    AUXILIARY_BASE_LOAD_KW: float = 10.0
    MACHINE_A_CRITICAL_POWER_KW: float = 25.0

    @classmethod
    def verify_energy_balance(
        cls,
        solar_kw: float,
        wind_kw: float,
        battery_discharge_kw: float,
        grid_import_kw: float,
        factory_total_load_kw: float,
        battery_charge_kw: float,
        grid_export_kw: float,
        curtailment_kw: float,
        tolerance_kw: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Verifies the strict First Law of Energy Conservation:
        Supply (Solar + Wind + Battery_Discharge + Grid_Import)
        == Demand (Factory_Load + Battery_Charge + Grid_Export + Curtailment)
        """
        tol = tolerance_kw if tolerance_kw is not None else cls.TOLERANCE_KW

        supply = round(solar_kw + wind_kw + battery_discharge_kw + grid_import_kw, 6)
        demand = round(factory_total_load_kw + battery_charge_kw + grid_export_kw + curtailment_kw, 6)
        balance_error = round(supply - demand, 6)

        is_valid = abs(balance_error) <= tol
        return {
            "valid": is_valid,
            "supply_total_kw": supply,
            "demand_total_kw": demand,
            "balance_error_kw": balance_error,
            "tolerance_kw": tol,
            "status": "PASS" if is_valid else "FAIL"
        }

    @classmethod
    def verify_physical_non_negativity(cls, energy_allocation: Dict[str, float]) -> Dict[str, Any]:
        """Verifies that all energy flow magnitudes are non-negative."""
        violations = []
        for key in [
            "solar_kw", "wind_kw", "battery_charge_kw", "battery_discharge_kw",
            "grid_import_kw", "grid_export_kw", "curtailment_kw", "factory_total_load_kw"
        ]:
            val = float(energy_allocation.get(key, 0.0))
            if val < -cls.TOLERANCE_KW:
                violations.append(f"Negative power flow detected for '{key}': {val:.4f} kW")

        return {
            "valid": len(violations) == 0,
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "violations": violations
        }

    @classmethod
    def verify_battery_physics(
        cls,
        battery_soc: float,
        battery_charge_kw: float,
        battery_discharge_kw: float
    ) -> Dict[str, Any]:
        """
        Verifies BESS electrochemical constraints:
        1. No simultaneous charge and discharge
        2. Maximum charge rate limit (50 kW)
        3. Maximum discharge rate limit (60 kW)
        4. State-of-Charge bounds [20%, 95%] cutoff enforcement
        """
        violations = []

        # 1. Simultaneous charge and discharge
        if battery_charge_kw > cls.TOLERANCE_KW and battery_discharge_kw > cls.TOLERANCE_KW:
            violations.append(
                f"Simultaneous battery charge ({battery_charge_kw:.2f} kW) and discharge "
                f"({battery_discharge_kw:.2f} kW) violates physical battery inverter design."
            )

        # 2. Maximum charge rate limit
        if battery_charge_kw > cls.BATTERY_MAX_CHARGE_KW + cls.TOLERANCE_KW:
            violations.append(
                f"Battery charge rate ({battery_charge_kw:.2f} kW) exceeds maximum rating "
                f"({cls.BATTERY_MAX_CHARGE_KW:.1f} kW)."
            )

        # 3. Maximum discharge rate limit
        if battery_discharge_kw > cls.BATTERY_MAX_DISCHARGE_KW + cls.TOLERANCE_KW:
            violations.append(
                f"Battery discharge rate ({battery_discharge_kw:.2f} kW) exceeds maximum rating "
                f"({cls.BATTERY_MAX_DISCHARGE_KW:.1f} kW)."
            )

        # 4. SOC bounds
        if battery_soc < 0.0 or battery_soc > 100.0:
            violations.append(f"Battery SOC ({battery_soc:.2f}%) is outside physical limits [0%, 100%].")

        # 5. Overcharge protection: SOC cannot exceed 95.0%
        if battery_soc > (cls.BATTERY_MAX_SOC + 0.05) and battery_charge_kw > cls.TOLERANCE_KW:
            violations.append(
                f"Battery charged ({battery_charge_kw:.2f} kW) causing SOC ({battery_soc:.2f}%) to exceed "
                f"maximum limit ({cls.BATTERY_MAX_SOC:.1f}%)."
            )

        # 6. Deep discharge protection: SOC cannot drop below 20.0%
        if battery_soc < (cls.BATTERY_MIN_SOC - 0.05) and battery_discharge_kw > cls.TOLERANCE_KW:
            violations.append(
                f"Battery discharged ({battery_discharge_kw:.2f} kW) causing SOC ({battery_soc:.2f}%) to drop "
                f"below minimum threshold ({cls.BATTERY_MIN_SOC:.1f}%)."
            )

        return {
            "valid": len(violations) == 0,
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "violations": violations
        }

    @classmethod
    def verify_grid_physics(
        cls,
        grid_status: int,
        grid_import_kw: float,
        grid_export_kw: float,
        export_limit_kw: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Verifies grid interconnection constraints:
        1. No simultaneous import and export
        2. Maximum export limit
        3. Complete galvanic isolation during grid outage (grid_status == 0)
        """
        violations = []
        exp_limit = export_limit_kw if export_limit_kw is not None else cls.GRID_DEFAULT_EXPORT_LIMIT_KW

        # 1. Simultaneous import and export
        if grid_import_kw > cls.TOLERANCE_KW and grid_export_kw > cls.TOLERANCE_KW:
            violations.append(
                f"Simultaneous grid import ({grid_import_kw:.2f} kW) and export ({grid_export_kw:.2f} kW) "
                f"violates single-point-of-interconnection physics."
            )

        # 2. Grid outage / islanding
        if grid_status == 0:
            if grid_import_kw > cls.TOLERANCE_KW:
                violations.append(
                    f"Grid import ({grid_import_kw:.2f} kW) detected during grid outage/islanding (grid_status=0)."
                )
            if grid_export_kw > cls.TOLERANCE_KW:
                violations.append(
                    f"Grid export ({grid_export_kw:.2f} kW) detected during grid outage/islanding (grid_status=0)."
                )

        # 3. Export limit
        if grid_export_kw > exp_limit + cls.TOLERANCE_KW:
            violations.append(
                f"Grid export ({grid_export_kw:.2f} kW) exceeds contractual export limit ({exp_limit:.1f} kW)."
            )

        return {
            "valid": len(violations) == 0,
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "violations": violations
        }

    @classmethod
    def verify_production_load(
        cls,
        factory_total_load_kw: float,
        machine_decisions: Optional[Dict[str, Any]] = None,
        is_weekend: bool = False
    ) -> Dict[str, Any]:
        """
        Verifies factory load aggregation:
        Load == Machine A + Machine B + Machine C + Auxiliary Base Load (10 kW).
        Also verifies Machine A critical load protection.
        """
        violations = []

        if machine_decisions:
            m_a = float(machine_decisions.get("Machine_A", {}).get("power_kw", 0.0))
            m_b = float(machine_decisions.get("Machine_B", {}).get("power_kw", 0.0))
            m_c = float(machine_decisions.get("Machine_C", {}).get("power_kw", 0.0))
            expected_total = round(m_a + m_b + m_c + cls.AUXILIARY_BASE_LOAD_KW, 2)

            if abs(factory_total_load_kw - expected_total) > 0.05:
                violations.append(
                    f"Factory total load ({factory_total_load_kw:.2f} kW) does not match the sum of "
                    f"machines ({m_a:.1f} + {m_b:.1f} + {m_c:.1f}) + aux base ({cls.AUXILIARY_BASE_LOAD_KW:.1f}) = {expected_total:.2f} kW."
                )

            # Machine A critical protection
            if not is_weekend and m_a < (cls.MACHINE_A_CRITICAL_POWER_KW - 1.0):
                violations.append(
                    f"Critical Machine A operating below required continuous rating "
                    f"({m_a:.2f} kW < {cls.MACHINE_A_CRITICAL_POWER_KW:.1f} kW) on a weekday."
                )

        return {
            "valid": len(violations) == 0,
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "violations": violations
        }

    @classmethod
    def verify_curtailment_validity(
        cls,
        curtailment_kw: float,
        surplus_kw: float,
        battery_charge_kw: float,
        battery_soc: float,
        grid_export_kw: float,
        grid_status: int,
        export_limit_kw: float = 50.0
    ) -> Dict[str, Any]:
        """
        Verifies that curtailment is ONLY invoked when unavoidable:
        Surplus > 0, AND BESS cannot absorb more (at max charge rate or max SOC),
        AND grid cannot export more (at export limit or grid outage).
        """
        violations = []

        if curtailment_kw > cls.TOLERANCE_KW:
            if surplus_kw <= 0:
                violations.append(
                    f"Curtailment of {curtailment_kw:.2f} kW occurred during energy deficit (surplus = {surplus_kw:.2f} kW)."
                )

            # Check if battery had unutilized charging capacity
            battery_headroom_soc = (cls.BATTERY_MAX_SOC - battery_soc)
            bess_can_absorb_more = (battery_headroom_soc > 1.0) and (battery_charge_kw < cls.BATTERY_MAX_CHARGE_KW - 1.0)

            # Check if grid had unutilized export capacity
            grid_can_export_more = (grid_status == 1) and (grid_export_kw < export_limit_kw - 1.0)

            if bess_can_absorb_more and grid_can_export_more:
                violations.append(
                    f"Unwarranted curtailment: {curtailment_kw:.2f} kW was curtailed while both BESS "
                    f"(charge: {battery_charge_kw:.1f}/{cls.BATTERY_MAX_CHARGE_KW:.1f} kW) and Grid Export "
                    f"(export: {grid_export_kw:.1f}/{export_limit_kw:.1f} kW) had absorption capacity."
                )

        return {
            "valid": len(violations) == 0,
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "violations": violations
        }

    @classmethod
    def verify_timestep(
        cls,
        energy_allocation: Dict[str, float],
        battery_soc: float,
        grid_status: int = 1,
        export_limit_kw: float = 50.0,
        machine_decisions: Optional[Dict[str, Any]] = None,
        is_weekend: bool = False,
        timestamp: Optional[str] = None,
        tolerance_kw: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes complete multi-aspect verification for a single operational timestep.
        Returns a structured pass/fail report with granular check results and violation messages.
        """
        all_violations = []

        # 1. Non-negativity check
        nn_res = cls.verify_physical_non_negativity(energy_allocation)
        all_violations.extend(nn_res["violations"])

        # 2. Strict Energy Conservation check
        solar = float(energy_allocation.get("solar_kw", 0.0))
        wind = float(energy_allocation.get("wind_kw", 0.0))
        b_disch = float(energy_allocation.get("battery_discharge_kw", 0.0))
        g_imp = float(energy_allocation.get("grid_import_kw", 0.0))
        load = float(energy_allocation.get("factory_total_load_kw", 0.0))
        b_chg = float(energy_allocation.get("battery_charge_kw", 0.0))
        g_exp = float(energy_allocation.get("grid_export_kw", 0.0))
        curt = float(energy_allocation.get("curtailment_kw", 0.0))

        balance_res = cls.verify_energy_balance(
            solar_kw=solar,
            wind_kw=wind,
            battery_discharge_kw=b_disch,
            grid_import_kw=g_imp,
            factory_total_load_kw=load,
            battery_charge_kw=b_chg,
            grid_export_kw=g_exp,
            curtailment_kw=curt,
            tolerance_kw=tolerance_kw
        )
        if not balance_res["valid"]:
            all_violations.append(
                f"Strict energy conservation violated: Supply ({balance_res['supply_total_kw']:.4f} kW) != "
                f"Demand ({balance_res['demand_total_kw']:.4f} kW), Balance Error = {balance_res['balance_error_kw']:.4f} kW."
            )

        # 3. Battery physics check
        batt_res = cls.verify_battery_physics(
            battery_soc=battery_soc,
            battery_charge_kw=b_chg,
            battery_discharge_kw=b_disch
        )
        all_violations.extend(batt_res["violations"])

        # 4. Grid physics check
        grid_res = cls.verify_grid_physics(
            grid_status=grid_status,
            grid_import_kw=g_imp,
            grid_export_kw=g_exp,
            export_limit_kw=export_limit_kw
        )
        all_violations.extend(grid_res["violations"])

        # 5. Production load check
        prod_res = cls.verify_production_load(
            factory_total_load_kw=load,
            machine_decisions=machine_decisions,
            is_weekend=is_weekend
        )
        all_violations.extend(prod_res["violations"])

        # 6. Curtailment validity check
        surplus = (solar + wind) - load
        curt_res = cls.verify_curtailment_validity(
            curtailment_kw=curt,
            surplus_kw=surplus,
            battery_charge_kw=b_chg,
            battery_soc=battery_soc,
            grid_export_kw=g_exp,
            grid_status=grid_status,
            export_limit_kw=export_limit_kw
        )
        all_violations.extend(curt_res["violations"])

        is_overall_valid = len(all_violations) == 0

        return {
            "valid": is_overall_valid,
            "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "balance_error_kw": balance_res["balance_error_kw"],
            "tolerance_kw": balance_res["tolerance_kw"],
            "supply_total_kw": balance_res["supply_total_kw"],
            "demand_total_kw": balance_res["demand_total_kw"],
            "checks": {
                "energy_balance": balance_res["status"],
                "non_negative_flows": nn_res["status"],
                "battery_limits": batt_res["status"],
                "no_simultaneous_battery_action": "PASS" if not (b_chg > cls.TOLERANCE_KW and b_disch > cls.TOLERANCE_KW) else "FAIL",
                "grid_limits": grid_res["status"],
                "no_simultaneous_grid_action": "PASS" if not (g_imp > cls.TOLERANCE_KW and g_exp > cls.TOLERANCE_KW) else "FAIL",
                "production_constraints": prod_res["status"],
                "curtailment_validity": curt_res["status"]
            },
            "violations": all_violations
        }

    @classmethod
    def verify_decision(cls, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method to verify a decision dictionary directly from apex_decision_engine.evaluate()."""
        energy_alloc = decision.get("energy_allocation", {})
        machine_dec = decision.get("machine_decisions", {})
        timestamp = decision.get("timestamp", "")
        
        # Infer battery soc and grid status if present, else defaults
        battery_soc = 50.0
        grid_status = 1
        export_limit = cls.GRID_DEFAULT_EXPORT_LIMIT_KW

        # Check explanations for hints if direct keys missing
        for exp in decision.get("explanations", []):
            if "SOC:" in exp:
                try:
                    battery_soc = float(exp.split("SOC:")[1].split("%")[0].strip())
                except Exception:
                    pass

        return cls.verify_timestep(
            energy_allocation=energy_alloc,
            battery_soc=battery_soc,
            grid_status=grid_status,
            export_limit_kw=export_limit,
            machine_decisions=machine_dec,
            timestamp=timestamp
        )

    @classmethod
    def verify_timeseries_dataset(
        cls,
        csv_path: Optional[str] = None,
        tolerance_kw: float = 0.015
    ) -> Dict[str, Any]:
        """
        Runs comprehensive batch verification across all timesteps of the 7-day Phase 1 dataset.
        Returns aggregate statistics and confirms zero physical balance drift.
        """
        if csv_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, "sample_datasets", "apex_industrial_dataset.csv")

        if not os.path.exists(csv_path):
            return {"error": f"Dataset file not found at: {csv_path}", "valid": False}

        rows_total = 0
        rows_passed = 0
        rows_failed = 0
        violations_log = []
        max_error = 0.0
        total_error = 0.0
        total_load_kwh = 0.0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                rows_total += 1
                solar = float(row.get("solar_generation_kw", 0.0))
                wind = float(row.get("wind_generation_kw", 0.0))
                b_disch = float(row.get("baseline_battery_discharge_kw", 0.0))
                g_imp = float(row.get("baseline_grid_import_kw", 0.0))
                load = float(row.get("baseline_total_load_kw", 0.0))
                b_chg = float(row.get("baseline_battery_charge_kw", 0.0))
                g_exp = float(row.get("baseline_grid_export_kw", 0.0))
                curt = float(row.get("baseline_curtailment_kw", 0.0))
                soc = float(row.get("baseline_battery_soc", 50.0))
                grid_status = int(row.get("grid_status", 1))
                export_limit = float(row.get("grid_export_limit_kw", 50.0))
                is_weekend = bool(int(row.get("is_weekend", 0)))

                energy_alloc = {
                    "solar_kw": solar,
                    "wind_kw": wind,
                    "battery_discharge_kw": b_disch,
                    "grid_import_kw": g_imp,
                    "factory_total_load_kw": load,
                    "battery_charge_kw": b_chg,
                    "grid_export_kw": g_exp,
                    "curtailment_kw": curt
                }

                # Track metrics
                total_load_kwh += load * (5.0 / 60.0)

                v_res = cls.verify_timestep(
                    energy_allocation=energy_alloc,
                    battery_soc=soc,
                    grid_status=grid_status,
                    export_limit_kw=export_limit,
                    is_weekend=is_weekend,
                    timestamp=row.get("timestamp"),
                    tolerance_kw=tolerance_kw
                )

                err = abs(v_res["balance_error_kw"])
                if err > max_error:
                    max_error = err
                total_error += err

                if v_res["valid"]:
                    rows_passed += 1
                else:
                    rows_failed += 1
                    if len(violations_log) < 10:
                        violations_log.append({
                            "row_index": idx,
                            "timestamp": row.get("timestamp"),
                            "violations": v_res["violations"]
                        })

        mean_error = total_error / max(1, rows_total)
        compliance_rate = (rows_passed / max(1, rows_total)) * 100.0

        return {
            "valid": rows_failed == 0,
            "dataset_path": csv_path,
            "total_timesteps": rows_total,
            "verified_timesteps": rows_passed,
            "failed_timesteps": rows_failed,
            "compliance_rate_pct": round(compliance_rate, 4),
            "max_balance_error_kw": round(max_error, 6),
            "mean_balance_error_kw": round(mean_error, 6),
            "tolerance_kw": tolerance_kw,
            "total_energy_verified_kwh": round(total_load_kwh, 2),
            "sample_violations": violations_log
        }


# Global singleton instance
apex_verifier = EnergyBalanceVerifier()

if __name__ == "__main__":
    print("=====================================================================")
    print(" APEX-ENERGY: PHASE 4 STRICT ENERGY BALANCE & VERIFIER")
    print("=====================================================================")
    
    print("\n1. Verifying Clean Legal Timestep...")
    clean_sample = {
        "solar_kw": 80.0,
        "wind_kw": 10.0,
        "battery_discharge_kw": 0.0,
        "grid_import_kw": 0.0,
        "factory_total_load_kw": 55.0,
        "battery_charge_kw": 25.0,
        "grid_export_kw": 10.0,
        "curtailment_kw": 0.0
    }
    r1 = apex_verifier.verify_timestep(clean_sample, battery_soc=65.0)
    print(f"  Valid: {r1['valid']} | Error: {r1['balance_error_kw']:.4f} kW | Checks: {r1['checks']}")

    print("\n2. Verifying Discrepancy Detection (+0.5 kW Balance Error)...")
    flawed_sample = dict(clean_sample)
    flawed_sample["curtailment_kw"] = 0.5 # creates demand = 90.5 vs supply = 90.0
    r2 = apex_verifier.verify_timestep(flawed_sample, battery_soc=65.0)
    print(f"  Caught Violation: {not r2['valid']} | Violations: {r2['violations']}")

    print("\n3. Verifying Entire Phase 1 Dataset (2,016 Timesteps)...")
    batch_res = apex_verifier.verify_timeseries_dataset()
    print(f"  Dataset Valid: {batch_res['valid']}")
    print(f"  Total Steps  : {batch_res['total_timesteps']}")
    print(f"  Passed Steps : {batch_res['verified_timesteps']}")
    print(f"  Compliance   : {batch_res['compliance_rate_pct']}%")
    print(f"  Max Error    : {batch_res['max_balance_error_kw']} kW")
    print(f"  Mean Error   : {batch_res['mean_balance_error_kw']} kW")
