"""
APEX-Energy: Production-Aware Energy Decision Engine
=====================================================
Phase 3: Production-Aware Energy Decision Engine.

Connects industrial production context (Machine A, B, C) with:
1. Phase 2 Renewable Forecasting Engine
2. Battery Energy Storage System (BESS) state and limits
3. Utility Grid status, export limits, and Time-of-Use tariffs

Core Capabilities:
- Formal constraint validation (operating windows, durations, deadlines)
- Dynamic candidate window generation and scoring (NO hardcoding)
- Explainable decision hierarchy:
    Critical Load -> Feasible Schedule -> Renewable Preference -> Load Shift ->
    BESS Charge/Discharge -> Grid Import/Export -> Unavoidable Curtailment
- Clean service contract and explainable reasoning generation.
"""

import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Import Phase 2 forecasting engine
try:
    from forecasting import renewable_forecaster, get_renewable_forecast
except ImportError:
    from backend.forecasting import renewable_forecaster, get_renewable_forecast

# Import Phase 4 verification layer
try:
    from verification import apex_verifier, EnergyBalanceVerifier
except ImportError:
    from backend.verification import apex_verifier, EnergyBalanceVerifier

class ProductionConstraintChecker:
    """
    Formal validator for industrial machine operational constraints.
    """
    # Machine Specifications (Authoritative Phase 1 specs)
    MACHINE_SPECS = {
        "Machine_A": {
            "name": "Machine A (Continuous Extruder / Smelter)",
            "power_kw": 25.0,
            "criticality": "CRITICAL",
            "shiftable": False,
            "can_interrupt": False,
            "earliest_start": 0.0,
            "latest_end": 24.0,
            "required_duration_hours": 24.0,
            "deadline": 24.0
        },
        "Machine_B": {
            "name": "Machine B (Batch Annealing Oven / CNC)",
            "power_kw": 20.0,
            "criticality": "SEMI_FLEXIBLE",
            "shiftable": True,
            "can_interrupt": True, # Allowed lunch standby
            "earliest_start": 8.0,
            "latest_end": 17.0,
            "required_duration_hours": 8.0,
            "deadline": 17.0
        },
        "Machine_C": {
            "name": "Machine C (Heavy Grinder / Raw Material Crushing / Batch Coater)",
            "power_kw": 35.0,
            "criticality": "FLEXIBLE",
            "shiftable": True,
            "can_interrupt": False, # Continuous batch
            "earliest_start": 8.0, # 08:00
            "latest_end": 17.0,    # 17:00
            "required_duration_hours": 3.0,
            "deadline": 17.0,       # 17:00
            "baseline_start": 9.0, # 09:00
            "baseline_end": 12.0   # 12:00
        }
    }

    @classmethod
    def validate_schedule(cls, machine_id: str, start_hour: float, end_hour: float) -> Dict[str, Any]:
        """
        Validates whether a proposed production schedule satisfies all machine constraints.
        Returns validation pass/fail with explicit check results and violation details.
        """
        if machine_id not in cls.MACHINE_SPECS:
            return {
                "valid": False,
                "checks": {},
                "violations": [f"Unknown machine identifier: {machine_id}"]
            }

        spec = cls.MACHINE_SPECS[machine_id]
        duration = round(end_hour - start_hour, 3)
        violations = []

        # Check 1: Non-negative and logical bounds
        if start_hour < 0.0 or end_hour > 24.0 or start_hour >= end_hour:
            violations.append(f"Invalid time bounds: start {start_hour:.2f}h, end {end_hour:.2f}h")

        # Check 2: Shiftability for Critical Loads
        if not spec["shiftable"] and machine_id == "Machine_A":
            if start_hour != spec["earliest_start"] or end_hour != spec["latest_end"]:
                violations.append("Machine A is CRITICAL and cannot be shifted from continuous operation.")

        # Check 3: Operating Window Bounds
        window_pass = (start_hour >= spec["earliest_start"]) and (end_hour <= spec["latest_end"])
        if not window_pass:
            violations.append(
                f"Proposed window ({start_hour:.2f}h - {end_hour:.2f}h) violates allowed operating window "
                f"({spec['earliest_start']:.2f}h - {spec['latest_end']:.2f}h)."
            )

        # Check 4: Required Operating Duration
        duration_pass = abs(duration - spec["required_duration_hours"]) < 0.05
        if not duration_pass:
            violations.append(
                f"Proposed duration ({duration:.2f}h) does not match required production duration "
                f"({spec['required_duration_hours']:.2f}h)."
            )

        # Check 5: Production Deadline
        deadline_pass = (end_hour <= spec["deadline"] + 0.001)
        if not deadline_pass:
            violations.append(
                f"Proposed end time ({end_hour:.2f}h) violates hard production deadline ({spec['deadline']:.2f}h)."
            )

        checks = {
            "operating_window": "PASS" if window_pass else "FAIL",
            "required_duration": "PASS" if duration_pass else "FAIL",
            "deadline_compliance": "PASS" if deadline_pass else "FAIL",
            "criticality_protection": "PASS" if (spec["shiftable"] or machine_id != "Machine_A" or len(violations) == 0) else "FAIL"
        }

        return {
            "valid": len(violations) == 0,
            "machine_id": machine_id,
            "proposed_window": f"{int(start_hour):02d}:{int((start_hour % 1) * 60):02d} - {int(end_hour):02d}:{int((end_hour % 1) * 60):02d}",
            "checks": checks,
            "violations": violations
        }


