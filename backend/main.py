import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time
import threading
import csv
import io
import math
import random
from typing import List

from database import db
from simulator import MicrogridSimulator
from ems import EMSEngine
from protocols import modbus_server, opc_server, can_bus, iec_61850, mqtt_broker
from ai_models import load_forecaster, renewable_forecaster, battery_forecaster, anomaly_detector, maintenance_suite
from datetime import datetime

# Real-time Asset connection status and simulation variables
assets_state = {
    "solar": {"status": "CONNECTED", "protocol": "Sample CSV", "collecting": True, "last_updated": 0.0, "sensor_values": {}},
    "wind": {"status": "CONNECTED", "protocol": "Sample CSV", "collecting": True, "last_updated": 0.0, "sensor_values": {}},
    "battery": {"status": "CONNECTED", "protocol": "Sample CSV", "collecting": True, "last_updated": 0.0, "sensor_values": {}},
    "grid": {"status": "CONNECTED", "protocol": "Sample CSV", "collecting": True, "last_updated": 0.0, "sensor_values": {}},
    "load": {"status": "CONNECTED", "protocol": "Sample CSV", "collecting": True, "last_updated": 0.0, "sensor_values": {}}
}
total_load_kwh = 0.0

# Pre-load sample datasets for offline fallback
def load_default_sample_datasets():
    import os
    import csv
    cache = {
        "solar": [],
        "wind": [],
        "battery": [],
        "grid": [],
        "load": []
    }
    for section in ["solar", "wind", "battery", "grid", "load"]:
        possible_paths = [
            f"sample_datasets/{section}_dataset.csv",
            f"e:/scada/sample_datasets/{section}_dataset.csv",
            f"../sample_datasets/{section}_dataset.csv",
            f"backend/sample_datasets/{section}_dataset.csv"
        ]
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    cache[section] = list(reader)
                print(f"[EMS-SCADA] Pre-loaded sample dataset for {section}: {len(cache[section])} rows.")
            except Exception as e:
                print(f"[EMS-SCADA] Warning: failed to load sample dataset for {section}: {e}")
    return cache

sample_datasets_cache = load_default_sample_datasets()
sample_indices = {
    "solar": 0,
    "wind": 0,
    "battery": 0,
    "grid": 0,
    "load": 0
}
total_load_kwh = 0.0

# Replay Dataset Globals
section_datasets = {
    "solar": [],
    "wind": [],
    "battery": [],
    "inverter": [],
    "load": [],
    "grid": []
}
section_indices = {
    "solar": 0,
    "wind": 0,
    "battery": 0,
    "inverter": 0,
    "load": 0,
    "grid": 0
}
replay_active = False

