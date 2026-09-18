import csv
import math
import random
from datetime import datetime, timedelta

def generate_microgrid_dataset(days=7, interval_minutes=5):
    """
    Generates a realistic historical dataset for a microgrid system.
    Saves to dataset.csv in the requested format:
    timestamp,solar_power,wind_power,battery_soc,load_demand,grid_power,temperature,ems_action
    """
    start_time = datetime(2026, 5, 1, 0, 0, 0)
    total_steps = int((days * 24 * 60) / interval_minutes)
    
    battery_soc = 50.0  # Starting SOC
    battery_capacity_kwh = 200.0
    max_charge_kw = 50.0
    max_discharge_kw = 60.0
    min_soc = 20.0
    max_soc = 100.0
    dt_hours = interval_minutes / 60.0
    
    rows = []
    
    for step in range(total_steps):
        current_time = start_time + timedelta(minutes=step * interval_minutes)
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        hour = current_time.hour + current_time.minute / 60.0
        day_of_week = current_time.weekday() # 0-6 (5,6 are weekend)
        
        # 1. Temperature Simulation
        # Daily cycle peaking at 3 PM, cooler at night
        base_temp = 22.0 + 8.0 * math.sin(2 * math.pi * (hour - 9) / 24)
        temperature = base_temp + random.uniform(-1.0, 1.0)
        
        # 2. Solar Generation Simulation
        solar_power = 0.0
        if 6.0 <= hour <= 18.0:
            irradiance_factor = math.sin(math.pi * (hour - 6.0) / 12.0)
            # Cloud cover scenario: some days are cloudier
            day_index = step // (24 * 60 // interval_minutes)
            cloud_factor = 0.1 if day_index % 3 == 0 else (0.6 if day_index % 3 == 1 else 0.2)
            solar_power = 100.0 * irradiance_factor * (1.0 - cloud_factor)
            solar_power = max(0.0, solar_power + random.uniform(-2.0, 2.0))
            
        # 3. Wind Generation Simulation
        # Wind speed has dynamic cycles
        wind_cycle = 8.0 + 4.0 * math.sin(2 * math.pi * (hour - 2) / 24)
        wind_speed = max(0.0, wind_cycle + random.uniform(-2.0, 2.0))
        
        wind_power = 0.0
        if 3.0 <= wind_speed < 12.0:
            wind_power = 50.0 * ((wind_speed - 3.0) / 9.0) ** 3
        elif 12.0 <= wind_speed <= 25.0:
            wind_power = 50.0 + random.uniform(-0.5, 0.5)
            
        p_renewable = solar_power + wind_power
        
        # 4. Load Demand Simulation
        # Double peak (8 AM, 7 PM)
        t1 = math.exp(-((hour - 8.0) / 2.0) ** 2)
        t2 = math.exp(-((hour - 19.0) / 3.0) ** 2)
        # Weekends have slightly lower base load
        weekend_mult = 0.8 if day_of_week >= 5 else 1.0
        base_load = (25.0 + 20.0 * t1 + 35.0 * t2) * weekend_mult
        load_demand = max(5.0, base_load + random.uniform(-3.0, 3.0))
        
        # 5. Grid Outage Simulation (stochastic 2-hour outage on day 3)
        grid_status = 1
        day_index = step // (24 * 60 // interval_minutes)
        if day_index == 3 and (14.0 <= hour <= 16.0):
            grid_status = 0 # Outage!
            
        # 6. EMS Dispatch Controller logic
        battery_power = 0.0
        grid_power = 0.0
        ems_action = "STANDBY"
        
        surplus = p_renewable - load_demand
        
        if grid_status == 0:
            # Islanding Mode
            if surplus >= 0:
                battery_power = min(surplus, max_charge_kw)
                charge_energy = battery_power * 0.95 * dt_hours
                battery_soc += (charge_energy / battery_capacity_kwh) * 100.0
                ems_action = "ISLAND_CHARGE" if battery_power > 0 else "ISLAND_BALANCED"
            else:
                if battery_soc > min_soc:
                    battery_power = max(surplus, -max_discharge_kw)
                    discharge_energy = battery_power * (1.0 / 0.95) * dt_hours
                    battery_soc += (discharge_energy / battery_capacity_kwh) * 100.0
                    ems_action = "ISLAND_DISCHARGE"
                else:
                    battery_power = 0.0
                    ems_action = "ISLAND_LOAD_SHED"
            grid_power = 0.0
        else:
            # Connected Mode
            if surplus >= 0:
                # Renewable surplus charges battery
                if battery_soc < max_soc:
                    battery_power = min(surplus, max_charge_kw)
                    charge_energy = battery_power * 0.95 * dt_hours
                    battery_soc += (charge_energy / battery_capacity_kwh) * 100.0
                    grid_power = -(surplus - battery_power) # export remaining
                    ems_action = "RENEWABLE_CHARGE"
                else:
                    # Battery full -> export all
                    grid_power = -surplus
                    ems_action = "GRID_EXPORT"
            else:
                # Deficit -> BESS support or Grid fallback
                deficit = abs(surplus)
                is_peak_tariff = (14.0 <= hour <= 20.0) # 2 PM to 8 PM peak price
                
                if battery_soc > min_soc and (is_peak_tariff or load_demand > 45.0):
                    # Discharge BESS to support grid/save cost
                    discharge_needed = min(deficit, max_discharge_kw)
                    battery_power = -discharge_needed
                    discharge_energy = battery_power * (1.0 / 0.95) * dt_hours
                    battery_soc += (discharge_energy / battery_capacity_kwh) * 100.0
                    grid_power = deficit - discharge_needed
                    ems_action = "BATTERY_SUPPORT" if not (load_demand > 45.0) else "PEAK_SHAVING_DISCHARGE"
                else:
                    # Drained battery or cheap rate -> grid fallback
                    battery_power = 0.0
                    grid_power = deficit
                    ems_action = "GRID_FALLBACK"
                    
                    # If off-peak (nighttime) and SOC very low, slow charge from grid
                    if battery_soc < 35.0 and (hour < 6.0 or hour > 22.0):
                        grid_charge = 15.0 # slow charge
                        battery_power = grid_charge
                        charge_energy = battery_power * 0.95 * dt_hours
                        battery_soc += (charge_energy / battery_capacity_kwh) * 100.0
                        grid_power = deficit + grid_charge
                        ems_action = "GRID_CHARGING_OFFPEAK"
                        
        # Clamp SOC
        battery_soc = max(0.0, min(battery_soc, 100.0))
        
        # Round calculations for CSV aesthetics
        rows.append({
            "timestamp": timestamp_str,
            "solar_power": round(solar_power, 2),
            "wind_power": round(wind_power, 2),
            "battery_soc": round(battery_soc, 2),
            "load_demand": round(load_demand, 2),
            "grid_power": round(grid_power, 2),
            "temperature": round(temperature, 2),
            "ems_action": ems_action
        })
        
    # Write to CSV
    csv_file = "dataset.csv"
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "solar_power", "wind_power", "battery_soc", 
            "load_demand", "grid_power", "temperature", "ems_action"
        ])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"[Generator] Created microgrid dataset with {len(rows)} entries in {csv_file}")

if __name__ == "__main__":
    generate_microgrid_dataset(days=7, interval_minutes=5)