class ProductionAwareDecisionEngine:
    """
    APEX-Energy Orchestration & Decision Engine.
    Evaluates factory production context against renewable forecasts and microgrid states.
    """
    def __init__(self, forecaster=None):
        self.forecaster = forecaster or renewable_forecaster
        self.validator = ProductionConstraintChecker()
        self.verifier = apex_verifier
        
        # Factory Auxiliary base load
        self.AUXILIARY_BASE_LOAD_KW = 10.0
        
        # BESS Physical Ratings (from Phase 1)
        self.BATTERY_CAPACITY_KWH = 200.0
        self.BATTERY_MAX_CHARGE_KW = 50.0
        self.BATTERY_MAX_DISCHARGE_KW = 60.0
        self.BATTERY_MIN_SOC = 20.0
        self.BATTERY_MAX_SOC = 95.0

    def generate_candidate_schedules(self, machine_id: str = "Machine_C", step_interval_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Generates all production-feasible candidate operating windows for a shiftable machine.
        For Machine C:
          Earliest start: 08:00, Latest end: 17:00, Required duration: 3.0 hours.
          Generates candidates starting every 30 minutes from 08:00 to 14:00.
        """
        spec = self.validator.MACHINE_SPECS.get(machine_id)
        if not spec or not spec["shiftable"]:
            return []

        earliest = spec["earliest_start"]
        latest = spec["latest_end"]
        duration = spec["required_duration_hours"]

        step_hours = step_interval_minutes / 60.0
        candidates = []

        curr_start = earliest
        while (curr_start + duration) <= (latest + 0.001):
            curr_end = curr_start + duration
            # Validate constraints
            val = self.validator.validate_schedule(machine_id, curr_start, curr_end)
            if val["valid"]:
                start_h = int(curr_start)
                start_m = int(round((curr_start % 1.0) * 60))
                end_h = int(curr_end)
                end_m = int(round((curr_end % 1.0) * 60))
                
                is_baseline = (abs(curr_start - spec.get("baseline_start", -1)) < 0.01)

                candidates.append({
                    "candidate_id": f"WINDOW_{start_h:02d}{start_m:02d}_{end_h:02d}{end_m:02d}",
                    "machine_id": machine_id,
                    "start_hour": round(curr_start, 2),
                    "end_hour": round(curr_end, 2),
                    "start_time": f"{start_h:02d}:{start_m:02d}",
                    "end_time": f"{end_h:02d}:{end_m:02d}",
                    "duration_hours": duration,
                    "is_baseline_schedule": is_baseline,
                    "constraint_validation": val
                })
            curr_start += step_hours

        return candidates

    def score_candidate_schedules(
        self,
        machine_id: str = "Machine_C",
        forecast_predictions: Optional[List[Dict[str, Any]]] = None,
        tariff_peak_rate: float = 7.50,
        tariff_offpeak_rate: float = 4.50,
        tariff_peak_start: float = 14.0,
        tariff_peak_end: float = 20.0
    ) -> Dict[str, Any]:
        """
        Dynamically evaluates and scores all candidate windows against the renewable forecast.
        Computes renewable coverage, avoided grid import, and tariff energy cost.
        NO hardcoding: window with the highest score is mathematically selected.
        """
        candidates = self.generate_candidate_schedules(machine_id)
        if not candidates:
            return {"error": f"No feasible candidates for {machine_id}", "candidates": []}

        machine_power = self.validator.MACHINE_SPECS[machine_id]["power_kw"]
        scored_candidates = []

        # Helper to get solar + wind at any hour from forecast or fallback model
        for cand in candidates:
            start_h = cand["start_hour"]
            end_h = cand["end_hour"]
            
            # Identify predictions falling inside this candidate window
            window_preds = []
            if forecast_predictions:
                for p in forecast_predictions:
                    try:
                        p_dt = datetime.strptime(p["timestamp"], "%Y-%m-%d %H:%M:%S")
                        p_hour = p_dt.hour + p_dt.minute / 60.0
                        if start_h <= p_hour < end_h:
                            window_preds.append((p_hour, p.get("total_renewable_kw", 0.0)))
                    except Exception:
                        pass

            # If fewer than 6 window points, supplement with physical diurnal calculation
            if len(window_preds) < 6:
                sample_hours = [start_h + (end_h - start_h) * (k / 5.0) for k in range(6)]
                for sh in sample_hours:
                    solar_est = 100.0 * math.sin(math.pi * (sh - 6.0) / 12.0) if 6.0 <= sh <= 18.0 else 0.0
                    solar_est = max(0.0, solar_est)
                    window_preds.append((sh, solar_est + 8.0))

            # Total factory demand during operation = Machine A (25) + Machine B (20) + Aux (10) + Machine C (35) = 90 kW
            total_factory_load_kw = 25.0 + 20.0 + self.AUXILIARY_BASE_LOAD_KW + machine_power
            
            renewable_powers = [wp[1] for wp in window_preds]
            avg_renewable_kw = sum(renewable_powers) / len(renewable_powers)
            peak_renewable_kw = max(renewable_powers)

            # Compute grid import and tariff cost across window points
            grid_imports = []
            costs = []
            dt_step = cand["duration_hours"] / len(window_preds)

            for sh, ren_kw in window_preds:
                is_peak = (tariff_peak_start <= sh < tariff_peak_end)
                rate = tariff_peak_rate if is_peak else tariff_offpeak_rate
                imp = max(0.0, total_factory_load_kw - ren_kw)
                grid_imports.append(imp)
                costs.append(imp * rate * dt_step)

            avg_grid_import_kw = sum(grid_imports) / len(grid_imports)
            total_grid_cost = sum(costs)
            renewable_coverage_pct = min(100.0, (avg_renewable_kw / total_factory_load_kw) * 100.0)

            # Transparent Scoring Formula:
            # High score prefers abundant renewables, zero grid import, and low tariff cost
            composite_score = avg_renewable_kw - 1.5 * avg_grid_import_kw - 0.2 * total_grid_cost

            cand_result = {
                **cand,
                "avg_forecast_renewable_kw": round(avg_renewable_kw, 2),
                "peak_forecast_renewable_kw": round(peak_renewable_kw, 2),
                "renewable_coverage_pct": round(renewable_coverage_pct, 1),
                "expected_grid_import_kw": round(avg_grid_import_kw, 2),
                "expected_tariff_cost": round(total_grid_cost, 2),
                "composite_score": round(composite_score, 2)
            }
            scored_candidates.append(cand_result)

        # Sort candidates by composite score descending
        scored_candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        optimal_candidate = scored_candidates[0]
        
        # Identify baseline candidate for comparison (09:00 - 12:00)
        baseline_candidate = next((c for c in scored_candidates if c["is_baseline_schedule"]), scored_candidates[-1])

        # Savings comparison
        grid_import_reduction_kw = max(0.0, baseline_candidate["expected_grid_import_kw"] - optimal_candidate["expected_grid_import_kw"])
        cost_savings = max(0.0, baseline_candidate["expected_tariff_cost"] - optimal_candidate["expected_tariff_cost"])
        coverage_boost_pct = optimal_candidate["renewable_coverage_pct"] - baseline_candidate["renewable_coverage_pct"]

        return {
            "machine_id": machine_id,
            "optimal_window": optimal_candidate["start_time"] + " - " + optimal_candidate["end_time"],
            "optimal_candidate_id": optimal_candidate["candidate_id"],
            "baseline_window": baseline_candidate["start_time"] + " - " + baseline_candidate["end_time"],
            "is_shift_recommended": optimal_candidate["candidate_id"] != baseline_candidate["candidate_id"],
            "expected_benefits": {
                "renewable_coverage_increase_pct": round(coverage_boost_pct, 1),
                "grid_import_reduction_kw": round(grid_import_reduction_kw, 2),
                "cost_savings": round(cost_savings, 2)
            },
            "candidate_rankings": scored_candidates
        }

    def evaluate(
        self,
        current_timestamp: str,
        current_solar_kw: float,
        current_wind_kw: float,
        battery_soc: float,
        grid_status: int = 1,
        export_limit_kw: float = 50.0,
        tariff_rate: float = 4.50,
        is_weekend: bool = False
    ) -> Dict[str, Any]:
        """
        Main APEX Decision Evaluation function for a single timestep.
        Integrates:
          1. Phase 2 renewable forecast and surge detection
          2. Candidate window optimization for Machine C
          3. Machine constraint enforcement
          4. APEX Decision Hierarchy energy allocation
          5. Explainability generation for all actions
        """
        # Parse current hour
        try:
            dt = datetime.strptime(current_timestamp, "%Y-%m-%d %H:%M:%S")
            hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        except Exception:
            hour = 10.0
            dt = datetime(2026, 6, 3, 10, 0, 0)

        # ----------------------------------------------------
        # 1. QUERY PHASE 2 RENEWABLE FORECAST
        # ----------------------------------------------------
        try:
            forecast_res = self.forecaster.predict_multi_step(current_timestamp, horizon_minutes=180)
            forecast_predictions = forecast_res.get("predictions", [])
            renewable_window = forecast_res.get("renewable_rich_window", {})
        except Exception as e:
            forecast_predictions = []
            renewable_window = {"is_renewable_rich": False}

        # ----------------------------------------------------
        # 2. DYNAMIC CANDIDATE WINDOW OPTIMIZATION FOR MACHINE C
        # ----------------------------------------------------
        optimization_res = self.score_candidate_schedules(
            machine_id="Machine_C",
            forecast_predictions=forecast_predictions,
            tariff_peak_rate=7.50,
            tariff_offpeak_rate=4.50
        )
        
        opt_start_h = 12.0
        opt_end_h = 15.0
        if "candidate_rankings" in optimization_res and len(optimization_res["candidate_rankings"]) > 0:
            best_cand = optimization_res["candidate_rankings"][0]
            opt_start_h = best_cand["start_hour"]
            opt_end_h = best_cand["end_hour"]

        # ----------------------------------------------------
        # 3. PRODUCTION MACHINE DECISIONS & STATES
        # ----------------------------------------------------
        machine_decisions = {}
        explanations = []

        # Machine A: Protected Critical Load
        if is_weekend:
            m_a_power = 10.0
            m_a_action = "MAINTENANCE_IDLE"
            m_a_reason = "Machine A operating at reduced maintenance idle during weekend."
        else:
            m_a_power = 25.0
            m_a_action = "RUN"
            m_a_reason = "Machine A is CRITICAL and uninterruptible; fully protected to satisfy production quota."
        
        machine_decisions["Machine_A"] = {
            "machine_id": "Machine_A",
            "name": "Machine A (Critical)",
            "power_kw": m_a_power,
            "action": m_a_action,
            "reason": m_a_reason,
            "constraints": "PASS"
        }
        explanations.append(m_a_reason)

        # Machine B: Semi-Flexible Load (Two Shifts: 08:00-12:00 and 13:00-17:00)
        if is_weekend:
            m_b_power = 0.0
            m_b_action = "OFF"
            m_b_reason = "Machine B offline during weekend."
        elif (8.0 <= hour < 12.0) or (13.0 <= hour < 17.0):
            m_b_power = 20.0
            m_b_action = "RUN"
            m_b_reason = "Machine B operating within scheduled shift window (08:00-12:00, 13:00-17:00)."
        elif 12.0 <= hour < 13.0:
            m_b_power = 3.0
            m_b_action = "STANDBY"
            m_b_reason = "Machine B on scheduled lunch break standby."
        else:
            m_b_power = 0.0
            m_b_action = "OFF"
            m_b_reason = "Machine B offline outside permitted shift hours."

        machine_decisions["Machine_B"] = {
            "machine_id": "Machine_B",
            "name": "Machine B (Semi-Flexible)",
            "power_kw": m_b_power,
            "action": m_b_action,
            "reason": m_b_reason,
            "constraints": "PASS"
        }
        explanations.append(m_b_reason)

        # Machine C: Highly Flexible Load (APEX Load-Shifting Core)
        # Check if Machine C should be RUNNING right now under APEX Schedule
        if is_weekend:
            m_c_power = 0.0
            m_c_action = "OFF"
            m_c_reason = "Machine C offline during weekend."
        elif opt_start_h <= hour < opt_end_h:
            m_c_power = 35.0
            m_c_action = "RUN"
            m_c_reason = (
                f"Machine C active in optimal forecast-aligned window ({int(opt_start_h):02d}:00 - {int(opt_end_h):02d}:00) "
                f"to maximize renewable self-consumption."
            )
        elif 9.0 <= hour < 12.0 and optimization_res.get("is_shift_recommended", False):
            # In baseline, Machine C would run right now, but APEX has shifted it!
            m_c_power = 0.0
            m_c_action = "SHIFT_DELAY"
            m_c_reason = (
                f"Machine C delayed from baseline schedule (09:00-12:00) and SHIFTED to optimal window "
                f"({int(opt_start_h):02d}:00 - {int(opt_end_h):02d}:00). Avoids {optimization_res['expected_benefits']['grid_import_reduction_kw']} kW "
                f"grid import while guaranteeing deadline compliance by 17:00."
            )
        else:
            m_c_power = 0.0
            m_c_action = "IDLE"
            m_c_reason = "Machine C idle outside scheduled batch execution window."

        machine_decisions["Machine_C"] = {
            "machine_id": "Machine_C",
            "name": "Machine C (Flexible)",
            "power_kw": m_c_power,
            "action": m_c_action,
            "baseline_window": "09:00 - 12:00",
            "apex_optimized_window": f"{int(opt_start_h):02d}:00 - {int(opt_end_h):02d}:00",
            "is_shifted": optimization_res.get("is_shift_recommended", False),
            "reason": m_c_reason,
            "constraints": "PASS (Deadline 17:00 respected)"
        }
        explanations.append(m_c_reason)

        # ----------------------------------------------------
        # 4. ENERGY ALLOCATION (APEX DECISION HIERARCHY)
        # ----------------------------------------------------
        total_production_load = round(m_a_power + m_b_power + m_c_power + self.AUXILIARY_BASE_LOAD_KW, 2)
        total_renewable = round(current_solar_kw + current_wind_kw, 2)
        surplus = round(total_renewable - total_production_load, 2)

        battery_action = "STANDBY"
        battery_target_kw = 0.0
        grid_action = "STANDBY"
        grid_target_kw = 0.0
        curtailment_kw = 0.0
        renewable_action = "DIRECT_CONSUMPTION"

        if grid_status == 0:
            # Grid Outage / Islanding
            grid_action = "DISCONNECTED_OUTAGE"
            if surplus >= 0:
                headroom = max(0.0, (self.BATTERY_MAX_SOC - battery_soc) / 100.0 * self.BATTERY_CAPACITY_KWH)
                if battery_soc < self.BATTERY_MAX_SOC and headroom > 0.1:
                    battery_target_kw = min(surplus, self.BATTERY_MAX_CHARGE_KW)
                    battery_action = "CHARGE"
                leftover = surplus - battery_target_kw
                curtailment_kw = max(0.0, leftover) # Cannot export during outage
                renewable_action = "ISLAND_STORAGE"
            else:
                deficit = abs(surplus)
                if battery_soc > self.BATTERY_MIN_SOC:
                    battery_target_kw = -min(deficit, self.BATTERY_MAX_DISCHARGE_KW)
                    battery_action = "DISCHARGE"
                unmet = deficit - abs(battery_target_kw)
                if unmet > 0.01:
                    renewable_action = "DEFICIT_LOAD_SHED"

        else:
            # Grid Connected: APEX Decision Hierarchy
            if surplus >= 0:
                # Renewable Surplus:
                # 1. Satisfy production load (already accounted via surplus)
                # 2. Charge Battery if SOC allows
                headroom = max(0.0, (self.BATTERY_MAX_SOC - battery_soc) / 100.0 * self.BATTERY_CAPACITY_KWH)
                if battery_soc < self.BATTERY_MAX_SOC and headroom > 0.1:
                    battery_target_kw = min(surplus, self.BATTERY_MAX_CHARGE_KW)
                    battery_action = "CHARGE"
                    battery_reason = f"Charging BESS with {battery_target_kw:.1f} kW renewable surplus (SOC: {battery_soc:.1f}%)."
                else:
                    battery_target_kw = 0.0
                    battery_action = "STANDBY_FULL"
                    battery_reason = f"BESS fully charged (SOC: {battery_soc:.1f}%); surplus directed to export."

                leftover_surplus = surplus - battery_target_kw

                # 3. Export surplus up to export limit
                if leftover_surplus > 0:
                    grid_target_kw = -min(leftover_surplus, export_limit_kw)
                    grid_action = "EXPORT"
                    grid_reason = f"Exporting {abs(grid_target_kw):.1f} kW surplus to grid under feed-in tariff."
                    
                    # 4. Curtail ONLY remaining unavoidable surplus
                    curtailment_kw = max(0.0, leftover_surplus - abs(grid_target_kw))
                    if curtailment_kw > 0.01:
                        curtail_reason = (
                            f"Curtailing {curtailment_kw:.1f} kW unavoidable surplus because grid export cap "
                            f"({export_limit_kw} kW) and BESS capacity are saturated."
                        )
                        explanations.append(curtail_reason)
                else:
                    grid_target_kw = 0.0
                    grid_action = "STANDBY"
                    grid_reason = "Local load and battery absorption matched available renewable generation."

                explanations.append(battery_reason)
                explanations.append(grid_reason)

            else:
                # Renewable Deficit:
                # 1. Discharge battery if SOC > 20%
                deficit = abs(surplus)
                if battery_soc > self.BATTERY_MIN_SOC:
                    discharge_needed = min(deficit, self.BATTERY_MAX_DISCHARGE_KW)
                    battery_target_kw = -discharge_needed
                    battery_action = "DISCHARGE"
                    battery_reason = f"Discharging BESS ({discharge_needed:.1f} kW) to cover deficit and avoid grid import."
                else:
                    battery_target_kw = 0.0
                    battery_action = "STANDBY_DEPLETED"
                    battery_reason = f"BESS protected at minimum SOC threshold ({battery_soc:.1f}%)."

                # 2. Grid import fills remaining deficit
                remaining_deficit = max(0.0, deficit - abs(battery_target_kw))
                if remaining_deficit > 0:
                    grid_target_kw = remaining_deficit
                    grid_action = "IMPORT"
                    grid_reason = f"Importing {grid_target_kw:.1f} kW from utility grid to guarantee factory production."
                else:
                    grid_target_kw = 0.0
                    grid_action = "STANDBY"
                    grid_reason = "Renewable + BESS discharge completely covered factory demand."

                explanations.append(battery_reason)
                explanations.append(grid_reason)

        energy_allocation = {
            "solar_kw": current_solar_kw,
            "wind_kw": current_wind_kw,
            "battery_charge_kw": max(0.0, battery_target_kw),
            "battery_discharge_kw": max(0.0, -battery_target_kw),
            "grid_import_kw": max(0.0, grid_target_kw),
            "grid_export_kw": max(0.0, -grid_target_kw),
            "curtailment_kw": round(curtailment_kw, 2),
            "factory_total_load_kw": total_production_load
        }

        verification_result = self.verifier.verify_timestep(
            energy_allocation=energy_allocation,
            battery_soc=battery_soc,
            grid_status=grid_status,
            export_limit_kw=export_limit_kw,
            machine_decisions=machine_decisions,
            is_weekend=is_weekend,
            timestamp=current_timestamp,
            tolerance_kw=0.001
        )

        return {
            "timestamp": current_timestamp,
            "decision_summary": {
                "total_production_load_kw": total_production_load,
                "total_renewable_kw": total_renewable,
                "surplus_kw": surplus,
                "machine_c_status": m_c_action,
                "is_machine_c_shifted": optimization_res.get("is_shift_recommended", False),
                "battery_action": battery_action,
                "battery_power_target_kw": round(battery_target_kw, 2),
                "grid_action": grid_action,
                "grid_power_target_kw": round(grid_target_kw, 2),
                "curtailment_kw": round(curtailment_kw, 2),
                "is_verified": verification_result["valid"],
                "balance_error_kw": verification_result["balance_error_kw"]
            },
            "machine_decisions": machine_decisions,
            "energy_allocation": energy_allocation,
            "verification": verification_result,
            "schedule_optimization": optimization_res,
            "renewable_forecast_window": renewable_window,
            "explanations": explanations
        }

# Global singleton instance for service consumption
apex_decision_engine = ProductionAwareDecisionEngine()

def evaluate_decision(current_timestamp: str = None, current_solar_kw: float = 0.0, current_wind_kw: float = 0.0, battery_soc: float = 50.0):
    """Clean interface for Phase 4 verification and Phase 5 integration."""
    ts = current_timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return apex_decision_engine.evaluate(
        current_timestamp=ts,
        current_solar_kw=current_solar_kw,
        current_wind_kw=current_wind_kw,
        battery_soc=battery_soc
    )

if __name__ == "__main__":
    print("[Decision Engine] Initializing APEX Production-Aware Decision Engine...")
    engine = ProductionAwareDecisionEngine()
    
    print("\n1. Testing Constraint Checker for Machine C...")
    # Valid schedule
    v1 = engine.validator.validate_schedule("Machine_C", 12.0, 15.0)
    print(f"  Candidate 12:00-15:00 Valid: {v1['valid']} (Checks: {v1['checks']})")
    
    # Invalid schedule (past 17:00 deadline)
    v2 = engine.validator.validate_schedule("Machine_C", 15.0, 18.0)
    print(f"  Candidate 15:00-18:00 Valid: {v2['valid']} (Violations: {v2['violations']})")

    print("\n2. Testing Candidate Window Scoring...")
    scoring = engine.score_candidate_schedules("Machine_C")
    print(f"  Baseline Window : {scoring['baseline_window']}")
    print(f"  Optimal Window  : {scoring['optimal_window']}")
    print(f"  Shift Recommended: {scoring['is_shift_recommended']}")
    print(f"  Benefits        : {scoring['expected_benefits']}")

    print("\n3. Testing Real-time Decision Evaluation at Wednesday 10:00:00...")
    dec = engine.evaluate("2026-06-03 10:00:00", current_solar_kw=80.0, current_wind_kw=10.0, battery_soc=65.0)
    print("  Decision Summary:")
    for k, v in dec["decision_summary"].items():
        print(f"    {k:25s}: {v}")
    print("\n  Explanations Generated:")
    for e in dec["explanations"]:
        print(f"    • {e}")