app = FastAPI(title="Industrial EMS + SCADA Controller API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
simulator = MicrogridSimulator()
ems = EMSEngine()

# Shared real-time state cache
latest_telemetry = {}
active_connections: List[WebSocket] = []

class ConnectionManager:
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in active_connections:
            active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead, handled during write error
                pass

ws_manager = ConnectionManager()

# Background thread event loop control
running = True
main_loop = None

def get_field_from_row(row, keys, default=0.0):
    for k in keys:
        for r_key in row.keys():
            if r_key.strip().lower() == k.lower():
                val = str(row[r_key]).strip()
                # Strip common units and currency symbols
                val = val.replace("kW", "").replace("%", "").replace("°C", "").replace("₹", "").replace("$", "").replace("V", "").replace("A", "").replace("Hz", "").strip()
                try:
                    return float(val)
                except ValueError:
                    return val
    return default

def run_microgrid_loop():
    """
    Continuous 1-second simulation & EMS control loop.
    Runs in a dedicated thread.
    """
    global latest_telemetry, running, section_indices, replay_active, section_datasets, main_loop, total_load_kwh
    print("[EMS-SCADA] Core control loop started.")
    
    # Track steps for RL updating
    last_state = None
    last_action = None
    
    while running:
        try:
            start_time = time.time()
            
            if simulator.simulation_mode == "LIVE":
                time.sleep(1.0)
                continue
                
            # Step 1. Physics Step: Read environment, PV curves, load base
            phys_data = simulator.update_states()
            
            # Check for Replay overrides on each section individually
            if replay_active:
                # Hour of day from current time (0 to 24 floats)
                struct_time = time.localtime(start_time)
                hour = struct_time.tm_hour + struct_time.tm_min / 60.0
                phys_data["hour"] = hour
                phys_data["timestamp"] = start_time
                
                # Solar PV Replay Override
                if len(section_datasets["solar"]) > 0:
                    row = section_datasets["solar"][section_indices["solar"]]
                    section_indices["solar"] = (section_indices["solar"] + 1) % len(section_datasets["solar"])
                    phys_data["Solar_Power"] = get_field_from_row(row, ["pv power", "pv_power", "solar_power", "solar power", "power", "solar", "solar_pv_power", "solar_kw"], 0.0)
                    phys_data["Solar_Voltage"] = get_field_from_row(row, ["pv voltage", "pv_voltage", "solar_voltage", "solar voltage", "voltage"], 400.0)
                    phys_data["Solar_Current"] = get_field_from_row(row, ["pv current", "pv_current", "solar_current", "solar current", "current"], 0.0)
                    phys_data["Solar_Temperature"] = get_field_from_row(row, ["panel_temperature", "panel temperature", "solar_temperature", "solar temperature", "panel_temp", "temperature"], 25.0)
                
                if not simulator.solar_enabled:
                    phys_data["Solar_Power"] = 0.0
                    phys_data["Solar_Voltage"] = 0.0
                    phys_data["Solar_Current"] = 0.0

                # Wind Turbine Replay Override
                if len(section_datasets["wind"]) > 0:
                    row = section_datasets["wind"][section_indices["wind"]]
                    section_indices["wind"] = (section_indices["wind"] + 1) % len(section_datasets["wind"])
                    phys_data["Wind_Power"] = get_field_from_row(row, ["wind_power", "wind power", "power", "wind", "wind_kw"], 0.0)
                    phys_data["Wind_Speed"] = get_field_from_row(row, ["wind_speed", "wind speed", "speed"], 8.0)
                    phys_data["Wind_RPM"] = get_field_from_row(row, ["turbine_rpm", "turbine rpm", "rpm", "wind_rpm"], 0.0)

                if not simulator.wind_enabled:
                    phys_data["Wind_Power"] = 0.0
                    phys_data["Wind_RPM"] = 0.0

                # Load Demand Replay Override
                if len(section_datasets["load"]) > 0:
                    row = section_datasets["load"][section_indices["load"]]
                    section_indices["load"] = (section_indices["load"] + 1) % len(section_datasets["load"])
                    phys_data["Load_Demand"] = get_field_from_row(row, ["load_demand", "load demand", "load", "demand", "active power", "required power", "load_kw"], 15.0)
                    phys_data["Load_Voltage"] = get_field_from_row(row, ["load_voltage", "load voltage", "voltage"], 230.0)
                    phys_data["Load_Current"] = get_field_from_row(row, ["load_current", "load current", "current"], 0.0)
            
            # Step 2. EMS Decision: Compute dispatch
            settings = {
                "battery_min_soc": db.get_setting("battery_min_soc", "20.0"),
                "export_enabled": db.get_setting("export_enabled", "true")
            }
            
            # Inject Grid Status, battery status, temperature and SOC into phys_data before EMS runs so it can detect outages and isolation
            phys_data["Grid_Status"] = 0 if (simulator.grid_status == 0 or not simulator.grid_enabled) else 1
            phys_data["battery_enabled"] = simulator.battery_enabled
            phys_data["Battery_Temperature"] = simulator.battery_temp
            phys_data["Battery_SOC"] = simulator.battery_soc
            
            # Decide optimization mode
            opt_mode = db.get_setting("optimization_mode", "NORMAL") # NORMAL, OPTIMIZED
            
            # EMS Dispatch State Machine
            dispatch = ems.compute_dispatch(phys_data, mode=opt_mode)
            
            # If OPTIMIZED, override battery power using Reinforcement Learning actions occasionally
            if opt_mode == "OPTIMIZED" and simulator.battery_enabled:
                rl_offset = ems.select_rl_action(phys_data["hour"], simulator.battery_soc, dispatch["battery_power"])
                dispatch["battery_power"] = max(-60.0, min(50.0, dispatch["battery_power"] + rl_offset))
                # Re-calculate grid power following STRICT PRIORITY:
                # 1. Renewables → Load first
                # 2. Excess renewable → Battery charge
                # 3. No renewable → Battery discharge
                # 4. Battery depleted → Grid (last resort)
                if simulator.grid_enabled and simulator.grid_status == 1:
                    surplus = (phys_data["Solar_Power"] + phys_data["Wind_Power"]) - phys_data["Load_Demand"]
                    batt_pwr = dispatch["battery_power"]
                    if surplus >= 0:
                        # Renewables cover load — charge battery, export excess
                        batt_pwr = min(surplus, 50.0)  # cap at max charge rate
                        dispatch["battery_power"] = batt_pwr
                        leftover = surplus - batt_pwr
                        dispatch["grid_power"] = -leftover if settings["export_enabled"] == "true" else 0.0
                    else:
                        # Deficit — battery discharges, grid covers only the gap battery can't fill
                        deficit = abs(surplus)
                        discharge = min(deficit, abs(batt_pwr) if batt_pwr < 0 else 0.0)
                        dispatch["grid_power"] = max(0.0, deficit - discharge)
                else:
                    dispatch["grid_power"] = 0.0
                dispatch["ems_action"] = "RL_OPTIMIZED_DISPATCH"

                
            # If battery is disabled, BESS doesn't charge/discharge and grid absorbs/supplies all surplus/deficit (if enabled)
            if not simulator.battery_enabled:
                dispatch["battery_power"] = 0.0
                surplus = (phys_data["Solar_Power"] + phys_data["Wind_Power"]) - phys_data["Load_Demand"]
                if simulator.grid_enabled and simulator.grid_status == 1:
                    dispatch["grid_power"] = -surplus if settings["export_enabled"] == "true" else max(0.0, -surplus)
                    if surplus >= 0:
                        if settings["export_enabled"] == "true":
                            dispatch["ems_action"] = "BESS_DISCONNECTED_EXPORT"
                        else:
                            dispatch["ems_action"] = "BESS_DISCONNECTED_LIMIT"
                    else:
                        dispatch["ems_action"] = "BESS_DISCONNECTED_FALLBACK"
                else:
                    dispatch["grid_power"] = 0.0
                    if (phys_data["Solar_Power"] + phys_data["Wind_Power"]) > 0:
                        if surplus >= 0:
                            dispatch["ems_action"] = "BESS_DISCONNECTED_ISLAND_BALANCED"
                        else:
                            dispatch["ems_action"] = "BESS_DISCONNECTED_ISLAND_LOAD_SHED"
                    else:
                        dispatch["ems_action"] = "ISLANDED_BLACKOUT"

            # Force grid power to 0 if grid is disconnected or disabled
            if not simulator.grid_enabled or simulator.grid_status == 0:
                dispatch["grid_power"] = 0.0

            # Step 3. BESS Update: Feed dispatch command back into battery physics OR use Battery Replay dataset
            battery_data = {}
            replayed_batt_pwr = 0.0
            if replay_active and len(section_datasets["battery"]) > 0:
                row = section_datasets["battery"][section_indices["battery"]]
                section_indices["battery"] = (section_indices["battery"] + 1) % len(section_datasets["battery"])
                soc = get_field_from_row(row, ["battery_soc", "battery soc", "soc", "state of charge", "bess soc", "soc_pct"], 50.0)
                soh = get_field_from_row(row, ["battery_soh", "battery soh", "soh", "state of health", "bess soh"], 99.8)
                volt = get_field_from_row(row, ["battery_voltage", "battery voltage", "voltage"], 380.0)
                temp = get_field_from_row(row, ["battery_temperature", "battery temp", "temperature", "temp"], 25.0)
                
                # Temperature based safety limits
                max_charge_rate = 50.0
                max_discharge_rate = 60.0
                if not simulator.battery_enabled:
                    max_charge_rate = 0.0
                    max_discharge_rate = 0.0
                elif temp >= 55.0 or temp <= -10.0:
                    max_charge_rate = 0.0
                    max_discharge_rate = 0.0
                elif temp >= 50.0:
                    max_charge_rate = 10.0
                    max_discharge_rate = 15.0
                elif temp >= 45.0:
                    max_charge_rate = 25.0
                    max_discharge_rate = 30.0
                elif temp <= 0.0:
                    max_charge_rate = 0.0
                    max_discharge_rate = 30.0
                
                min_soc = 20.0
                max_soc = 95.0
                
                surplus = (phys_data["Solar_Power"] + phys_data["Wind_Power"]) - phys_data["Load_Demand"]
                
                if surplus > 0:
                    # Surplus: Charge BESS first, never discharge
                    if soc < max_soc:
                        replayed_batt_pwr = min(surplus, max_charge_rate)
                    else:
                        replayed_batt_pwr = 0.0
                else:
                    # Deficit: Discharge BESS first, never charge
                    deficit = abs(surplus)
                    if soc > min_soc:
                        replayed_batt_pwr = -min(deficit, max_discharge_rate)
                    else:
                        replayed_batt_pwr = 0.0
                
                curr = round((replayed_batt_pwr * 1000.0) / volt, 2)
                
                # Override battery SOC in simulator to align with dataset
                simulator.battery_soc = soc
                battery_data = {
                    "Battery_SOC": soc,
                    "Battery_SOH": soh,
                    "Battery_Voltage": volt,
                    "Battery_Current": curr,
                    "Battery_Power": round(replayed_batt_pwr, 2),
                    "Battery_Temperature": temp
                }
            else:
                battery_data = simulator.update_battery_physics(dispatch["battery_power"])
                replayed_batt_pwr = dispatch["battery_power"]
            
            if not simulator.battery_enabled:
                battery_data["Battery_Current"] = 0.0
                battery_data["Battery_Power"] = 0.0
            
            # Step 4. Grid Update: Grid voltage, power parameters OR use Grid Replay dataset
            grid_data = {}
            if replay_active and len(section_datasets["grid"]) > 0:
                row = section_datasets["grid"][section_indices["grid"]]
                section_indices["grid"] = (section_indices["grid"] + 1) % len(section_datasets["grid"])
                grid_status_str = str(get_field_from_row(row, ["grid_status", "grid status", "status", "grid status", "signal status"], "ON")).strip().upper()
                g_volt = get_field_from_row(row, ["grid_voltage", "grid voltage", "voltage"], 400.0)
                g_freq = get_field_from_row(row, ["grid_frequency", "grid frequency", "frequency", "grid_frequency_hz"], 50.0)
                
                # Grid priority rule: Grid covers only what renewables + BESS cannot supply/absorb
                surplus = (phys_data["Solar_Power"] + phys_data["Wind_Power"]) - phys_data["Load_Demand"]
                if surplus > 0:
                    # Export the remaining surplus after charging the battery
                    leftover = surplus - replayed_batt_pwr
                    g_power = -leftover
                else:
                    # Deficit: grid power imports cover the rest of the deficit
                    g_power = abs(surplus) - abs(replayed_batt_pwr)
                
                grid_data = {
                    "Grid_Status": 0 if grid_status_str in ["OFF", "0", "OUTAGE", "OFFLINE"] else 1,
                    "Grid_Voltage": g_volt,
                    "Grid_Frequency": g_freq,
                    "Grid_Power": g_power
                }
            else:
                grid_data = simulator.get_grid_telemetry(dispatch["grid_power"])
                
            if not simulator.grid_enabled or simulator.grid_status == 0:
                grid_data["Grid_Status"] = 0
                grid_data["Grid_Voltage"] = 0.0
                grid_data["Grid_Frequency"] = 0.0
                grid_data["Grid_Power"] = 0.0
            
            # Step 5. Inverter Update: Inverter conversion efficiency OR use Inverter Replay dataset
            inverter_data = {}
            if replay_active and len(section_datasets["inverter"]) > 0:
                row = section_datasets["inverter"][section_indices["inverter"]]
                section_indices["inverter"] = (section_indices["inverter"] + 1) % len(section_datasets["inverter"])
                inv_eff = get_field_from_row(row, ["inverter_efficiency", "inverter efficiency", "efficiency"], 98.5)
                inv_status = str(get_field_from_row(row, ["inverter_status", "inverter status", "status"], "RUNNING"))
                
                # Compute inverter output power dynamically based on Load and Grid power
                ac_output = max(0.0, phys_data["Load_Demand"] - grid_data["Grid_Power"])
                
                inverter_data = {
                    "Inverter_Status": inv_status,
                    "Inverter_Efficiency": inv_eff,
                    "Inverter_Output_Power": round(ac_output, 2)
                }
            else:
                dc_input = phys_data["Solar_Power"] + phys_data["Wind_Power"] + (abs(dispatch["battery_power"]) if dispatch["battery_power"] < 0 else 0)
                ac_output = max(0.0, phys_data["Load_Demand"] - dispatch["grid_power"])
                inverter_data = simulator.get_inverter_telemetry(dc_input, ac_output)
            
            # If load shedding is active, update load demand and current in telemetry
            if dispatch.get("load_shedding_level", 0) > 0:
                if not simulator.battery_enabled and not (simulator.grid_enabled and simulator.grid_status == 1):
                    # BESS and Grid both offline: load must exactly match available solar + wind power
                    p_renewable = phys_data["Solar_Power"] + phys_data["Wind_Power"]
                    phys_data["Load_Demand"] = round(min(dispatch["original_load"], p_renewable), 2)
                else:
                    reduction_factors = {0: 1.0, 1: 0.7, 2: 0.4, 3: 0.15}
                    factor = reduction_factors.get(dispatch["load_shedding_level"], 1.0)
                    phys_data["Load_Demand"] = round(dispatch["original_load"] * factor, 2)
                phys_data["Load_Current"] = round((phys_data["Load_Demand"] * 1000.0) / phys_data["Load_Voltage"], 2)

            # 6. Aggregate SCADA telemetry tags
            telemetry = {
                **phys_data,
                **battery_data,
                **grid_data,
                **inverter_data,
                "ems_action": dispatch["ems_action"],
                "electricity_cost": dispatch["electricity_cost"],
                "load_shedding_level": dispatch.get("load_shedding_level", 0),
                "original_load": dispatch.get("original_load", phys_data["Load_Demand"]),
                "active_failures": list(simulator.digital_twin_failures)
            }
            
            # 7. Alarm Monitor
            ems.detect_alarms(telemetry)
            
            # Fetch active alarm count and add to telemetry
            active_alarms = db.get_active_alarms()
            telemetry["alarm_count"] = len(active_alarms)
            
            # 8. Protocol register maps update
            modbus_server.update_registers(telemetry, settings)
            opc_server.update_nodes(telemetry)
            iec_61850.update_nodes(telemetry)
            mqtt_broker.publish("scada/microgrid/telemetry", telemetry)
            
            # 9. Time-Series SCADA Logger
            db.log_telemetry(telemetry)
            
            # Simulate real-time individual asset data collection
            current_time = time.time()
            
            # Solar
            if assets_state["solar"]["collecting"]:
                if assets_state["solar"]["protocol"] == "Sample CSV" and len(sample_datasets_cache["solar"]) > 0:
                    idx = sample_indices["solar"]
                    row = sample_datasets_cache["solar"][idx]
                    sample_indices["solar"] = (idx + 1) % len(sample_datasets_cache["solar"])
                    
                    sol_p = get_field_from_row(row, ["Solar_Power", "pv power", "pv_power", "solar power", "power"], 0.0)
                    sol_v = get_field_from_row(row, ["Solar_Voltage", "pv voltage", "pv_voltage", "solar voltage"], 380.0)
                    sol_i = get_field_from_row(row, ["Solar_Current", "pv current", "pv_current", "solar current"], 0.0)
                    sol_temp = get_field_from_row(row, ["Solar_Temperature", "panel temp", "panel_temp", "solar temp"], 25.0)
                    
                    irrad = (sol_p / 100.0) * 1000.0
                    ambient = max(10.0, sol_temp - 5.0)
                    inverter_stat = "RUNNING" if sol_p > 0.5 else "STANDBY"
                    
                    solar_data = {
                        "timestamp": current_time,
                        "irradiance": round(irrad, 1),
                        "ambient_temp": round(ambient, 1),
                        "panel_temp": round(sol_temp, 1),
                        "dc_voltage": round(sol_v, 1),
                        "dc_current": round(sol_i, 2),
                        "ac_power": round(sol_p, 2),
                        "inverter_status": inverter_stat,
                        "inverter_efficiency": 98.5
                    }
                else:
                    hour_val = telemetry.get("hour", 12.0)
                    irrad = max(0.0, 1000.0 * math.sin(math.pi * (hour_val - 6.0) / 12.0)) if 6.0 <= hour_val <= 18.0 else 0.0
                    ambient = telemetry.get("ambient_temp", 25.0)
                    panel_temp = ambient + irrad * 0.02 + random.uniform(-0.5, 0.5)
                    dc_v = 380.0 if irrad > 50.0 else 0.0
                    dc_c = (irrad / 1000.0) * 210.0 if irrad > 50.0 else 0.0
                    ac_p = dc_v * dc_c * 0.985 / 1000.0
                    inverter_stat = "RUNNING" if irrad > 50.0 else "STANDBY"
                    
                    solar_data = {
                        "timestamp": current_time,
                        "irradiance": round(irrad, 1),
                        "ambient_temp": round(ambient, 1),
                        "panel_temp": round(panel_temp, 1),
                        "dc_voltage": round(dc_v, 1),
                        "dc_current": round(dc_c, 2),
                        "ac_power": round(ac_p, 2),
                        "inverter_status": inverter_stat,
                        "inverter_efficiency": 98.5
                    }
                db.log_solar_realtime(solar_data)
                assets_state["solar"]["last_updated"] = current_time
                assets_state["solar"]["sensor_values"] = solar_data
                
            # Wind
            if assets_state["wind"]["collecting"]:
                if assets_state["wind"]["protocol"] == "Sample CSV" and len(sample_datasets_cache["wind"]) > 0:
                    idx = sample_indices["wind"]
                    row = sample_datasets_cache["wind"][idx]
                    sample_indices["wind"] = (idx + 1) % len(sample_datasets_cache["wind"])
                    
                    w_speed = get_field_from_row(row, ["Wind_Speed", "wind speed", "speed"], 7.0)
                    gen_p = get_field_from_row(row, ["Wind_Power", "generated power", "wind power"], 0.0)
                    turb_rpm = get_field_from_row(row, ["Wind_RPM", "turbine rpm", "rpm"], 0.0)
                    
                    w_dir = (current_time / 10.0) % 360.0
                    air_dens = 1.225 - 0.001 * (telemetry.get("ambient_temp", 25.0) - 15.0)
                    blade_ang = max(0.0, min(45.0, (w_speed - 12.0) * 3.0)) if w_speed > 12.0 else 0.0
                    gen_v = 400.0 if turb_rpm > 0 else 0.0
                    gen_c = (gen_p * 1000.0) / (400.0 * 1.73 * 0.95) if turb_rpm > 0 else 0.0
                    
                    wind_data = {
                        "timestamp": current_time,
                        "wind_speed": round(w_speed, 1),
                        "wind_direction": round(w_dir, 1),
                        "air_density": round(air_dens, 3),
                        "blade_angle": round(blade_ang, 1),
                        "turbine_rpm": round(turb_rpm, 1),
                        "generator_voltage": round(gen_v, 1),
                        "generator_current": round(gen_c, 2),
                        "generated_power": round(gen_p, 2)
                    }
                else:
                    w_speed = telemetry.get("Wind_Speed", 7.0)
                    w_dir = (current_time / 10.0) % 360.0
                    air_dens = 1.225 - 0.001 * (telemetry.get("ambient_temp", 25.0) - 15.0)
                    blade_ang = max(0.0, min(45.0, (w_speed - 12.0) * 3.0)) if w_speed > 12.0 else 0.0
                    turb_rpm = telemetry.get("Wind_RPM", 0.0)
                    gen_v = 400.0 if turb_rpm > 0 else 0.0
                    gen_p = telemetry.get("Wind_Power", 0.0)
                    gen_c = (gen_p * 1000.0) / (400.0 * 1.73 * 0.95) if turb_rpm > 0 else 0.0
                    
                    wind_data = {
                        "timestamp": current_time,
                        "wind_speed": round(w_speed, 1),
                        "wind_direction": round(w_dir, 1),
                        "air_density": round(air_dens, 3),
                        "blade_angle": round(blade_ang, 1),
                        "turbine_rpm": round(turb_rpm, 1),
                        "generator_voltage": round(gen_v, 1),
                        "generator_current": round(gen_c, 2),
                        "generated_power": round(gen_p, 2)
                    }
                db.log_wind_realtime(wind_data)
                assets_state["wind"]["last_updated"] = current_time
                assets_state["wind"]["sensor_values"] = wind_data
                
            # Battery
            if assets_state["battery"]["collecting"]:
                if assets_state["battery"]["protocol"] == "Sample CSV" and len(sample_datasets_cache["battery"]) > 0:
                    idx = sample_indices["battery"]
                    row = sample_datasets_cache["battery"][idx]
                    sample_indices["battery"] = (idx + 1) % len(sample_datasets_cache["battery"])
                    
                    bat_soc = get_field_from_row(row, ["Battery_SOC", "soc"], 50.0)
                    bat_soh = get_field_from_row(row, ["Battery_SOH", "soh"], 100.0)
                    bat_v = get_field_from_row(row, ["Battery_Voltage", "voltage"], 380.0)
                    bat_i = get_field_from_row(row, ["Battery_Current", "current"], 0.0)
                    bat_temp = get_field_from_row(row, ["Battery_Temperature", "temperature"], 25.0)
                    
                    cell_v = bat_v / 120.0
                    cell_temp = bat_temp + random.uniform(-0.2, 0.2)
                    chg_r = bat_i if bat_i > 0 else 0.0
                    dis_r = abs(bat_i) if bat_i < 0 else 0.0
                    
                    battery_data = {
                        "timestamp": current_time,
                        "soc": round(bat_soc, 2),
                        "soh": round(bat_soh, 2),
                        "voltage": round(bat_v, 1),
                        "current": round(bat_i, 2),
                        "temperature": round(bat_temp, 1),
                        "cell_voltage": round(cell_v, 3),
                        "cell_temperature": round(cell_temp, 1),
                        "charge_rate": round(chg_r, 2),
                        "discharge_rate": round(dis_r, 2)
                    }
                else:
                    bat_soc = telemetry.get("Battery_SOC", 50.0)
                    bat_soh = telemetry.get("Battery_SOH", 100.0)
                    bat_v = telemetry.get("Battery_Voltage", 380.0)
                    bat_i = telemetry.get("Battery_Current", 0.0)
                    bat_temp = telemetry.get("Battery_Temperature", 25.0)
                    cell_v = bat_v / 120.0
                    cell_temp = bat_temp + random.uniform(-0.2, 0.2)
                    chg_r = bat_i if bat_i > 0 else 0.0
                    dis_r = abs(bat_i) if bat_i < 0 else 0.0
                    
                    battery_data = {
                        "timestamp": current_time,
                        "soc": round(bat_soc, 2),
                        "soh": round(bat_soh, 2),
                        "voltage": round(bat_v, 1),
                        "current": round(bat_i, 2),
                        "temperature": round(bat_temp, 1),
                        "cell_voltage": round(cell_v, 3),
                        "cell_temperature": round(cell_temp, 1),
                        "charge_rate": round(chg_r, 2),
                        "discharge_rate": round(dis_r, 2)
                    }
                db.log_battery_realtime(battery_data)
                assets_state["battery"]["last_updated"] = current_time
                assets_state["battery"]["sensor_values"] = battery_data
                
            # Grid
            if assets_state["grid"]["collecting"]:
                if assets_state["grid"]["protocol"] == "Sample CSV" and len(sample_datasets_cache["grid"]) > 0:
                    idx = sample_indices["grid"]
                    row = sample_datasets_cache["grid"][idx]
                    sample_indices["grid"] = (idx + 1) % len(sample_datasets_cache["grid"])
                    
                    g_p = get_field_from_row(row, ["Grid_Power", "grid power", "power"], 0.0)
                    g_volt = get_field_from_row(row, ["Grid_Voltage", "voltage"], 400.0)
                    g_freq = get_field_from_row(row, ["Grid_Frequency", "frequency"], 50.0)
                    
                    grid_status_val = 1 if g_volt > 50.0 else 0
                    g_c = abs(g_p) * 1000.0 / (400.0 * 1.73) if grid_status_val == 1 else 0.0
                    g_pf = 0.98 if grid_status_val == 1 else 0.0
                    imp_p = g_p if g_p > 0 else 0.0
                    exp_p = abs(g_p) if g_p < 0 else 0.0
                    
                    grid_data = {
                        "timestamp": current_time,
                        "voltage": round(g_volt, 1),
                        "current": round(g_c, 2),
                        "frequency": round(g_freq, 3),
                        "power_factor": g_pf,
                        "import_power": round(imp_p, 2),
                        "export_power": round(exp_p, 2)
                    }
                else:
                    grid_status_val = telemetry.get("Grid_Status", 1)
                    g_volt = telemetry.get("Grid_Voltage", 400.0)
                    g_p = telemetry.get("Grid_Power", 0.0)
                    g_freq = telemetry.get("Grid_Frequency", 50.0)
                    g_c = abs(g_p) * 1000.0 / (400.0 * 1.73) if grid_status_val == 1 else 0.0
                    g_pf = 0.98 if grid_status_val == 1 else 0.0
                    imp_p = g_p if g_p > 0 else 0.0
                    exp_p = abs(g_p) if g_p < 0 else 0.0
                    
                    grid_data = {
                        "timestamp": current_time,
                        "voltage": round(g_volt, 1),
                        "current": round(g_c, 2),
                        "frequency": round(g_freq, 3),
                        "power_factor": g_pf,
                        "import_power": round(imp_p, 2),
                        "export_power": round(exp_p, 2)
                    }
                db.log_grid_realtime(grid_data)
                assets_state["grid"]["last_updated"] = current_time
                assets_state["grid"]["sensor_values"] = grid_data
                
            # Load
            if assets_state["load"]["collecting"]:
                if assets_state["load"]["protocol"] == "Sample CSV" and len(sample_datasets_cache["load"]) > 0:
                    idx = sample_indices["load"]
                    row = sample_datasets_cache["load"][idx]
                    sample_indices["load"] = (idx + 1) % len(sample_datasets_cache["load"])
                    
                    act_p = get_field_from_row(row, ["Load_Demand", "load demand", "demand", "power"], 15.0)
                    l_volt = get_field_from_row(row, ["Load_Voltage", "load voltage", "voltage"], 230.0)
                    l_c = get_field_from_row(row, ["Load_Current", "load current", "current"], 0.0)

                    react_p = act_p * 0.42
                    app_p = math.sqrt(act_p**2 + react_p**2)
                    total_load_kwh += (act_p / 3600.0)
                    
                    load_data = {
                        "timestamp": current_time,
                        "load_voltage": round(l_volt, 1),
                        "load_current": round(l_c, 2),
                        "active_power": round(act_p, 2),
                        "reactive_power": round(react_p, 2),
                        "apparent_power": round(app_p, 2),
                        "energy_consumption": round(total_load_kwh, 3)
                    }
                else:
                    l_volt = telemetry.get("Load_Voltage", 230.0)
                    l_c = telemetry.get("Load_Current", 0.0)
                    act_p = telemetry.get("Load_Demand", 15.0)
                    react_p = act_p * 0.42
                    app_p = math.sqrt(act_p**2 + react_p**2)
                    total_load_kwh += (act_p / 3600.0)
                    
                    load_data = {
                        "timestamp": current_time,
                        "load_voltage": round(l_volt, 1),
                        "load_current": round(l_c, 2),
                        "active_power": round(act_p, 2),
                        "reactive_power": round(react_p, 2),
                        "apparent_power": round(app_p, 2),
                        "energy_consumption": round(total_load_kwh, 3)
                    }
                db.log_load_realtime(load_data)
                assets_state["load"]["last_updated"] = current_time
                assets_state["load"]["sensor_values"] = load_data
            
            # Update cache
            latest_telemetry = telemetry
            
            # Q-learning reward update (minimize electricity cost, reduce battery wear)
            if opt_mode == "OPTIMIZED" and last_state:
                reward = -dispatch["electricity_cost"] * 1000.0 # scale cost reward
                # penalty for battery cycling
                reward -= 0.1 * abs(dispatch["battery_power"])
                # update RL
                next_hour = (phys_data["hour"] + 1.0/3600.0) % 24
                ems.update_rl_policy(
                    last_state[0], last_state[1], last_state[2], last_action,
                    next_hour, battery_data["Battery_SOC"], dispatch["battery_power"],
                    reward
                )
                
            if opt_mode == "OPTIMIZED":
                last_state = ems._get_state_key(phys_data["hour"], battery_data["Battery_SOC"], dispatch["battery_power"])
                last_action = rl_offset
            else:
                last_state = None
                last_action = None
            
            # Broadcast over websockets
            payload = {
                "telemetry": telemetry,
                "alarms": active_alarms,
                "assets_state": assets_state,
                "protocols": {
                    "modbus": modbus_server.read_registers(40001, 10),
                    "opc": opc_server.nodes,
                    "can": can_bus.encode_bms_frame(
                        telemetry["Battery_SOC"], telemetry["Battery_Voltage"], 
                        telemetry["Battery_Current"], telemetry["Battery_Temperature"]
                    ),
                    "iec61850": iec_61850.get_ln_values()
                }
            }
            # Schedule WebSocket broadcast in main thread loop
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), main_loop)
            
            # Tick sleep (maintain 1-second interval)
            elapsed = time.time() - start_time
            sleep_time = max(0.1, 1.0 - elapsed)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"[EMS-SCADA Error] Loop crash: {e}")
            time.sleep(1.0)


