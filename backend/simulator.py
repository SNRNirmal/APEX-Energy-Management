import random
import math
import time
from database import db

class MicrogridSimulator:
    def __init__(self):
        # Simulation Settings & Overrides
        self.simulation_mode = "NORMAL"  # NORMAL, HIGH_RENEWABLES, LOW_RENEWABLES, GRID_OUTAGE, PEAK_LOAD, FAULT
        self.manual_solar_override = None
        self.manual_wind_override = None
        self.manual_load_override = None
        self.digital_twin_failures = [] # List of active failure simulations
        self.solar_enabled = db.get_setting("solar_enabled", "true") == "true"
        self.wind_enabled = db.get_setting("wind_enabled", "true") == "true"
        self.battery_enabled = db.get_setting("battery_enabled", "true") == "true"
        self.grid_enabled = db.get_setting("grid_enabled", "true") == "true"
        
        saved_fan = db.get_setting("fan_override", "AUTO")
        self.manual_fan_override = None if saved_fan == "AUTO" else saved_fan
        
        # Physical Constants
        self.SOLAR_MAX_CAPACITY = 100.0  # kW
        self.WIND_MAX_CAPACITY = 50.0    # kW
        self.BATTERY_CAPACITY_KWH = 200.0 # kWh
        self.BATTERY_MAX_CHARGE_KW = 50.0 # Max charge rate
        self.BATTERY_MAX_DISCHARGE_KW = 60.0 # Max discharge rate
        self.NOMINAL_GRID_VOLTAGE = 400.0 # V (3-Phase)
        self.NOMINAL_GRID_FREQ = 50.0     # Hz
        
        # State Variables (Dynamic)
        self.battery_soc = 50.0  # %
        self.battery_soh = 99.8  # %
        self.battery_temp = 25.0 # Celsius
        self.battery_voltage = 368.0 # V
        self.battery_current = 0.0   # A
        self.battery_fan_status = "OFF" # OFF, ON, FAULTED
        self.grid_status = 1     # 1 = Connected, 0 = Outage
        self.fault_active = False
        self.fault_reason = ""
        
        # Environment
        self.ambient_temp = 25.0 # Celsius
        self.wind_speed = 7.0    # m/s
        self.cloud_cover = 0.2   # 0 to 1

    def set_simulation_mode(self, mode: str):
        self.simulation_mode = mode
        if mode == "GRID_OUTAGE":
            self.grid_status = 0
        else:
            self.grid_status = 1
            
        if mode == "FAULT":
            self.fault_active = True
            self.fault_reason = "INVERTER_OVERCURRENT"
        else:
            self.fault_active = False
            self.fault_reason = ""

    def simulate_failure(self, failure_type: str, active: bool):
        if active:
            if failure_type not in self.digital_twin_failures:
                self.digital_twin_failures.append(failure_type)
        else:
            if failure_type in self.digital_twin_failures:
                self.digital_twin_failures.remove(failure_type)
                
        # Update state flags based on failures
        if "INVERTER_FAULT" in self.digital_twin_failures:
            self.fault_active = True
            self.fault_reason = "INVERTER_OVERCURRENT"
        else:
            if self.simulation_mode != "FAULT":
                self.fault_active = False
                self.fault_reason = ""

    def update_states(self, dt: float = 1.0 / 3600.0):
        """
        Runs one step of the microgrid physics simulation.
        dt is the time step in hours. 1 second = 1/3600 hour.
        """
        current_time = time.time()
        # Get hour of day from current time (0 to 24 floats)
        struct_time = time.localtime(current_time)
        hour = struct_time.tm_hour + struct_time.tm_min / 60.0 + struct_time.tm_sec / 3600.0
        
        # ----------------------------------------------------
        # 1. ENVIRONMENT STOCHASTIC SIMULATION
        # ----------------------------------------------------
        # Slowly walk ambient temperature
        self.ambient_temp += random.uniform(-0.1, 0.1)
        self.ambient_temp = max(10.0, min(self.ambient_temp, 42.0))
        
        # Wind speed random walk with diurnal component
        base_wind = 7.0 + 3.0 * math.sin(2 * math.pi * (hour - 4) / 24)
        if self.simulation_mode == "HIGH_RENEWABLES":
            self.wind_speed = base_wind + 5.0 + random.uniform(-0.5, 0.5)
            self.cloud_cover = max(0.0, self.cloud_cover - 0.05)
        elif self.simulation_mode == "LOW_RENEWABLES":
            self.wind_speed = max(0.0, random.uniform(0.0, 2.0))
            self.cloud_cover = min(1.0, self.cloud_cover + 0.05)
        else:
            self.wind_speed = base_wind + random.uniform(-1.0, 1.0)
            self.cloud_cover = max(0.0, min(1.0, self.cloud_cover + random.uniform(-0.02, 0.02)))
            
        self.wind_speed = max(0.0, min(self.wind_speed, 30.0))

        # ----------------------------------------------------
        # 2. SOLAR GENERATION PHYSICS
        # ----------------------------------------------------
        solar_power = 0.0
        solar_voltage = 0.0
        solar_current = 0.0
        solar_temperature = self.ambient_temp
        
        if 6.0 <= hour <= 18.0 and self.solar_enabled:
            # Solar peak at 12 PM
            irradiance_factor = math.sin(math.pi * (hour - 6.0) / 12.0)
            # Derating based on temperature (PV efficiency drops at high temp)
            temp_derating = 1.0 - 0.004 * (self.ambient_temp - 25.0)
            solar_power = self.SOLAR_MAX_CAPACITY * irradiance_factor * (1.0 - self.cloud_cover) * temp_derating
            solar_power = max(0.0, solar_power)
            
            # Solar tag simulations
            solar_voltage = 380.0 + 40.0 * irradiance_factor + random.uniform(-2.0, 2.0)
            solar_current = (solar_power * 1000.0) / solar_voltage if solar_voltage > 0 else 0.0
            solar_temperature = self.ambient_temp + 15.0 * irradiance_factor + random.uniform(-0.5, 0.5)
            
        if self.manual_solar_override is not None and self.solar_enabled:
            solar_power = self.manual_solar_override
            solar_voltage = 400.0 if solar_power > 0 else 0.0
            solar_current = (solar_power * 1000.0) / solar_voltage if solar_voltage > 0 else 0.0
            solar_temperature = self.ambient_temp + 5.0 if solar_power > 0 else self.ambient_temp

        # ----------------------------------------------------
        # 3. WIND GENERATION PHYSICS
        # ----------------------------------------------------
        wind_power = 0.0
        wind_rpm = 0.0
        
        cut_in = 3.0 # m/s
        rated_speed = 12.0 # m/s
        cut_out = 25.0 # m/s
        
        if cut_in <= self.wind_speed < rated_speed and self.wind_enabled:
            # Cubic power curve
            efficiency_coef = 0.45
            wind_power = self.WIND_MAX_CAPACITY * ((self.wind_speed - cut_in) / (rated_speed - cut_in)) ** 3
            wind_rpm = 100 + 400 * ((self.wind_speed - cut_in) / (rated_speed - cut_in))
        elif rated_speed <= self.wind_speed <= cut_out and self.wind_enabled:
            # Rated power plateau
            wind_power = self.WIND_MAX_CAPACITY + random.uniform(-0.5, 0.5)
            wind_rpm = 500 + random.uniform(-5.0, 5.0)
        else:
            # Under cut-in or over cut-out (feathered)
            wind_power = 0.0
            wind_rpm = 0.0 if (self.wind_speed < cut_in or not self.wind_enabled) else 10.0 # slow spin under high wind brake
            
        if self.manual_wind_override is not None and self.wind_enabled:
            wind_power = self.manual_wind_override
            wind_rpm = 450.0 if wind_power > 0 else 0.0

        # ----------------------------------------------------
        # 4. LOAD DEMAND MODEL
        # ----------------------------------------------------
        # Typical double peak load profile (8 AM peak, 7 PM peak)
        # Peak 1 (8 AM): 60 kW, Peak 2 (7 PM): 80 kW
        # Base load: 20 kW
        t1 = math.exp(-((hour - 8.0) / 2.0) ** 2)
        t2 = math.exp(-((hour - 19.0) / 3.0) ** 2)
        base_load = 25.0 + 20.0 * t1 + 35.0 * t2
        
        load_demand = base_load + random.uniform(-2.0, 2.0)
        
        if self.simulation_mode == "PEAK_LOAD":
            load_demand += 45.0 + random.uniform(-5.0, 5.0)
        elif self.simulation_mode == "FAULT":
            load_demand = max(0.0, load_demand - 15.0) # Fault drops load due to breaker trip
            
        if self.manual_load_override is not None:
            load_demand = self.manual_load_override
            
        load_demand = max(5.0, load_demand) # Never drops below 5 kW idle load
        
        load_voltage = 230.0 + random.uniform(-1.5, 1.5)
        load_current = (load_demand * 1000.0) / load_voltage

        return {
            "timestamp": current_time,
            "hour": hour,
            "Solar_Power": round(solar_power, 2),
            "Solar_Voltage": round(solar_voltage, 2),
            "Solar_Current": round(solar_current, 2),
            "Solar_Temperature": round(solar_temperature, 2),
            "Wind_Power": round(wind_power, 2),
            "Wind_Speed": round(self.wind_speed, 2),
            "Wind_RPM": round(wind_rpm, 1),
            "Load_Demand": round(load_demand, 2),
            "Load_Voltage": round(load_voltage, 2),
            "Load_Current": round(load_current, 2),
            "ambient_temp": round(self.ambient_temp, 2),
            "cloud_cover": round(self.cloud_cover, 2)
        }

    def update_battery_physics(self, battery_power_dispatch: float, dt: float = 1.0 / 3600.0):
        """
        Simulates the chemistry / physics of the battery storage system based on the EMS charge/discharge command.
        battery_power_dispatch: positive value means charging BESS, negative means discharging.
        """
        if not self.battery_enabled:
            self.battery_current = 0.0
            return {
                "Battery_SOC": round(self.battery_soc, 2),
                "Battery_SOH": round(self.battery_soh, 4),
                "Battery_Voltage": round(self.battery_voltage, 2),
                "Battery_Current": 0.0,
                "Battery_Temperature": round(self.battery_temp, 2)
            }
        # Limit power to battery physical rating
        actual_power = battery_power_dispatch
        if actual_power > 0:
            actual_power = min(actual_power, self.BATTERY_MAX_CHARGE_KW)
            # Charging efficiency
            efficiency = 0.95
            self.battery_soc += (actual_power * efficiency * dt) / self.BATTERY_CAPACITY_KWH * 100.0
        else:
            actual_power = -min(-actual_power, self.BATTERY_MAX_DISCHARGE_KW)
            # Discharging efficiency
            efficiency = 1.0 / 0.95
            self.battery_soc += (actual_power * efficiency * dt) / self.BATTERY_CAPACITY_KWH * 100.0
            
        self.battery_soc = max(0.0, min(self.battery_soc, 100.0))
        
        # 1. BMS Battery Temperature update
        # Heat generation = I^2 * R. We can approximate heat generated using power.
        current_sq = (actual_power * 1000.0 / 400.0) ** 2 # approximate voltage as 400V
        heat_generated = 0.0005 * current_sq
        
        # Determine Cooling Fan Status early for physics computation
        if "FAN_FAILURE" in self.digital_twin_failures:
            self.battery_fan_status = "FAULTED"
        elif self.manual_fan_override is not None:
            self.battery_fan_status = self.manual_fan_override
        elif self.battery_temp >= 35.0:
            self.battery_fan_status = "ON"
        else:
            self.battery_fan_status = "OFF"
            
        # Heat dissipation to ambient (ventilation fans)
        if self.battery_fan_status == "FAULTED":
            fan_cooling_coefficient = 0.005 # drastically reduce cooling
        elif self.battery_fan_status == "ON":
            fan_cooling_coefficient = 0.05 # high active cooling
        else:
            fan_cooling_coefficient = 0.008 # low natural convection cooling when fan is off
            
        cooling = fan_cooling_coefficient * (self.battery_temp - self.ambient_temp)
        self.battery_temp += (heat_generated - cooling) * (dt * 3600.0) # scaling to seconds
        
        # Simulate Battery thermal runaway step
        if "BATTERY_RUNAWAY" in self.digital_twin_failures:
            self.battery_temp += 1.5 # rapid heating step per second
            
        # Extreme temperature check
        if self.battery_temp < -10:
            self.battery_temp = -10.0
        elif self.battery_temp > 65.0:
            self.battery_temp = 65.0 # Max temp clamp
            
        # 2. SOH Degradation: drops slightly with usage and extreme temperatures
        degradation = 0.000001 * abs(actual_power) * dt
        if self.battery_temp > 45.0:
            degradation *= 5.0 # Elevated temperature speeds up capacity fade
        self.battery_soh -= degradation
        self.battery_soh = max(30.0, min(self.battery_soh, 100.0))
        
        # 3. Dynamic Voltage
        # 400V nominal. Emulate cell-packing. Standard pack 96S (Lithium).
        # Voltage varies from 320V (depleted) to 415V (full).
        self.battery_voltage = 320.0 + 95.0 * (self.battery_soc / 100.0) + (actual_power * 0.15)
        self.battery_current = (actual_power * 1000.0) / self.battery_voltage if self.battery_voltage > 0 else 0.0

        return {
            "Battery_SOC": round(self.battery_soc, 2),
            "Battery_SOH": round(self.battery_soh, 4),
            "Battery_Voltage": round(self.battery_voltage, 2),
            "Battery_Current": round(self.battery_current, 2),
            "Battery_Temperature": round(self.battery_temp, 2),
            "Battery_Fan_Status": self.battery_fan_status
        }

    def get_grid_telemetry(self, grid_power_dispatch: float):
        """
        Generates grid voltage, frequency, and status.
        grid_power_dispatch: positive is imports from grid, negative is exports to grid.
        """
        if self.grid_status == 0 or not self.grid_enabled:
            return {
                "Grid_Status": 0,
                "Grid_Voltage": 0.0,
                "Grid_Frequency": 0.0,
                "Grid_Power": 0.0
            }
            
        # Grid connection fluctuations
        grid_voltage = self.NOMINAL_GRID_VOLTAGE + random.uniform(-3.0, 3.0)
        # Frequency deviation based on network load (random walk)
        grid_freq = self.NOMINAL_GRID_FREQ + random.uniform(-0.02, 0.02)
        
        if self.simulation_mode == "FAULT" and random.random() < 0.1:
            grid_voltage += 55.0 # Simulate transient overvoltage spike
            
        return {
            "Grid_Status": 1,
            "Grid_Voltage": round(grid_voltage, 2),
            "Grid_Frequency": round(grid_freq, 3),
            "Grid_Power": round(grid_power_dispatch, 2)
        }

    def get_inverter_telemetry(self, input_dc_power: float, output_ac_power: float):
        efficiency = 98.5
        if input_dc_power > 0:
            efficiency = (output_ac_power / input_dc_power) * 100.0
            efficiency = min(99.0, max(85.0, efficiency))
            
        inverter_status = "RUNNING"
        if self.fault_active:
            inverter_status = "FAULTED"
        elif output_ac_power == 0:
            inverter_status = "STANDBY"
            
        return {
            "Inverter_Status": inverter_status,
            "Inverter_Efficiency": round(efficiency, 2),
            "Inverter_Output_Power": round(output_ac_power, 2)
        }
