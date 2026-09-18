"""
APEX-Energy: Production-Aware Industrial Microgrid Dataset Generator
=====================================================================
Phase 1: Deterministic, realistic, and reproducible synthetic industrial dataset.

Models an industrial facility integrating:
- Solar PV generation (100 kW max, irradiance & cloud physics, ambient derating)
- Wind turbine generation (50 kW max, cubic power curve, cut-in/cut-out)
- Industrial Machine Loads:
    * Machine A: Critical Load (25 kW continuous, uninterruptible)
    * Machine B: Semi-Flexible Load (20 kW, batch processing with window constraints)
    * Machine C: Highly Flexible Load (35 kW, discretionary/deferrable with deadline)
    * Auxiliary Base Load: 10 kW (continuous facility lighting, HVAC, servers)
- Battery Energy Storage System (200 kWh, 50 kW charge / 60 kW discharge, 20%-95% SOC limits)
- Utility Grid interface with Time-of-Use (ToU) tariffs and export limits
- Baseline Uncoordinated Counterfactual Dispatch (ground truth to prove APEX optimization against)
- Strict Mathematical Energy Balance Assertion on EVERY timestep:
    Gen + Battery_Discharge + Grid_Import == Load + Battery_Charge + Grid_Export + Curtailment
"""

import os
import csv
import math
import random
from datetime import datetime, timedelta