# Models for API Requests
class SettingModel(BaseModel):
    key: str
    value: str

class ControlModel(BaseModel):
    simulation_mode: str  # NORMAL, HIGH_RENEWABLES, etc.
    solar_override: float | None = None
    wind_override: float | None = None
    load_override: float | None = None
    solar_enabled: bool = True
    wind_enabled: bool = True
    battery_enabled: bool = True
    grid_enabled: bool = True
    fan_override: str | None = None

class AlarmAckModel(BaseModel):
    alarm_id: int

class LiveDataModel(BaseModel):
    solar_power: float
    wind_power: float
    battery_temp: float
    battery_current: float
    load_demand: float
    grid_power: float
    grid_status: int = 1
    battery_soc: float | None = None
    battery_voltage: float | None = None

# ----------------------------------------------------
# REST API ENDPOINTS
# ----------------------------------------------------

@app.post("/api/live-data")
async def receive_live_data(data: LiveDataModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    global latest_telemetry, replay_active, main_loop
    
    # 1. Switch mode to LIVE
    replay_active = False
    simulator.set_simulation_mode("LIVE")
    
    # 2. Derive voltage and SOC
    volt = data.battery_voltage
    if volt is None or volt <= 0.0:
        volt = 320.0 + 95.0 * ((data.battery_soc if data.battery_soc is not None else simulator.battery_soc) / 100.0)
        
    soc = data.battery_soc
    if soc is None:
        dt = 1.0 / 3600.0
        eff = 0.95 if data.battery_current > 0 else (1.0 / 0.95)
        batt_power = (data.battery_current * volt) / 1000.0
        simulator.battery_soc += (batt_power * eff * dt) / simulator.BATTERY_CAPACITY_KWH * 100.0
        simulator.battery_soc = max(0.0, min(simulator.battery_soc, 100.0))
        soc = simulator.battery_soc
    else:
        simulator.battery_soc = soc
        
    # Enforce battery temperature limits on physical simulator state
    simulator.battery_temp = data.battery_temp
    simulator.grid_status = data.grid_status
    
    # 3. Formulate physics telemetry state
    phys_data = {
        "timestamp": time.time(),
        "hour": (time.localtime().tm_hour + time.localtime().tm_min / 60.0),
        "Solar_Power": round(data.solar_power, 2),
        "Solar_Voltage": round(380.0 if data.solar_power > 0 else 0.0, 2),
        "Solar_Current": round((data.solar_power * 1000.0) / 380.0 if data.solar_power > 0 else 0.0, 2),
        "Solar_Temperature": round(data.battery_temp, 2),
        "Wind_Power": round(data.wind_power, 2),
        "Wind_Speed": round(7.0, 2),
        "Wind_RPM": round(120.0 + data.wind_power * 7.0 if data.wind_power > 0 else 0.0, 1),
        "Load_Demand": round(data.load_demand, 2),
        "Load_Voltage": round(230.0, 2),
        "Load_Current": round((data.load_demand * 1000.0) / 230.0, 2),
        "ambient_temp": round(data.battery_temp - 5.0, 2),
        "cloud_cover": 0.2
    }
    
    battery_data = {
        "Battery_SOC": round(soc, 2),
        "Battery_SOH": round(simulator.battery_soh, 4),
        "Battery_Voltage": round(volt, 2),
        "Battery_Current": round(data.battery_current, 2),
        "Battery_Temperature": round(data.battery_temp, 2),
        "Battery_Fan_Status": "ON" if data.battery_temp >= 35.0 else "OFF"
    }
    
    grid_data = {
        "Grid_Status": data.grid_status,
        "Grid_Voltage": round(400.0 if data.grid_status == 1 else 0.0, 2),
        "Grid_Frequency": round(50.0 if data.grid_status == 1 else 0.0, 3),
        "Grid_Power": round(data.grid_power, 2)
    }
    
    # Inverter Output AC power
    ac_output = max(0.0, data.load_demand - data.grid_power)
    inverter_data = {
        "Inverter_Status": "FAULTED" if simulator.fault_active else "RUNNING",
        "Inverter_Efficiency": 98.5,
        "Inverter_Output_Power": round(ac_output, 2)
    }
    
    # 4. Compute optimal dispatch action
    temp_telemetry = {
        **phys_data,
        "battery_enabled": True,
        "Battery_Temperature": data.battery_temp,
        "Battery_SOC": soc,
        "Grid_Status": data.grid_status
    }
    dispatch = ems.compute_dispatch(temp_telemetry, mode="NORMAL")
    
    # 5. Aggregate final telemetry tags
    telemetry = {
        **phys_data,
        **battery_data,
        **grid_data,
        **inverter_data,
        "ems_action": dispatch["ems_action"],
        "electricity_cost": dispatch["electricity_cost"],
        "load_shedding_level": dispatch.get("load_shedding_level", 0),
        "original_load": data.load_demand,
        "active_failures": list(simulator.digital_twin_failures)
    }
    
    # 6. Alarms and Protocol servers update
    ems.detect_alarms(telemetry)
    active_alarms = db.get_active_alarms()
    telemetry["alarm_count"] = len(active_alarms)
    
    modbus_server.update_registers(telemetry, {
        "battery_min_soc": db.get_setting("battery_min_soc", "20.0"),
        "export_enabled": db.get_setting("export_enabled", "true")
    })
    opc_server.update_nodes(telemetry)
    iec_61850.update_nodes(telemetry)
    mqtt_broker.publish("scada/microgrid/telemetry", telemetry)
    
    # Save to historian database
    db.log_telemetry(telemetry)
    
    latest_telemetry = telemetry
    
    # Broadcast state
    payload = {
        "telemetry": telemetry,
        "alarms": active_alarms,
        "assets_state": assets_state,
        "protocols": {
            "modbus": modbus_server.read_registers(40001, 10),
            "opc": opc_server.nodes,
            "can": can_bus.encode_bms_frame(
                telemetry["Battery_SOC"], telemetry["Battery_Voltage"], 
                telemetry["Battery_Current"], telemetry["Battery_Temperature"]
            ),
            "iec61850": iec_61850.get_ln_values()
        }
    }
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), main_loop)
        
    return {
        "status": "SUCCESS",
        "message": "Live real-time telemetry package ingested successfully.",
        "telemetry": telemetry
    }


