import os
import sqlite3
import json
import time
from datetime import datetime
import threading

# Environment configuration for production switches
POSTGRES_URI = os.getenv("POSTGRES_URI")
MONGO_URI = os.getenv("MONGO_URI")
INFLUXDB_URI = os.getenv("INFLUXDB_URI")

DB_FILE = "microgrid.db"

class DatabaseManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_tables()

    def _initialize_tables(self):
        with self.lock:
            cursor = self.conn.cursor()
            
            # 1. Relational Layer: EMS Configurations & Grid Tariffs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ems_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 2. Time-Series Layer: SCADA Historian
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scada_historian (
                    timestamp REAL PRIMARY KEY,
                    solar_power REAL,
                    solar_voltage REAL,
                    solar_current REAL,
                    solar_temperature REAL,
                    wind_power REAL,
                    wind_speed REAL,
                    wind_rpm REAL,
                    battery_soc REAL,
                    battery_soh REAL,
                    battery_voltage REAL,
                    battery_current REAL,
                    battery_temperature REAL,
                    grid_status INTEGER,
                    grid_voltage REAL,
                    grid_frequency REAL,
                    grid_power REAL,
                    load_demand REAL,
                    load_current REAL,
                    load_voltage REAL,
                    inverter_status TEXT,
                    inverter_efficiency REAL,
                    inverter_output_power REAL,
                    ems_action TEXT,
                    electricity_cost REAL
                )
            """)
            
            # 3. Document Layer: Alarms & Events Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alarms_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    severity TEXT,
                    source TEXT,
                    message TEXT,
                    status TEXT
                )
            """)

            # 4. Individual Asset Real-Time Data Storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS solar_realtime (
                    timestamp REAL PRIMARY KEY,
                    irradiance REAL,
                    ambient_temp REAL,
                    panel_temp REAL,
                    dc_voltage REAL,
                    dc_current REAL,
                    ac_power REAL,
                    inverter_status TEXT,
                    inverter_efficiency REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wind_realtime (
                    timestamp REAL PRIMARY KEY,
                    wind_speed REAL,
                    wind_direction REAL,
                    air_density REAL,
                    blade_angle REAL,
                    turbine_rpm REAL,
                    generator_voltage REAL,
                    generator_current REAL,
                    generated_power REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battery_realtime (
                    timestamp REAL PRIMARY KEY,
                    soc REAL,
                    soh REAL,
                    voltage REAL,
                    current REAL,
                    temperature REAL,
                    cell_voltage REAL,
                    cell_temperature REAL,
                    charge_rate REAL,
                    discharge_rate REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grid_realtime (
                    timestamp REAL PRIMARY KEY,
                    voltage REAL,
                    current REAL,
                    frequency REAL,
                    power_factor REAL,
                    import_power REAL,
                    export_power REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS load_realtime (
                    timestamp REAL PRIMARY KEY,
                    load_voltage REAL,
                    load_current REAL,
                    active_power REAL,
                    reactive_power REAL,
                    apparent_power REAL,
                    energy_consumption REAL
                )
            """)
            self.conn.commit()
            
        # Seed default settings if empty or set to old USD defaults (uses set_setting/get_setting)
        if self.get_setting("battery_min_soc") is None:
            self.set_setting("battery_min_soc", "20.0")
        if self.get_setting("battery_max_soc") is None:
            self.set_setting("battery_max_soc", "100.0")
        if self.get_setting("tariff_peak_start") is None:
            self.set_setting("tariff_peak_start", "14:00")
        if self.get_setting("tariff_peak_end") is None:
            self.set_setting("tariff_peak_end", "20:00")
        
        peak_val = self.get_setting("tariff_peak_rate")
        if peak_val is None or peak_val == "0.35":
            self.set_setting("tariff_peak_rate", "7.50") # ₹/kWh
            
        offpeak_val = self.get_setting("tariff_offpeak_rate")
        if offpeak_val is None or offpeak_val == "0.12":
            self.set_setting("tariff_offpeak_rate", "4.50") # ₹/kWh
            
        if self.get_setting("export_enabled") is None:
            self.set_setting("export_enabled", "true")

    # Relational Settings API
    def get_setting(self, key: str, default: str = None) -> str:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM ems_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO ems_settings (key, value) VALUES (?, ?)", (key, str(value)))
            self.conn.commit()

    # Time-Series Historian API
    def log_telemetry(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scada_historian (
                    timestamp, solar_power, solar_voltage, solar_current, solar_temperature,
                    wind_power, wind_speed, wind_rpm,
                    battery_soc, battery_soh, battery_voltage, battery_current, battery_temperature,
                    grid_status, grid_voltage, grid_frequency, grid_power,
                    load_demand, load_current, load_voltage,
                    inverter_status, inverter_efficiency, inverter_output_power,
                    ems_action, electricity_cost
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
            """, (
                data.get("timestamp", time.time()),
                data.get("Solar_Power", 0.0),
                data.get("Solar_Voltage", 0.0),
                data.get("Solar_Current", 0.0),
                data.get("Solar_Temperature", 0.0),
                data.get("Wind_Power", 0.0),
                data.get("Wind_Speed", 0.0),
                data.get("Wind_RPM", 0.0),
                data.get("Battery_SOC", 50.0),
                data.get("Battery_SOH", 100.0),
                data.get("Battery_Voltage", 0.0),
                data.get("Battery_Current", 0.0),
                data.get("Battery_Temperature", 25.0),
                data.get("Grid_Status", 1),
                data.get("Grid_Voltage", 0.0),
                data.get("Grid_Frequency", 50.0),
                data.get("Grid_Power", 0.0),
                data.get("Load_Demand", 0.0),
                data.get("Load_Current", 0.0),
                data.get("Load_Voltage", 0.0),
                data.get("Inverter_Status", "RUNNING"),
                data.get("Inverter_Efficiency", 98.5),
                data.get("Inverter_Output_Power", 0.0),
                data.get("ems_action", "STANDBY"),
                data.get("electricity_cost", 0.0)
            ))
            self.conn.commit()

    def get_historical_data(self, limit: int = 100) -> list:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM scada_historian ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    # Document Alarm API
    def trigger_alarm(self, severity: str, source: str, message: str) -> dict:
        with self.lock:
            cursor = self.conn.cursor()
            timestamp = time.time()
            
            # Check if an alarm with a similar message prefix already exists to prevent duplicate spamming from floating-point updates (e.g. temperatures or voltages)
            prefix = message.split(':')[0].split('warning')[0].split('detected')[0].strip()
            
            cursor.execute("""
                SELECT id, message FROM alarms_log 
                WHERE source = ? AND status = 'ACTIVE'
            """, (source,))
            rows = cursor.fetchall()
            
            matched_id = None
            for row in rows:
                row_prefix = row["message"].split(':')[0].split('warning')[0].split('detected')[0].strip()
                if row_prefix == prefix:
                    matched_id = row["id"]
                    break
                    
            if matched_id:
                # Update the existing alarm's timestamp and message instead of adding a duplicate row
                cursor.execute("""
                    UPDATE alarms_log 
                    SET timestamp = ?, message = ? 
                    WHERE id = ?
                """, (timestamp, message, matched_id))
                self.conn.commit()
                return {
                    "id": matched_id,
                    "timestamp": timestamp,
                    "severity": severity,
                    "source": source,
                    "message": message,
                    "status": "ACTIVE"
                }

            # If no existing active alarm matched the prefix, insert a new one
            cursor.execute("""
                INSERT INTO alarms_log (timestamp, severity, source, message, status)
                VALUES (?, ?, ?, ?, 'ACTIVE')
            """, (timestamp, severity, source, message))
            alarm_id = cursor.lastrowid
            self.conn.commit()
            return {
                "id": alarm_id,
                "timestamp": timestamp,
                "severity": severity,
                "source": source,
                "message": message,
                "status": "ACTIVE"
            }
    def acknowledge_alarm(self, alarm_id: int):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE alarms_log SET status = 'ACKNOWLEDGED' WHERE id = ?", (alarm_id,))
            self.conn.commit()

    def clear_alarm(self, alarm_id: int):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE alarms_log SET status = 'CLEARED' WHERE id = ?", (alarm_id,))
            self.conn.commit()

    def clear_alarm_by_message(self, source: str, message: str):
        with self.lock:
            cursor = self.conn.cursor()
            
            # Extract the message prefix to match dynamically generated messages
            prefix = message.split(':')[0].split('warning')[0].split('detected')[0].strip()
            
            # Retrieve all currently active or acknowledged alarms for this source
            cursor.execute("""
                SELECT id, message FROM alarms_log 
                WHERE source = ? AND status IN ('ACTIVE', 'ACKNOWLEDGED')
            """, (source,))
            rows = cursor.fetchall()
            
            # Update matching alarms to CLEARED
            for row in rows:
                row_prefix = row["message"].split(':')[0].split('warning')[0].split('detected')[0].strip()
                if row_prefix == prefix:
                    cursor.execute("UPDATE alarms_log SET status = 'CLEARED' WHERE id = ?", (row["id"],))
            self.conn.commit()

    def get_active_alarms(self) -> list:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM alarms_log WHERE status IN ('ACTIVE', 'ACKNOWLEDGED') ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_alarms(self, limit: int = 100) -> list:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM alarms_log ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def log_solar_realtime(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO solar_realtime (
                    timestamp, irradiance, ambient_temp, panel_temp,
                    dc_voltage, dc_current, ac_power, inverter_status, inverter_efficiency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", time.time()),
                data.get("irradiance", 0.0),
                data.get("ambient_temp", 25.0),
                data.get("panel_temp", 25.0),
                data.get("dc_voltage", 0.0),
                data.get("dc_current", 0.0),
                data.get("ac_power", 0.0),
                data.get("inverter_status", "STANDBY"),
                data.get("inverter_efficiency", 98.5)
            ))
            self.conn.commit()

    def log_wind_realtime(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO wind_realtime (
                    timestamp, wind_speed, wind_direction, air_density,
                    blade_angle, turbine_rpm, generator_voltage, generator_current, generated_power
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", time.time()),
                data.get("wind_speed", 0.0),
                data.get("wind_direction", 0.0),
                data.get("air_density", 1.225),
                data.get("blade_angle", 0.0),
                data.get("turbine_rpm", 0.0),
                data.get("generator_voltage", 0.0),
                data.get("generator_current", 0.0),
                data.get("generated_power", 0.0)
            ))
            self.conn.commit()

    def log_battery_realtime(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO battery_realtime (
                    timestamp, soc, soh, voltage, current, temperature,
                    cell_voltage, cell_temperature, charge_rate, discharge_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", time.time()),
                data.get("soc", 50.0),
                data.get("soh", 100.0),
                data.get("voltage", 0.0),
                data.get("current", 0.0),
                data.get("temperature", 25.0),
                data.get("cell_voltage", 3.2),
                data.get("cell_temperature", 25.0),
                data.get("charge_rate", 0.0),
                data.get("discharge_rate", 0.0)
            ))
            self.conn.commit()

    def log_grid_realtime(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO grid_realtime (
                    timestamp, voltage, current, frequency, power_factor, import_power, export_power
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", time.time()),
                data.get("voltage", 0.0),
                data.get("current", 0.0),
                data.get("frequency", 50.0),
                data.get("power_factor", 1.0),
                data.get("import_power", 0.0),
                data.get("export_power", 0.0)
            ))
            self.conn.commit()

    def log_load_realtime(self, data: dict):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO load_realtime (
                    timestamp, load_voltage, load_current, active_power,
                    reactive_power, apparent_power, energy_consumption
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", time.time()),
                data.get("load_voltage", 0.0),
                data.get("load_current", 0.0),
                data.get("active_power", 0.0),
                data.get("reactive_power", 0.0),
                data.get("apparent_power", 0.0),
                data.get("energy_consumption", 0.0)
            ))
            self.conn.commit()

    def get_realtime_history(self, asset_type: str, limit: int = 100) -> list:
        with self.lock:
            cursor = self.conn.cursor()
            table_name = f"{asset_type}_realtime"
            if table_name not in ["solar_realtime", "wind_realtime", "battery_realtime", "grid_realtime", "load_realtime"]:
                return []
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

db = DatabaseManager()