def generate_apex_dataset(days=7, interval_minutes=5, seed=42, output_dir=None):
    """
    Generates the APEX-Energy 7-day 5-minute resolution synthetic dataset.
    
    Total steps for 7 days at 5-minute resolution = 7 * 24 * 12 = 2,016 rows.
    """
    random.seed(seed)
    
    if output_dir is None:
        # Default to sample_datasets directory in workspace
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_datasets")
    os.makedirs(output_dir, exist_ok=True)

    start_time = datetime(2026, 6, 1, 0, 0, 0) # Monday 00:00:00
    total_steps = int((days * 24 * 60) / interval_minutes)
    dt_hours = interval_minutes / 60.0 # 5/60 = 0.08333 hr

    # Physical Constants (matching existing MicrogridSimulator)
    SOLAR_MAX_CAPACITY = 100.0   # kW
    WIND_MAX_CAPACITY = 50.0     # kW
    BATTERY_CAPACITY_KWH = 200.0 # kWh
    BATTERY_MAX_CHARGE_KW = 50.0 # Max charge rate
    BATTERY_MAX_DISCHARGE_KW = 60.0 # Max discharge rate
    BATTERY_MIN_SOC = 20.0       # Minimum SOC limit (%)
    BATTERY_MAX_SOC = 95.0       # Maximum SOC limit (%)
    BATTERY_CHG_EFF = 0.95       # Charging efficiency
    BATTERY_DIS_EFF = 0.95       # Discharging efficiency

    # Tariff Structure (matching ems_settings)
    TARIFF_PEAK_RATE = 7.50      # ₹ or $ per kWh
    TARIFF_OFFPEAK_RATE = 4.50   # ₹ or $ per kWh
    TARIFF_PEAK_START = 14.0     # 14:00 (2 PM)
    TARIFF_PEAK_END = 20.0       # 20:00 (8 PM)

    # Initial States
    battery_soc = 50.0 # Starting SOC at 50%
    cumulative_cost = 0.0

    rows = []
    machine_rows = []

    for step in range(total_steps):
        current_time = start_time + timedelta(minutes=step * interval_minutes)
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        epoch_timestamp = current_time.timestamp()
        hour = current_time.hour + current_time.minute / 60.0 + current_time.second / 3600.0
        day_index = step // (24 * 60 // interval_minutes) # 0 to 6
        day_of_week = current_time.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = 1 if day_of_week >= 5 else 0

        # ----------------------------------------------------
        # 1. SCENARIO CONFIGURATION ACROSS 7 DAYS
        # ----------------------------------------------------
        # Day 0: Normal mixed operations
        # Day 1: Solar Surge Day (clear sky, high irradiance)
        # Day 2: Flexible Shift Opportunity Day (strong noon solar peak, uncoordinated morning baseline)
        # Day 3: Cloudy / Low Renewable Day (heavy cloud cover, low wind)
        # Day 4: Grid Export Cap & Curtailment Day (full battery + high solar + export limit capped at 20 kW)
        # Day 5: Weekend Light Production (Machine B & C idle/maintenance, excess solar export)
        # Day 6: Grid Outage Stress-Test (Utility grid islanded 14:00-16:00, BESS & PV support)
        
        if day_index == 0:
            day_scenario_base = "NORMAL_OPERATION"
            cloud_base = 0.15
            wind_base_speed = 7.5
            export_limit = 50.0
            grid_outage = False
        elif day_index == 1:
            day_scenario_base = "SOLAR_SURGE"
            cloud_base = 0.05 # Crystal clear
            wind_base_speed = 6.0
            export_limit = 50.0
            grid_outage = False
        elif day_index == 2:
            day_scenario_base = "FLEXIBLE_SHIFT_OPPORTUNITY"
            cloud_base = 0.10
            wind_base_speed = 8.0
            export_limit = 50.0
            grid_outage = False
        elif day_index == 3:
            day_scenario_base = "LOW_RENEWABLE_DAY"
            cloud_base = 0.75 # Heavy overcast
            wind_base_speed = 3.5 # Low wind
            export_limit = 50.0
            grid_outage = False
        elif day_index == 4:
            day_scenario_base = "CURTAILMENT_SURPLUS"
            cloud_base = 0.05
            wind_base_speed = 10.0 # High wind + solar
            export_limit = 20.0 # Strict export cap by utility, forcing curtailment!
            grid_outage = False
        elif day_index == 5:
            day_scenario_base = "WEEKEND_LIGHT_LOAD"
            cloud_base = 0.20
            wind_base_speed = 7.0
            export_limit = 50.0
            grid_outage = False
        else:
            day_scenario_base = "GRID_OUTAGE_ISLANDING"
            cloud_base = 0.25
            wind_base_speed = 6.5
            export_limit = 50.0
            grid_outage = (14.0 <= hour <= 16.0) # 2-hour outage

        # ----------------------------------------------------
        # 2. WEATHER & AMBIENT ENVIRONMENT
        # ----------------------------------------------------
        # Temperature diurnal cycle peaking around 15:00
        ambient_temp = 24.0 + 8.0 * math.sin(2 * math.pi * (hour - 9.0) / 24.0) + random.uniform(-0.4, 0.4)
        cloud_cover = max(0.0, min(1.0, cloud_base + random.uniform(-0.05, 0.05)))
        
        # Wind speed diurnal pattern with turbulence
        wind_diurnal = wind_base_speed + 2.5 * math.sin(2 * math.pi * (hour - 4.0) / 24.0)
        wind_speed = max(0.0, min(28.0, wind_diurnal + random.uniform(-0.8, 0.8)))

        # ----------------------------------------------------
        # 3. RENEWABLE GENERATION PHYSICS
        # ----------------------------------------------------
        # Solar PV Model
        solar_generation = 0.0
        irradiance_w_m2 = 0.0
        if 6.0 <= hour <= 18.0:
            sin_irrad = math.sin(math.pi * (hour - 6.0) / 12.0)
            irradiance_w_m2 = round(1000.0 * sin_irrad * (1.0 - cloud_cover), 1)
            # Temperature derating: -0.4% efficiency per degree above 25°C
            temp_derating = 1.0 - 0.004 * (ambient_temp - 25.0)
            solar_generation = SOLAR_MAX_CAPACITY * sin_irrad * (1.0 - cloud_cover) * temp_derating
            solar_generation = max(0.0, solar_generation + random.uniform(-0.5, 0.5))
        
        # Wind Turbine Model (Cubic Power Curve)
        wind_generation = 0.0
        cut_in = 3.0
        rated_speed = 12.0
        cut_out = 25.0
        if cut_in <= wind_speed < rated_speed:
            wind_generation = WIND_MAX_CAPACITY * ((wind_speed - cut_in) / (rated_speed - cut_in)) ** 3
        elif rated_speed <= wind_speed <= cut_out:
            wind_generation = WIND_MAX_CAPACITY + random.uniform(-0.4, 0.4)
        else:
            wind_generation = 0.0 # Below cut-in or cut-out shutdown

        total_renewable = round(solar_generation + wind_generation, 2)

        # ----------------------------------------------------
        # 4. INDUSTRIAL PRODUCTION CONTEXT & MACHINES
        # ----------------------------------------------------
        # Machine A: Critical Continuous Load (e.g., Extruder / Smelter / Cleanroom HVAC)
        # Power rating: 25 kW. Cannot be shifted or interrupted during factory shifts.
        if is_weekend:
            # Weekend idle/reduced baseline maintenance
            machine_a_power = 10.0 + random.uniform(-0.5, 0.5)
            machine_a_status = "IDLE"
        else:
            machine_a_power = 25.0 + random.uniform(-0.8, 0.8)
            machine_a_status = "RUNNING"

        # Machine B: Semi-Flexible Load (e.g., CNC Machining / Annealing Oven)
        # Power rating: 20 kW. Operates two shifts on weekdays (08:00 - 12:00 and 13:00 - 17:00).
        if is_weekend:
            machine_b_power = 0.0
            machine_b_status = "OFF"
        else:
            if (8.0 <= hour < 12.0) or (13.0 <= hour < 17.0):
                machine_b_power = 20.0 + random.uniform(-0.7, 0.7)
                machine_b_status = "RUNNING"
            elif 12.0 <= hour < 13.0:
                machine_b_power = 3.0 # Lunch break standby power
                machine_b_status = "STANDBY"
            else:
                machine_b_power = 0.0
                machine_b_status = "OFF"

        # Machine C: Highly Flexible / Discretionary Load (e.g., Heavy Grinding / Wastewater / Batch Process)
        # Power rating: 35 kW. Requires 3 hours to complete its daily production quota.
        # Operating window: 08:00 to 17:00. Deadline: 17:00.
        # In the UNCOORDINATED BASELINE schedule, it starts blindly at 09:00 (09:00 - 12:00) during low solar!
        # In APEX-Energy, this 35 kW is identified as flexible and candidate for shifting to 12:00 - 15:00.
        machine_c_flex_potential = 35.0
        machine_c_earliest_start = "08:00"
        machine_c_latest_end = "17:00"
        machine_c_duration_hours = 3.0
        machine_c_deadline = "17:00"

        if is_weekend:
            machine_c_baseline_power = 0.0
            machine_c_baseline_status = "OFF"
            machine_c_flex_potential = 0.0
        else:
            # Baseline runs Machine C from 09:00 to 12:00
            if 9.0 <= hour < 12.0:
                machine_c_baseline_power = 35.0 + random.uniform(-1.0, 1.0)
                machine_c_baseline_status = "RUNNING"
            else:
                machine_c_baseline_power = 0.0
                machine_c_baseline_status = "OFF"

        # Continuous Auxiliary Facility Load (Lighting, IT servers, safety ventilation)
        base_facility_load = 10.0 + random.uniform(-0.3, 0.3)

        # Baseline Total Load Demand
        baseline_total_load = round(
            machine_a_power + machine_b_power + machine_c_baseline_power + base_facility_load, 2
        )
        critical_load = round(machine_a_power + base_facility_load, 2)
        flexible_load = round(machine_c_baseline_power, 2)

        # ----------------------------------------------------
        # 5. GRID TARIFF & STATUS
        # ----------------------------------------------------
        is_peak_tariff = 1 if (TARIFF_PEAK_START <= hour < TARIFF_PEAK_END and not is_weekend) else 0
        current_tariff = TARIFF_PEAK_RATE if is_peak_tariff else TARIFF_OFFPEAK_RATE
        grid_status = 0 if grid_outage else 1

        # ----------------------------------------------------
        # 6. BASELINE COUNTERFACTUAL ENERGY BALANCE
        # ----------------------------------------------------
        surplus = total_renewable - baseline_total_load

        battery_charge = 0.0
        battery_discharge = 0.0
        grid_import = 0.0
        grid_export = 0.0
        curtailment = 0.0
        
        # Determine specific timestep scenario tag
        if grid_status == 0:
            scenario_tag = "GRID_OUTAGE_ISLANDING"
            if surplus >= 0:
                headroom_kwh = max(0.0, (BATTERY_MAX_SOC - battery_soc) / 100.0 * BATTERY_CAPACITY_KWH)
                max_chg_power = min(surplus, BATTERY_MAX_CHARGE_KW, headroom_kwh / (BATTERY_CHG_EFF * dt_hours))
                battery_charge = max(0.0, max_chg_power)
                curtailment = surplus - battery_charge # cannot export during outage!
                battery_soc += (battery_charge * BATTERY_CHG_EFF * dt_hours) / BATTERY_CAPACITY_KWH * 100.0
            else:
                deficit = abs(surplus)
                available_disch_kwh = max(0.0, (battery_soc - BATTERY_MIN_SOC) / 100.0 * BATTERY_CAPACITY_KWH)
                max_dis_power = min(deficit, BATTERY_MAX_DISCHARGE_KW, (available_disch_kwh * BATTERY_DIS_EFF) / dt_hours)
                battery_discharge = max(0.0, max_dis_power)
                battery_soc -= (battery_discharge / BATTERY_DIS_EFF * dt_hours) / BATTERY_CAPACITY_KWH * 100.0
                unmet_load = deficit - battery_discharge
                if unmet_load > 0:
                    scenario_tag = "ISLAND_LOAD_SHED"

        else:
            # Grid Connected Mode
            if surplus >= 0:
                # Renewable Surplus
                headroom_kwh = max(0.0, (BATTERY_MAX_SOC - battery_soc) / 100.0 * BATTERY_CAPACITY_KWH)
                if battery_soc < BATTERY_MAX_SOC and headroom_kwh > 0.01:
                    max_chg_power = min(surplus, BATTERY_MAX_CHARGE_KW, headroom_kwh / (BATTERY_CHG_EFF * dt_hours))
                    battery_charge = max(0.0, max_chg_power)
                    battery_soc += (battery_charge * BATTERY_CHG_EFF * dt_hours) / BATTERY_CAPACITY_KWH * 100.0
                    scenario_tag = "BATTERY_CHARGING"
                
                leftover_after_battery = surplus - battery_charge
                
                if leftover_after_battery > 0:
                    if battery_soc >= (BATTERY_MAX_SOC - 0.5):
                        scenario_tag = "BATTERY_FULL_SURPLUS"
                    
                    grid_export = min(leftover_after_battery, export_limit)
                    curtailment = leftover_after_battery - grid_export
                    
                    if curtailment > 0.01:
                        scenario_tag = "UNAVOIDABLE_CURTAILMENT"
                    elif grid_export > 0.01:
                        scenario_tag = "GRID_EXPORT"
                elif battery_charge > 0:
                    scenario_tag = "BATTERY_CHARGING"
                else:
                    scenario_tag = "NORMAL_OPERATION"

            else:
                # Renewable Deficit
                deficit = abs(surplus)
                available_disch_kwh = max(0.0, (battery_soc - BATTERY_MIN_SOC) / 100.0 * BATTERY_CAPACITY_KWH)
                
                if battery_soc > BATTERY_MIN_SOC and available_disch_kwh > 0.01:
                    max_dis_power = min(deficit, BATTERY_MAX_DISCHARGE_KW, (available_disch_kwh * BATTERY_DIS_EFF) / dt_hours)
                    battery_discharge = max(0.0, max_dis_power)
                    battery_soc -= (battery_discharge / BATTERY_DIS_EFF * dt_hours) / BATTERY_CAPACITY_KWH * 100.0
                    scenario_tag = "BATTERY_DISCHARGING"
                
                grid_import = deficit - battery_discharge
                if battery_soc <= BATTERY_MIN_SOC + 0.1 and grid_import > 0:
                    scenario_tag = "GRID_FALLBACK"
                elif grid_import > 0 and battery_discharge > 0:
                    scenario_tag = "NORMAL_OPERATION"

        # Contextual Scenario Highlights for Hackathon Demonstration:
        # 1. Flexible Shift Opportunity: Weekdays 09:00 - 12:00 when Machine C is running on grid power
        if not is_weekend and (9.0 <= hour < 12.0) and grid_import > 15.0:
            scenario_tag = "FLEXIBLE_SHIFT_OPPORTUNITY"
        # 2. Solar Surge: Day 1 midday when solar generation ramps to extreme peak (>75 kW)
        elif day_index == 1 and (11.0 <= hour < 14.0) and solar_generation > 70.0:
            scenario_tag = "SOLAR_SURGE"
        # 3. Grid Export: Clear surplus export to grid without curtailment
        elif grid_export > 5.0 and curtailment <= 0.01:
            scenario_tag = "GRID_EXPORT"
        # 4. Battery Charging: Morning solar surplus directed into BESS
        elif battery_charge > 10.0 and scenario_tag == "BATTERY_CHARGING":
            scenario_tag = "BATTERY_CHARGING"
        # 5. Normal Operation: Balanced mixed power flows
        elif scenario_tag not in ["UNAVOIDABLE_CURTAILMENT", "GRID_OUTAGE_ISLANDING", "GRID_FALLBACK", "FLEXIBLE_SHIFT_OPPORTUNITY", "SOLAR_SURGE", "GRID_EXPORT", "BATTERY_CHARGING"] and (solar_generation > 0 or wind_generation > 0) and grid_import < 20.0:
            scenario_tag = "NORMAL_OPERATION"

        battery_soc = max(0.0, min(100.0, battery_soc))
        battery_net_power = round(battery_charge - battery_discharge, 2) # positive = charge, negative = discharge

        # Step electricity cost
        step_cost = (grid_import * current_tariff - grid_export * (current_tariff * 0.5)) * dt_hours
        cumulative_cost += step_cost

        # ----------------------------------------------------
        # 7. STRICT ENERGY BALANCE ASSERTION
        # ----------------------------------------------------
        # Generation + Storage Discharge + Grid Import == Load + Storage Charge + Grid Export + Curtailment
        left_side = total_renewable + battery_discharge + grid_import
        right_side = baseline_total_load + battery_charge + grid_export + curtailment
        energy_balance_error = abs(left_side - right_side)
        
        assert energy_balance_error < 0.01, (
            f"Energy balance violation at {timestamp_str}! "
            f"Gen({total_renewable}) + Disch({battery_discharge}) + Imp({grid_import}) = {left_side:.3f} != "
            f"Load({baseline_total_load}) + Chg({battery_charge}) + Exp({grid_export}) + Curt({curtailment}) = {right_side:.3f} "
            f"(Error: {energy_balance_error:.4f})"
        )

        # ----------------------------------------------------
        # 8. ROW RECORD PACKING
        # ----------------------------------------------------
        row = {
            "timestamp": timestamp_str,
            "epoch_timestamp": int(epoch_timestamp),
            "hour": round(hour, 3),
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "scenario_tag": scenario_tag,
            
            # Weather & Environment
            "ambient_temperature_c": round(ambient_temp, 2),
            "solar_irradiance_w_m2": round(irradiance_w_m2, 1),
            "cloud_cover": round(cloud_cover, 2),
            "wind_speed_m_s": round(wind_speed, 2),
            
            # Generation
            "solar_generation_kw": round(solar_generation, 2),
            "wind_generation_kw": round(wind_generation, 2),
            "total_renewable_kw": total_renewable,
            
            # Production Machine Telemetry
            "machine_a_power_kw": round(machine_a_power, 2),
            "machine_a_status": machine_a_status,
            "machine_b_power_kw": round(machine_b_power, 2),
            "machine_b_status": machine_b_status,
            "machine_c_baseline_power_kw": round(machine_c_baseline_power, 2),
            "machine_c_baseline_status": machine_c_baseline_status,
            "base_facility_load_kw": round(base_facility_load, 2),
            "baseline_total_load_kw": baseline_total_load,
            "critical_load_kw": critical_load,
            "flexible_load_kw": flexible_load,
            
            # Machine C Constraints (for APEX optimization engine)
            "machine_c_flex_potential_kw": machine_c_flex_potential,
            "machine_c_earliest_start": machine_c_earliest_start,
            "machine_c_latest_end": machine_c_latest_end,
            "machine_c_required_duration_hours": machine_c_duration_hours,
            "machine_c_deadline": machine_c_deadline,
            
            # Grid & Tariffs
            "grid_status": grid_status,
            "tariff_rate": current_tariff,
            "is_peak_tariff": is_peak_tariff,
            "grid_export_limit_kw": export_limit,
            
            # Baseline Dispatch & Energy Balance
            "baseline_battery_power_kw": battery_net_power,
            "baseline_battery_charge_kw": round(battery_charge, 2),
            "baseline_battery_discharge_kw": round(battery_discharge, 2),
            "baseline_battery_soc": round(battery_soc, 2),
            "baseline_grid_import_kw": round(grid_import, 2),
            "baseline_grid_export_kw": round(grid_export, 2),
            "baseline_curtailment_kw": round(curtailment, 2),
            "baseline_step_cost": round(step_cost, 4),
            "baseline_cumulative_cost": round(cumulative_cost, 2),
            "energy_balance_verified": 1
        }
        rows.append(row)

        # Machine-specific replay row
        machine_row = {
            "timestamp": timestamp_str,
            "Machine_A_Power": round(machine_a_power, 2),
            "Machine_A_Status": machine_a_status,
            "Machine_B_Power": round(machine_b_power, 2),
            "Machine_B_Status": machine_b_status,
            "Machine_C_Power": round(machine_c_baseline_power, 2),
            "Machine_C_Status": machine_c_baseline_status,
            "Auxiliary_Load": round(base_facility_load, 2),
            "Total_Production_Load": baseline_total_load
        }
        machine_rows.append(machine_row)

    # ----------------------------------------------------
    # 9. EXPORT CSV DATASETS
    # ----------------------------------------------------
    main_csv_path = os.path.join(output_dir, "apex_industrial_dataset.csv")
    with open(main_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[APEX Generator] Successfully generated primary dataset: {main_csv_path} ({len(rows)} records)")

    machines_csv_path = os.path.join(output_dir, "apex_machines_dataset.csv")
    with open(machines_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(machine_rows[0].keys()))
        writer.writeheader()
        writer.writerows(machine_rows)
    print(f"[APEX Generator] Successfully generated machines dataset: {machines_csv_path} ({len(machine_rows)} records)")

    # Also update backend/dataset.csv for backward compatibility with existing tests
    backend_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset.csv")
    legacy_rows = []
    for r in rows:
        legacy_rows.append({
            "timestamp": r["timestamp"],
            "solar_power": r["solar_generation_kw"],
            "wind_power": r["wind_generation_kw"],
            "battery_soc": r["baseline_battery_soc"],
            "load_demand": r["baseline_total_load_kw"],
            "grid_power": round(r["baseline_grid_import_kw"] - r["baseline_grid_export_kw"], 2),
            "temperature": r["ambient_temperature_c"],
            "ems_action": r["scenario_tag"]
        })
    with open(backend_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(legacy_rows[0].keys()))
        writer.writeheader()
        writer.writerows(legacy_rows)
    print(f"[APEX Generator] Updated backend legacy replay dataset: {backend_csv_path}")

    return main_csv_path, machines_csv_path

if __name__ == "__main__":
    generate_apex_dataset()