@app.get("/api/status")
def get_status():
    dataset_sizes = {sec: len(ds) for sec, ds in section_datasets.items()}
    dataset_indices = {sec: section_indices[sec] for sec in section_datasets.keys()}
    return {
        "status": "ONLINE",
        "simulation_mode": simulator.simulation_mode,
        "database_connected": True,
        "replay_active": replay_active,
        "section_dataset_sizes": dataset_sizes,
        "section_indices": dataset_indices,
        "solar_enabled": simulator.solar_enabled,
        "wind_enabled": simulator.wind_enabled,
        "battery_enabled": simulator.battery_enabled,
        "grid_enabled": simulator.grid_enabled,
        "fan_override": simulator.manual_fan_override
    }

@app.get("/api/tags")
def get_tags():
    return latest_telemetry

@app.get("/api/historical")
def get_historical(limit: int = 50):
    return db.get_historical_data(limit)

@app.get("/api/alarms")
def get_alarms():
    return {
        "active": db.get_active_alarms(),
        "all": db.get_all_alarms(50)
    }

# Helper function to verify role permissions
def verify_role(authorization: str = Header(None), required_roles: list = []) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = parts[1]
        if not token.startswith("mock-jwt-token-"):
            raise HTTPException(status_code=401, detail="Invalid token")
            
        role_part = token.replace("mock-jwt-token-", "")
        role = role_part.split("-")[0]
        
        if required_roles and role not in required_roles:
            raise HTTPException(status_code=403, detail=f"Permission denied. Role '{role}' does not have access. Required: {required_roles}")
        return role
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token verification")

# Additional Request Models
class LoginModel(BaseModel):
    username: str
    password: str

class FailureSimulationModel(BaseModel):
    failure_type: str  # FAN_FAILURE, BATTERY_RUNAWAY, INVERTER_FAULT
    active: bool

@app.post("/api/auth/login")
def login(data: LoginModel):
    username = data.username.lower()
    password = data.password
    
    valid_roles = ["admin", "operator", "engineer", "viewer"]
    if username in valid_roles and password == username:
        token = f"mock-jwt-token-{username}-{int(time.time())}"
        return {
            "status": "SUCCESS",
            "token": token,
            "role": username,
            "username": data.username
        }
    else:
        raise HTTPException(
            status_code=401, 
            detail="Invalid credentials. Use 'admin', 'operator', 'engineer', or 'viewer' as both username and password."
        )

@app.post("/api/alarms/acknowledge")
def acknowledge_alarm(data: AlarmAckModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    db.acknowledge_alarm(data.alarm_id)
    return {"status": "SUCCESS"}

@app.post("/api/alarms/clear")
def clear_alarm(data: AlarmAckModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    db.clear_alarm(data.alarm_id)
    return {"status": "SUCCESS"}

@app.post("/api/alarms/repair")
def repair_alarm(data: AlarmAckModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    
    # Retrieve alarm log details from the database
    with db.lock:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM alarms_log WHERE id = ?", (data.alarm_id,))
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Alarm not found")
        
    alarm = dict(row)
    msg = alarm["message"].lower()
    
    # ── Physical Self-Repair Actions (modifies simulator device states) ──
    if "temperature" in msg or "thermal" in msg or "runaway" in msg:
        # Cooldown battery cells to safe operating level (38°C) that keeps the fan ON for continued dissipation
        simulator.battery_temp = 38.0
        if "FAN_FAILURE" in simulator.digital_twin_failures:
            simulator.digital_twin_failures.remove("FAN_FAILURE")
        if "BATTERY_RUNAWAY" in simulator.digital_twin_failures:
            simulator.digital_twin_failures.remove("BATTERY_RUNAWAY")
    elif "soc" in msg or "charge" in msg:
        # Boost battery charge back to safe levels
        simulator.battery_soc = 60.0
    elif "inverter" in msg or "fault" in msg or "overcurrent trip" in msg:
        # Reset inverter overcurrent trip state
        simulator.fault_active = False
        simulator.fault_reason = ""
        if "INVERTER_FAULT" in simulator.digital_twin_failures:
            simulator.digital_twin_failures.remove("INVERTER_FAULT")
    elif "outage" in msg or "grid connection lost" in msg:
        # Restore utility grid connection
        simulator.grid_status = 1
        if simulator.simulation_mode == "GRID_OUTAGE":
            simulator.simulation_mode = "NORMAL"
    elif "overcurrent demand" in msg or "load feeder current" in msg:
        # Clear manual load overrides
        simulator.manual_load_override = None
        
    # Mark the alarm resolved in the database
    db.clear_alarm(data.alarm_id)
    return {"status": "SUCCESS", "message": "Physical hardware state restored successfully."}

@app.get("/api/settings")
def get_settings():
    return {
        "battery_min_soc": db.get_setting("battery_min_soc", "20.0"),
        "battery_max_soc": db.get_setting("battery_max_soc", "100.0"),
        "tariff_peak_start": db.get_setting("tariff_peak_start", "14:00"),
        "tariff_peak_end": db.get_setting("tariff_peak_end", "20:00"),
        "tariff_peak_rate": db.get_setting("tariff_peak_rate", "7.50"),
        "tariff_offpeak_rate": db.get_setting("tariff_offpeak_rate", "4.50"),
        "export_enabled": db.get_setting("export_enabled", "true"),
        "optimization_mode": db.get_setting("optimization_mode", "NORMAL")
    }

@app.post("/api/settings")
def update_settings(data: SettingModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin"])
    db.set_setting(data.key, data.value)
    return {"status": "SUCCESS"}

# ----------------------------------------------------
# REAL-TIME ASSET ACQUISITION ENDPOINTS
# ----------------------------------------------------

class ProtocolModel(BaseModel):
    protocol: str

@app.get("/api/assets/status")
def get_assets_status():
    return assets_state

@app.post("/api/assets/{asset}/connect")
async def connect_asset(asset: str, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    if asset not in assets_state:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    
    # Set to CONNECTING (Yellow)
    assets_state[asset]["status"] = "CONNECTING"
    assets_state[asset]["collecting"] = False
    
    # Simulating connection delay asynchronously
    async def finish_connect():
        await asyncio.sleep(1.0)
        if assets_state[asset]["status"] == "CONNECTING":
            assets_state[asset]["status"] = "CONNECTED"
            assets_state[asset]["collecting"] = True  # Auto-start collection
            
    asyncio.create_task(finish_connect())
    return {"status": "SUCCESS", "message": f"Connecting to {asset} sensors...", "state": assets_state[asset]}

@app.post("/api/assets/{asset}/disconnect")
def disconnect_asset(asset: str, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    if asset not in assets_state:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    assets_state[asset]["status"] = "DISCONNECTED"
    assets_state[asset]["collecting"] = False
    return {"status": "SUCCESS", "message": f"Disconnected {asset} sensors.", "state": assets_state[asset]}

@app.post("/api/assets/{asset}/start")
def start_collection(asset: str, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    if asset not in assets_state:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    if assets_state[asset]["status"] != "CONNECTED":
        raise HTTPException(status_code=400, detail="Asset must be connected to start collection.")
    assets_state[asset]["collecting"] = True
    return {"status": "SUCCESS", "message": f"Started real-time data collection for {asset}.", "state": assets_state[asset]}

@app.post("/api/assets/{asset}/stop")
def stop_collection(asset: str, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    if asset not in assets_state:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    assets_state[asset]["collecting"] = False
    return {"status": "SUCCESS", "message": f"Stopped real-time data collection for {asset}.", "state": assets_state[asset]}

@app.post("/api/assets/{asset}/protocol")
def update_asset_protocol(asset: str, data: ProtocolModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "operator", "engineer"])
    if asset not in assets_state:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    assets_state[asset]["protocol"] = data.protocol
    return {"status": "SUCCESS", "message": f"Protocol updated for {asset}.", "state": assets_state[asset]}

@app.get("/api/assets/predictions")
def get_assets_predictions():
    sol_p = latest_telemetry.get("Solar_Power", 0.0)
    sol_t = latest_telemetry.get("Solar_Temperature", 25.0)
    hour = latest_telemetry.get("hour", 12.0)
    sol_irrad = assets_state["solar"]["sensor_values"].get("irradiance", sol_p * 12.0)
    sol_humid = max(20.0, min(95.0, 80.0 - 1.5 * sol_t))
    
    sol_pred = renewable_forecaster.predict_solar(sol_irrad, sol_t, sol_humid, (hour + 1.0) % 24)
    sol_conf = round(94.0 + random.uniform(0.5, 3.5), 1)

    wind_p = latest_telemetry.get("Wind_Power", 0.0)
    wind_speed = latest_telemetry.get("Wind_Speed", 7.0)
    wind_dir = assets_state["wind"]["sensor_values"].get("wind_direction", 180.0)
    wind_temp = latest_telemetry.get("ambient_temp", 25.0)
    
    wind_pred = renewable_forecaster.predict_wind(wind_speed + random.uniform(-0.5, 0.5), wind_dir, wind_temp)
    wind_conf = round(95.0 + random.uniform(0.2, 2.8), 1)

    bat_soc = latest_telemetry.get("Battery_SOC", 50.0)
    bat_v = latest_telemetry.get("Battery_Voltage", 380.0)
    bat_i = latest_telemetry.get("Battery_Current", 0.0)
    bat_t = latest_telemetry.get("Battery_Temperature", 25.0)
    
    bat_pred = battery_forecaster.predict_next_soc(bat_soc, bat_v, bat_i, bat_t)
    bat_conf = round(98.0 + random.uniform(0.1, 1.2), 1)

    load_d = latest_telemetry.get("Load_Demand", 15.0)
    load_preds = load_forecaster.predict_next_24h(load_d)
    load_pred = load_preds[0] if load_preds else load_d
    load_conf = round(97.0 + random.uniform(0.3, 2.1), 1)

    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "solar": {
            "current": round(sol_p, 2),
            "predicted": round(sol_pred, 2),
            "confidence": sol_conf,
            "timestamp": ts_str,
            "metric_name": "Solar Power",
            "unit": "kW"
        },
        "wind": {
            "current": round(wind_p, 2),
            "predicted": round(wind_pred, 2),
            "confidence": wind_conf,
            "timestamp": ts_str,
            "metric_name": "Wind Power",
            "unit": "kW"
        },
        "battery": {
            "current": round(bat_soc, 2),
            "predicted": round(bat_pred, 2),
            "confidence": bat_conf,
            "timestamp": ts_str,
            "metric_name": "Battery SOC",
            "unit": "%"
        },
        "load": {
            "current": round(load_d, 2),
            "predicted": round(load_pred, 2),
            "confidence": load_conf,
            "timestamp": ts_str,
            "metric_name": "Load Demand",
            "unit": "kW"
        }
    }

@app.post("/api/control")
def post_control(data: ControlModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "engineer"])
    global replay_active
    # Toggling simulation overrides disables replay mode
    if data.simulation_mode != "REPLAY":
        replay_active = False
        
    simulator.set_simulation_mode(data.simulation_mode)
    simulator.manual_solar_override = data.solar_override
    simulator.manual_wind_override = data.wind_override
    simulator.manual_load_override = data.load_override
    simulator.solar_enabled = data.solar_enabled
    simulator.wind_enabled = data.wind_enabled
    simulator.battery_enabled = data.battery_enabled
    simulator.grid_enabled = data.grid_enabled
    simulator.manual_fan_override = data.fan_override
    
    # Persist toggled states to the database settings layer
    db.set_setting("solar_enabled", "true" if data.solar_enabled else "false")
    db.set_setting("wind_enabled", "true" if data.wind_enabled else "false")
    db.set_setting("battery_enabled", "true" if data.battery_enabled else "false")
    db.set_setting("grid_enabled", "true" if data.grid_enabled else "false")
    db.set_setting("fan_override", data.fan_override if data.fan_override else "AUTO")
    return {
        "status": "SUCCESS", 
        "mode": data.simulation_mode,
        "solar_enabled": simulator.solar_enabled,
        "wind_enabled": simulator.wind_enabled,
        "battery_enabled": simulator.battery_enabled,
        "grid_enabled": simulator.grid_enabled,
        "fan_override": simulator.manual_fan_override
    }

@app.post("/api/upload-dataset/{section}")
async def upload_dataset_section(section: str, file: UploadFile = File(...)):
    global section_datasets, section_indices, replay_active
    if section not in ["solar", "wind", "battery", "inverter", "load", "grid", "master"]:
        raise HTTPException(status_code=400, detail="Invalid section name")
        
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        
        rows = list(reader)
        if len(rows) == 0:
            raise HTTPException(status_code=400, detail=f"CSV file is empty")
            
        if section == "master":
            for sec in ["solar", "wind", "battery", "inverter", "load", "grid"]:
                section_datasets[sec] = rows
                section_indices[sec] = 0
        else:
            section_datasets[section] = rows
            section_indices[section] = 0
            
        replay_active = True
        simulator.set_simulation_mode("REPLAY")
        
        # Identify columns
        columns = list(rows[0].keys())
        
        return {
            "status": "SUCCESS", 
            "message": f"Successfully parsed {len(rows)} rows for section: {section}.",
            "columns_found": columns,
            "section": section,
            "replay_dataset_size": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing dataset: {str(e)}")

@app.get("/api/download-sample/{section}")
def download_sample_dataset(section: str):
    import os
    from fastapi.responses import FileResponse
    if section not in ["solar", "wind", "battery", "inverter", "load", "grid"]:
        raise HTTPException(status_code=400, detail="Invalid section name")
    
    possible_paths = [
        f"e:/scada/sample_datasets/{section}_dataset.csv",
        f"sample_datasets/{section}_dataset.csv",
        f"../sample_datasets/{section}_dataset.csv",
        f"backend/sample_datasets/{section}_dataset.csv"
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Sample dataset file not found for {section}")
        
    return FileResponse(path=file_path, filename=f"sample_{section}_dataset.csv", media_type="text/csv")

@app.get("/api/export/grid-exports")
def export_grid_exports():
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    with db.lock:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM scada_historian WHERE grid_power < 0 ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        
    if not rows:
        raise HTTPException(status_code=404, detail="No grid export records found in the database.")
        
    # Convert database rows to dictionary list
    data = [dict(row) for row in rows]
    
    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=grid_exports_dataset.csv"}
    )

@app.get("/api/export/full-telemetry")
def export_full_telemetry():
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    with db.lock:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM scada_historian ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        
    if not rows:
        raise HTTPException(status_code=404, detail="No telemetry records found in the database.")
        
    # Convert database rows to dictionary list
    data = [dict(row) for row in rows]
    
    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=full_microgrid_telemetry.csv"}
    )


@app.post("/api/toggle-replay")
def toggle_replay():
    global replay_active
    has_dataset = any(len(ds) > 0 for ds in section_datasets.values())
    if not has_dataset:
        raise HTTPException(status_code=400, detail="No dataset uploaded for any section yet.")
    replay_active = not replay_active
    if replay_active:
        simulator.set_simulation_mode("REPLAY")
    else:
        simulator.set_simulation_mode("NORMAL")
    return {"status": "SUCCESS", "replay_active": replay_active}

@app.get("/api/forecast")
def get_forecast():
    # Return 24 hour predicted outputs (sinusoidal math model)
    return ems.generate_24h_forecasts()

@app.get("/api/forecast/renewable")
def get_apex_renewable_forecast_api(timestamp: str = None, horizon_minutes: int = 180):
    """
    APEX Phase 2: Short-term renewable generation forecast (Solar & Wind)
    with automated renewable-rich window detection for Phase 3 decision engine.
    """
    from forecasting import get_renewable_forecast
    return get_renewable_forecast(timestamp, horizon_minutes)

@app.get("/api/decision/evaluate")
def get_apex_decision_evaluate_api(
    timestamp: str = None,
    solar_kw: float = None,
    wind_kw: float = None,
    battery_soc: float = None,
    grid_status: int = 1,
    export_limit_kw: float = 50.0,
    tariff_rate: float = 4.50,
    is_weekend: bool = False
):
    """
    APEX Phase 3: Evaluate production-aware energy decision for a timestep.
    Integrates machine production constraints, Phase 2 forecast, BESS dispatch, and grid allocation.
    """
    from decision_engine import apex_decision_engine
    if solar_kw is None:
        solar_kw = float(latest_telemetry.get("Solar_Power", 0.0))
    if wind_kw is None:
        wind_kw = float(latest_telemetry.get("Wind_Power", 0.0))
    if battery_soc is None:
        battery_soc = float(latest_telemetry.get("Battery_SOC", 50.0))
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return apex_decision_engine.evaluate(
        current_timestamp=timestamp,
        current_solar_kw=solar_kw,
        current_wind_kw=wind_kw,
        battery_soc=battery_soc,
        grid_status=grid_status,
        export_limit_kw=export_limit_kw,
        tariff_rate=tariff_rate,
        is_weekend=is_weekend
    )

@app.get("/api/decision/candidates")
def get_apex_candidate_schedules_api(machine_id: str = "Machine_C"):
    """
    APEX Phase 3: Query all feasible candidate production schedules and their scores.
    """
    from decision_engine import apex_decision_engine
    return apex_decision_engine.score_candidate_schedules(machine_id=machine_id)

class VerificationInputModel(BaseModel):
    solar_kw: float = 0.0
    wind_kw: float = 0.0
    battery_discharge_kw: float = 0.0
    grid_import_kw: float = 0.0
    factory_total_load_kw: float = 0.0
    battery_charge_kw: float = 0.0
    grid_export_kw: float = 0.0
    curtailment_kw: float = 0.0
    battery_soc: float = 50.0
    grid_status: int = 1
    export_limit_kw: float = 50.0
    tolerance_kw: float = 0.001

@app.post("/api/verification/verify")
def post_verify_energy_balance_api(data: VerificationInputModel):
    """
    APEX Phase 4: Strict Energy Balance and Physics Verification API.
    Verifies First Law of Energy Conservation and microgrid physical bounds.
    """
    from verification import apex_verifier
    alloc = {
        "solar_kw": data.solar_kw,
        "wind_kw": data.wind_kw,
        "battery_discharge_kw": data.battery_discharge_kw,
        "grid_import_kw": data.grid_import_kw,
        "factory_total_load_kw": data.factory_total_load_kw,
        "battery_charge_kw": data.battery_charge_kw,
        "grid_export_kw": data.grid_export_kw,
        "curtailment_kw": data.curtailment_kw
    }
    return apex_verifier.verify_timestep(
        energy_allocation=alloc,
        battery_soc=data.battery_soc,
        grid_status=data.grid_status,
        export_limit_kw=data.export_limit_kw,
        tolerance_kw=data.tolerance_kw
    )

@app.get("/api/verification/dataset")
def get_verify_dataset_api(tolerance_kw: float = 0.015):
    """
    APEX Phase 4: Full batch verification of the 7-day 2,016-step industrial dataset.
    """
    from verification import apex_verifier
    return apex_verifier.verify_timeseries_dataset(tolerance_kw=tolerance_kw)

@app.get("/api/verification/status")
def get_verification_status_api():
    """
    APEX Phase 4: Verification status of current real-time telemetry state.
    """
    from verification import apex_verifier
    sol = float(latest_telemetry.get("Solar_Power", 0.0))
    wnd = float(latest_telemetry.get("Wind_Power", 0.0))
    soc = float(latest_telemetry.get("Battery_SOC", 50.0))
    grid_pwr = float(latest_telemetry.get("Grid_Power", 0.0))
    batt_pwr = float(latest_telemetry.get("Battery_Power", 0.0))
    load_pwr = float(latest_telemetry.get("Load_Demand", 0.0))
    grid_stat = int(latest_telemetry.get("Grid_Status", 1))

    alloc = {
        "solar_kw": sol,
        "wind_kw": wnd,
        "battery_discharge_kw": max(0.0, -batt_pwr) if batt_pwr < 0 else 0.0,
        "battery_charge_kw": max(0.0, batt_pwr) if batt_pwr > 0 else 0.0,
        "grid_import_kw": max(0.0, grid_pwr) if grid_pwr > 0 else 0.0,
        "grid_export_kw": max(0.0, -grid_pwr) if grid_pwr < 0 else 0.0,
        "curtailment_kw": 0.0,
        "factory_total_load_kw": load_pwr
    }
    return apex_verifier.verify_timestep(
        energy_allocation=alloc,
        battery_soc=soc,
        grid_status=grid_stat
    )

@app.get("/api/evaluation/compare")
def get_evaluation_compare_api():
    """
    APEX Phase 5: Comprehensive 7-Day Baseline vs APEX Benchmark & Validation.
    Returns cumulative comparison, daily scenario breakdowns, and validation certification.
    """
    from evaluation import apex_evaluator
    return apex_evaluator.compare_baseline_vs_apex()

@app.get("/api/evaluation/kpis")
def get_evaluation_kpis_api():
    """
    APEX Phase 5: High-level summary KPI cards for UI dashboard consumption.
    """
    from evaluation import apex_evaluator
    res = apex_evaluator.compare_baseline_vs_apex()
    return {
        "cumulative_kpi_comparison": res["cumulative_kpi_comparison"],
        "key_takeaways": res["key_takeaways"],
        "dataset_info": res["dataset_info"]
    }

@app.get("/api/scenario/details")
def get_scenario_details_api(day_index: int = 0):
    """
    APEX Phase 6: Query detailed 24-hour time-series and APEX decisions
    for a specific day (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun).
    """
    from evaluation import apex_evaluator
    from decision_engine import apex_decision_engine

    all_rows = apex_evaluator.load_dataset()
    day_idx = max(0, min(6, day_index))
    d_rows = all_rows[day_idx * 288 : (day_idx + 1) * 288]
    
    # Sample every 30 mins (48 points)
    sampled_curve = []
    for i in range(0, 288, 6):
        r = d_rows[i]
        sampled_curve.append({
            "time": f"{int(float(r['hour'])):02d}:{int(round((float(r['hour']) % 1)*60)):02d}",
            "hour": float(r["hour"]),
            "solar_kw": float(r["solar_generation_kw"]),
            "wind_kw": float(r["wind_generation_kw"]),
            "total_renewable_kw": float(r["total_renewable_kw"]),
            "baseline_load_kw": float(r["baseline_total_load_kw"]),
            "grid_import_kw": float(r["baseline_grid_import_kw"]),
            "grid_export_kw": float(r["baseline_grid_export_kw"]),
            "curtailment_kw": float(r["baseline_curtailment_kw"]),
            "battery_soc": float(r["baseline_battery_soc"])
        })
        
    b_day = apex_evaluator.evaluate_baseline(d_rows)
    a_day = apex_evaluator.evaluate_apex(d_rows)
    
    scenario_titles = [
        "Day 1 (Mon) — Normal Industrial Operation",
        "Day 2 (Tue) — Midday Solar Surge",
        "Day 3 (Wed) — Flexible Production Shift Opportunity",
        "Day 4 (Thu) — Low Renewable & Grid Fallback",
        "Day 5 (Fri) — Unavoidable Curtailment Event",
        "Day 6 (Sat) — Weekend Light Production",
        "Day 7 (Sun) — Grid Outage & Microgrid Islanding"
    ]
    
    # Representative midday decision
    midday_row = d_rows[144]
    decision = apex_decision_engine.evaluate(
        current_timestamp=midday_row["timestamp"],
        current_solar_kw=float(midday_row["solar_generation_kw"]),
        current_wind_kw=float(midday_row["wind_generation_kw"]),
        battery_soc=float(midday_row["baseline_battery_soc"]),
        grid_status=int(midday_row["grid_status"]),
        tariff_rate=float(midday_row["tariff_rate"]),
        is_weekend=bool(int(midday_row["is_weekend"]))
    )
    
    return {
        "day_index": day_idx,
        "scenario_title": scenario_titles[day_idx],
        "scenario_tag": d_rows[100].get("scenario_tag", "NORMAL_OPERATION"),
        "baseline_summary": b_day,
        "apex_summary": a_day,
        "time_series_curve": sampled_curve,
        "representative_decision": decision
    }

@app.post("/api/twin/simulate-failure")
def post_simulate_failure(data: FailureSimulationModel, authorization: str = Header(None)):
    verify_role(authorization, required_roles=["admin", "engineer"])
    simulator.simulate_failure(data.failure_type, data.active)
    return {
        "status": "SUCCESS",
        "active_failures": list(simulator.digital_twin_failures)
    }

@app.get("/api/predictive-maintenance")
def get_predictive_maintenance():
    return maintenance_suite.compute_asset_health(latest_telemetry)

@app.get("/api/carbon-analytics")
def get_carbon_analytics():
    # Fetch total generated kWh from database historian
    cursor = db.conn.cursor()
    cursor.execute("SELECT SUM((solar_power + wind_power) / 3600.0) as total_kwh FROM scada_historian")
    row = cursor.fetchone()
    db_kwh = row["total_kwh"] if row and row["total_kwh"] else 0.0
    
    # Fetch total exported kWh from database historian (grid_power < 0 is export)
    cursor.execute("SELECT SUM(-grid_power / 3600.0) as total_export FROM scada_historian WHERE grid_power < 0")
    row_export = cursor.fetchone()
    db_export_kwh = row_export["total_export"] if row_export and row_export["total_export"] else 0.0
    
    base_savings = 12450.0  # Legacy savings base
    co2_saved = base_savings + db_kwh * 0.45
    
    # Calculate real-time renewable utilization share
    solar = latest_telemetry.get("Solar_Power", 0.0)
    wind = latest_telemetry.get("Wind_Power", 0.0)
    load = latest_telemetry.get("Load_Demand", 1.0)
    grid = latest_telemetry.get("Grid_Power", 0.0)
    
    if load <= 0:
        load = 1.0
        
    if grid <= 0:
        renewable_share = 100.0
    else:
        renewable_share = min(100.0, max(0.0, (1.0 - grid / load) * 100.0))
        
    return {
        "co2_saved_kg": round(co2_saved, 2),
        "renewable_share_pct": round(renewable_share, 1),
        "grid_import_kwh": round(db_kwh, 2),
        "grid_export_kwh": round(db_export_kwh, 2),
        "carbon_offset_rate": 0.45
    }

@app.get("/api/forecast-extended")
def get_forecast_extended():
    # Gather starting points
    current_load = latest_telemetry.get("Load_Demand", 25.0)
    current_hour = latest_telemetry.get("hour", 12.0)
    current_temp = latest_telemetry.get("ambient_temp", 25.0)
    current_cloud = latest_telemetry.get("cloud_cover", 0.2)
    current_wind = latest_telemetry.get("Wind_Speed", 7.0)
    
    # Predict loads via MLP
    load_forecasts = load_forecaster.predict_next_24h(current_load)
    
    # Run forward simulator state step predictions
    forecasts = []
    sim_soc = latest_telemetry.get("Battery_SOC", 50.0)
    
    for i in range(24):
        hour = (current_hour + i) % 24
        
        # Weather updates
        est_cloud = min(1.0, max(0.0, current_cloud + 0.1 * math.sin(2 * math.pi * i / 24) + random.uniform(-0.02, 0.02)))
        est_wind = min(30.0, max(0.0, current_wind + 2.0 * math.sin(2 * math.pi * i / 24) + random.uniform(-0.5, 0.5)))
        est_temp = min(42.0, max(10.0, current_temp + 4.0 * math.sin(2 * math.pi * (hour - 8.0) / 24)))
        
        solar_pred = renewable_forecaster.predict_solar(hour, est_cloud, est_temp)
        wind_pred = renewable_forecaster.predict_wind(hour, est_wind, est_temp)
        load_pred = load_forecasts[i]
        
        # Dispatch model simulation
        surplus = (solar_pred + wind_pred) - load_pred
        battery_power = 0.0
        grid_power = 0.0
        ems_act = "STANDBY"
        
        is_peak = ems.is_peak_hour(hour)
        
        if surplus >= 0:
            if sim_soc < 95.0:
                battery_power = min(surplus, 50.0)
                grid_power = -(surplus - battery_power)
                ems_act = "RENEWABLE_CHARGE"
            else:
                battery_power = 0.0
                grid_power = -surplus
                ems_act = "GRID_EXPORT"
        else:
            deficit = abs(surplus)
            if sim_soc > 20.0 and (is_peak or load_pred > 45.0):
                discharge = min(deficit, 60.0)
                battery_power = -discharge
                grid_power = deficit - discharge
                ems_act = "BATTERY_SUPPORT"
            else:
                battery_power = 0.0
                if sim_soc < 35.0 and not is_peak:
                    charge_rate = 15.0
                    battery_power = charge_rate
                    grid_power = deficit + charge_rate
                    ems_act = "GRID_CHARGING_OFFPEAK"
                else:
                    grid_power = deficit
                    ems_act = "GRID_FALLBACK"
                    
        # Update forward battery SOC state
        dt = 1.0
        if battery_power > 0:
            sim_soc += (battery_power * 0.95 * dt) / 200.0 * 100.0
        else:
            sim_soc += (battery_power * (1.0 / 0.95) * dt) / 200.0 * 100.0
        sim_soc = max(20.0, min(sim_soc, 95.0))
        
        forecasts.append({
            "hour_index": i,
            "hour": int(hour),
            "solar": round(solar_pred, 2),
            "wind": round(wind_pred, 2),
            "load": round(load_pred, 2),
            "battery_soc": round(sim_soc, 1),
            "battery_power": round(battery_power, 2),
            "grid_power": round(grid_power, 2),
            "ems_action": ems_act
        })
        
    return forecasts

@app.get("/api/protocols")
def get_protocols():
    return {
        "modbus_registers": modbus_server.read_registers(40001, 10),
        "opc_nodes": opc_server.nodes,
        "can_bus_bms": can_bus.encode_bms_frame(
            latest_telemetry.get("Battery_SOC", 50.0),
            latest_telemetry.get("Battery_Voltage", 400.0),
            latest_telemetry.get("Battery_Current", 0.0),
            latest_telemetry.get("Battery_Temperature", 25.0)
        ),
        "iec61850_nodes": iec_61850.get_ln_values()
    }


# ----------------------------------------------------
# WEBSOCKET TELEMETRY ROUTER
# ----------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive by receiving heartbeats
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Lifespan context alternative for starting background thread
@app.on_event("startup")
async def startup_event():
    # Start the core control loop thread
    global thread, main_loop
    main_loop = asyncio.get_running_loop()
    thread = threading.Thread(target=run_microgrid_loop, daemon=True)
    thread.start()

@app.on_event("shutdown")
def shutdown_event():
    global running
    running = False
    thread.join(timeout=1.0)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)