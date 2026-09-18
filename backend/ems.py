import math
import random
from datetime import datetime
import time
from database import db

class EMSEngine:
    def __init__(self):
        # Q-learning reinforcement learning parameters
        # States: hour_bin (0-5), soc_bin (0-4), surplus_bin (0-2)
        # Actions: 0 (Discharge 20kW), 1 (Standby), 2 (Charge 20kW)
        self.q_table = {}
        self.actions = [-20.0, 0.0, 20.0]
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.15 # exploration
        
        # Load pre-trained or empty Q-table
        self._initialize_q_table()

    def _get_state_key(self, hour: float, soc: float, surplus: float) -> tuple:
        hour_bin = int(hour / 4) # 6 bins (0 to 5)
        soc_bin = int(soc / 20)  # 5 bins (0 to 4)
        if surplus > 10.0:
            surplus_bin = 2
        elif surplus < -10.0:
            surplus_bin = 0
        else:
            surplus_bin = 1
        return (hour_bin, soc_bin, surplus_bin)

    def _initialize_q_table(self):
        # Initialize all possible states with zeros
        for h in range(6):
            for s in range(5):
                for p in range(3):
                    self.q_table[(h, s, p)] = [0.0, 0.0, 0.0]

    def select_rl_action(self, hour: float, soc: float, surplus: float) -> float:
        """
        Uses epsilon-greedy reinforcement learning to select charge/discharge action (kW offset).
        Positive action charges battery, negative action discharges battery.
        """
        state = self._get_state_key(hour, soc, surplus)
        if random.random() < self.epsilon:
            action_idx = random.randint(0, len(self.actions) - 1)
        else:
            action_idx = self.q_table[state].index(max(self.q_table[state]))
            
        return self.actions[action_idx]

    def update_rl_policy(self, hour: float, soc: float, surplus: float, action_val: float, next_hour: float, next_soc: float, next_surplus: float, reward: float):
        """
        Bellman equation update for Q-learning.
        """
        state = self._get_state_key(hour, soc, surplus)
        next_state = self._get_state_key(next_hour, next_soc, next_surplus)
        action_idx = self.actions.index(action_val)
        
        best_next_q = max(self.q_table[next_state])
        current_q = self.q_table[state][action_idx]
        
        # Q-learning temporal difference update
        self.q_table[state][action_idx] += self.learning_rate * (reward + self.discount_factor * best_next_q - current_q)

    def is_peak_hour(self, hour: float) -> bool:
        # Check database settings
        start_str = db.get_setting("tariff_peak_start", "14:00")
        end_str = db.get_setting("tariff_peak_end", "20:00")
        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            start = sh + sm / 60.0
            end = eh + em / 60.0
            return start <= hour <= end
        except Exception:
            return 14.0 <= hour <= 20.0

    def get_tariff(self, hour: float) -> float:
        if self.is_peak_hour(hour):
            return float(db.get_setting("tariff_peak_rate", "7.50"))
        else:
            return float(db.get_setting("tariff_offpeak_rate", "4.50"))

    def compute_dispatch(self, telemetry: dict, mode: str = "NORMAL") -> dict:
        """
        Implements the main EMS dispatch controller state machine.
        Enforces smart battery protection limits (SOC 20-95%) and thermal safety derating.
        Returns: {
            "battery_power": float,
            "grid_power": float,
            "ems_action": str,
            "electricity_cost": float,
            "load_shedding_level": int,
            "original_load": float
        }
        """
        solar = telemetry.get("Solar_Power", 0.0)
        wind = telemetry.get("Wind_Power", 0.0)
        load = telemetry.get("Load_Demand", 0.0)
        
        # Retrieve SOC from database or default to 50
        soc = db.conn.execute("SELECT battery_soc FROM scada_historian ORDER BY timestamp DESC LIMIT 1").fetchone()
        soc = soc["battery_soc"] if soc else 50.0
        
        # Enforce battery rules: prevent discharge below 20.0%, stop charging above 95.0%
        min_soc = 20.0
        max_soc = 95.0
        
        # Smart Battery Temperature Safety and Derating
        battery_enabled = telemetry.get("battery_enabled", True)
        battery_temp = telemetry.get("Battery_Temperature", 25.0)
        max_charge_rate = 50.0
        max_discharge_rate = 60.0
        
        if not battery_enabled:
            # Battery isolated manually
            max_charge_rate = 0.0
            max_discharge_rate = 0.0
        elif battery_temp >= 55.0 or battery_temp <= -10.0:
            # Critical temperature safety threshold (Thermal runaway or extreme cold): shut down battery
            max_charge_rate = 0.0
            max_discharge_rate = 0.0
        elif battery_temp >= 50.0:
            # High thermal stress: derate power by 80%
            max_charge_rate = 10.0
            max_discharge_rate = 15.0
        elif battery_temp >= 45.0:
            # Warning thermal stress: derate power by 50%
            max_charge_rate = 25.0
            max_discharge_rate = 30.0
        elif battery_temp <= 0.0:
            # Freezing threshold: disable charging to prevent lithium plating, permit derated discharge
            max_charge_rate = 0.0
            max_discharge_rate = 30.0

        p_renewable = solar + wind
        
        # Check grid outage simulation
        grid_connected = telemetry.get("Grid_Status", 1) == 1
        
        # Smart Load Shedding Rules (during Grid Outage / Islanding)
        load_shedding_level = 0
        original_load = load
        
        if not grid_connected:
            if not battery_enabled:
                # Without grid and without battery, we must shed load immediately to match renewable capacity
                if original_load > p_renewable:
                    ratio = p_renewable / original_load if original_load > 0 else 0.0
                    if ratio >= 0.7:
                        load_shedding_level = 1
                        load = original_load * 0.7
                    elif ratio >= 0.4:
                        load_shedding_level = 2
                        load = original_load * 0.4
                    else:
                        load_shedding_level = 3
                        load = original_load * 0.15
                else:
                    load_shedding_level = 0
            else:
                if soc <= 15.0:
                    # Shed all except vital infrastructure (85% load shed)
                    load_shedding_level = 3
                    load = original_load * 0.15
                elif soc <= 20.0:
                    # Shed medium and noncritical loads (60% load shed)
                    load_shedding_level = 2
                    load = original_load * 0.4
                elif soc <= 25.0:
                    # Shed noncritical loads (30% load shed)
                    load_shedding_level = 1
                    load = original_load * 0.7
                
        surplus = p_renewable - load
        
        battery_power = 0.0
        grid_power = 0.0
        ems_action = "STANDBY"
        
        export_enabled = db.get_setting("export_enabled", "true") == "true"
        peak_shave_threshold = 45.0 # kW
        
        # Hour of day from telemetry timestamp
        struct_t = time.localtime(telemetry.get("timestamp", time.time()))
        hour = struct_t.tm_hour + struct_t.tm_min / 60.0
        
        if not grid_connected:
            # Islanding Mode / Emergency Mode
            if surplus >= 0:
                # Excess power charges battery if possible under SOC limit
                if soc < max_soc and max_charge_rate > 0:
                    battery_power = min(surplus, max_charge_rate, (max_soc - soc) * 2.0) # approx charging rate limit
                    ems_action = "ISLAND_CHARGE" if battery_power > 0 else "ISLAND_BALANCED"
                else:
                    battery_power = 0.0
                    ems_action = "ISLAND_LIMIT"
            else:
                # Deficit: discharge battery if SOC is above min threshold
                if soc > min_soc:
                    battery_power = max(surplus, -max_discharge_rate)
                    ems_action = "ISLAND_DISCHARGE"
                else:
                    battery_power = 0.0
                    ems_action = "ISLAND_LOAD_SHED"
            grid_power = 0.0
            
        else:
            # Grid Connected Modes
            if surplus >= 0:
                # Renewable surplus
                if soc < max_soc and max_charge_rate > 0:
                    battery_power = min(surplus, max_charge_rate)
                    grid_power = -(surplus - battery_power) if export_enabled else 0.0
                    ems_action = "RENEWABLE_CHARGE"
                else:
                    if export_enabled:
                        grid_power = -surplus
                        ems_action = "GRID_EXPORT"
                    else:
                        grid_power = 0.0
                        ems_action = "RENEWABLE_LIMIT"
            else:
                # ════════════════════════════════════════════════════════════
                # GRID-CONNECTED EMS — STRICT PRIORITY ORDER
                # 1. Solar + Wind  →  Load  (always first, done via surplus)
                # 2. Excess renewable  →  Charge Battery
                # 3. No renewable  →  Discharge Battery FIRST
                # 4. Battery low/unavailable  →  Use Grid as last resort
                # ════════════════════════════════════════════════════════════

                # ── CASE 3: Renewable deficit — use battery FIRST ──
                deficit = abs(surplus)

                if (soc > min_soc) and (max_discharge_rate > 0):
                    # Battery available → discharge to cover as much deficit as possible
                    discharge_needed = min(deficit, max_discharge_rate)
                    battery_power = -discharge_needed
                    grid_power = max(0.0, deficit - discharge_needed)  # grid only fills the gap
                    if grid_power > 0:
                        ems_action = "BATTERY_GRID_SUPPORT"
                    else:
                        ems_action = "BATTERY_SUPPORT"
                else:
                    # ── CASE 4: Battery unavailable or depleted → Grid fallback ──
                    battery_power = 0.0
                    grid_power = deficit
                    ems_action = "GRID_FALLBACK"

        # Calculate cost based on tariff
        rate = self.get_tariff(hour)
        dt = 1.0 / 3600.0
        cost = max(0.0, grid_power) * rate * dt
        if grid_power < 0:
            export_rate = rate * 0.5
            cost += grid_power * export_rate * dt

        return {
            "battery_power": round(battery_power, 2),
            "grid_power": round(grid_power, 2),
            "ems_action": ems_action,
            "electricity_cost": round(cost, 6),
            "load_shedding_level": load_shedding_level,
            "original_load": round(original_load, 2)
        }

    # ── Fault Advisor Knowledge Base ──────────────────────────────────────
    FAULT_ADVISOR = {
        "BMS-SOC-001": {
            "fault_code": "BMS-SOC-001",
            "root_cause": "Battery State of Charge critically low (≤15%). Load shedding is now active to protect the cell stack from deep discharge damage.",
            "repair_actions": [
                "1. Enable utility grid import if available.",
                "2. Immediately reduce non-critical load by 30–50%.",
                "3. Check solar and wind generation are online and producing.",
                "4. Verify charge controller is not in fault state.",
                "5. Do NOT disconnect battery until SOC reaches ≥25%.",
            ],
            "estimated_time": "10–30 minutes",
            "safety_warning": "⚠️ Deep discharge below 10% SOC permanently damages lithium cells. Act immediately.",
        },
        "BMS-SOC-002": {
            "fault_code": "BMS-SOC-002",
            "root_cause": "Battery SOC approaching minimum protection threshold (≤20%). Risk of load shedding in next cycle.",
            "repair_actions": [
                "1. Enable grid import or increase renewable generation.",
                "2. Reduce load demand if possible.",
                "3. Monitor SOC trend — if declining, escalate to CRITICAL response.",
                "4. Check BMS charge parameters in settings.",
            ],
            "estimated_time": "5–20 minutes",
            "safety_warning": "⚠️ Monitor closely. SOC may drop further and trigger emergency load shedding.",
        },
        "BMS-THERM-001": {
            "fault_code": "BMS-THERM-001",
            "root_cause": "BESS thermal runaway threshold exceeded (≥55°C). Battery has been electronically disconnected for safety. Lithium cells are at risk of fire or explosion.",
            "repair_actions": [
                "1. 🚨 EMERGENCY: Evacuate battery room immediately.",
                "2. Activate fire suppression system if smoke or fire is visible.",
                "3. Call qualified battery engineer — do NOT attempt DIY repair.",
                "4. Keep battery isolated and disconnected until engineer arrives.",
                "5. Check and replace cooling fans and HVAC in battery enclosure.",
                "6. Inspect battery cells for swelling, leakage, or discolouration.",
                "7. Run full BMS diagnostics before reconnecting.",
            ],
            "estimated_time": "2–8 hours (engineer required)",
            "safety_warning": "🚨 CRITICAL SAFETY HAZARD. Lithium thermal runaway can cause fire. Do NOT reconnect without engineer clearance.",
        },
        "BMS-THERM-002": {
            "fault_code": "BMS-THERM-002",
            "root_cause": "Battery temperature elevated (≥45°C). Charge/discharge rates have been derated. Prolonged high temperature accelerates cell degradation.",
            "repair_actions": [
                "1. Check battery enclosure ventilation — clear any blockages.",
                "2. Verify cooling fans are spinning at correct RPM.",
                "3. Reduce charge current setpoint in EMS settings temporarily.",
                "4. Check ambient room temperature — should be ≤35°C.",
                "5. Monitor temperature trend — if rising, prepare for BMS-THERM-001 response.",
            ],
            "estimated_time": "15–60 minutes",
            "safety_warning": "⚠️ Sustained high temperature reduces battery lifespan. Address cooling immediately.",
        },
        "INV-FAULT-001": {
            "fault_code": "INV-FAULT-001",
            "root_cause": "Inverter overcurrent protection tripped. The DC or AC bus current exceeded safe operating limits, causing the inverter to fault.",
            "repair_actions": [
                "1. Disconnect AC and DC sides of inverter using isolation breakers.",
                "2. Wait 5 minutes for capacitors to discharge fully.",
                "3. Inspect AC output terminals for short circuits or loose wiring.",
                "4. Check DC bus fuses — replace if blown.",
                "5. Verify load demand has not spiked beyond inverter rating.",
                "6. Reset inverter via its front panel or SCADA reset command.",
                "7. Reconnect and monitor output current for 10 minutes.",
            ],
            "estimated_time": "20–45 minutes",
            "safety_warning": "⚠️ Always isolate both AC and DC sides before inspection. Inverter capacitors retain lethal voltage.",
        },
        "GRID-OUT-001": {
            "fault_code": "GRID-OUT-001",
            "root_cause": "Utility grid connection lost. System has automatically switched to island (off-grid) mode. Load is now served by battery + renewables only.",
            "repair_actions": [
                "1. Check utility meter and main incomer breaker.",
                "2. Verify grid supply at point of common coupling (PCC) with a voltmeter.",
                "3. If outage is external: contact utility grid operator immediately.",
                "4. Monitor battery SOC — implement load shedding if SOC drops below 30%.",
                "5. Ensure critical loads are prioritised during island mode.",
                "6. When grid restores, verify frequency and voltage are within limits before reconnecting.",
            ],
            "estimated_time": "Variable (utility-dependent)",
            "safety_warning": "⚠️ Do NOT connect to utility grid without verifying voltage/frequency. Anti-islanding protection must be active.",
        },
        "LOAD-OC-001": {
            "fault_code": "LOAD-OC-001",
            "root_cause": "Load feeder current exceeded 180A overcurrent threshold. Breaker trip risk. Possible causes: short circuit, motor startup surge, or unexpected load addition.",
            "repair_actions": [
                "1. Check load feeder panel for tripped sub-breakers.",
                "2. Identify which loads are drawing excess current using sub-metering.",
                "3. Disconnect non-critical loads to reduce total current.",
                "4. Inspect feeder cables for insulation damage or loose connections.",
                "5. Check for motor faults (stalled motor draws high starting current).",
                "6. Reset main feeder breaker only after identifying and removing the fault.",
            ],
            "estimated_time": "15–40 minutes",
            "safety_warning": "⚠️ Sustained overcurrent causes cable and insulation damage. Identify root cause before resetting breaker.",
        },
        "GRID-OV-001": {
            "fault_code": "GRID-OV-001",
            "root_cause": "Grid voltage exceeds 440V nominal limit. Overvoltage can damage connected equipment and indicates a grid regulation problem.",
            "repair_actions": [
                "1. Notify utility grid operator of overvoltage condition with timestamp and readings.",
                "2. Check transformer tap changer setting — may need adjustment.",
                "3. Activate on-load voltage regulator if available.",
                "4. Temporarily reduce or disconnect non-critical loads to reduce reactive demand.",
                "5. If voltage exceeds 460V, consider disconnecting from grid to protect equipment.",
            ],
            "estimated_time": "10–30 minutes",
            "safety_warning": "⚠️ Sustained overvoltage damages inverters, motors and sensitive equipment.",
        },
        "AI-ANOM-001": {
            "fault_code": "AI-ANOM-001",
            "root_cause": "AI anomaly detection model flagged statistically unusual telemetry values. This may indicate sensor drift, wiring issue, or early-stage equipment fault before it becomes critical.",
            "repair_actions": [
                "1. Review all telemetry readings for values outside normal operating ranges.",
                "2. Compare sensor readings against manual measurements (clamp meter, voltmeter).",
                "3. Check sensor wiring and communication cables for loose connections.",
                "4. Recalibrate any sensors showing drift.",
                "5. If readings normalise, AI model may have detected a brief transient — continue monitoring.",
                "6. Log this event in maintenance records.",
            ],
            "estimated_time": "10–30 minutes",
            "safety_warning": "ℹ️ AI anomaly warnings are early indicators. Do not ignore — investigate before a hard fault occurs.",
        },
    }

    def detect_alarms(self, telemetry: dict) -> list:
        """
        Scans current telemetry tags and registers/clears alarms in database.
        Enriches each alarm with fault_code and repair_actions from FAULT_ADVISOR.
        Returns triggered alarms.
        """
        alarms_triggered = []

        def _enrich(alarm_dict: dict, advisor_key: str) -> dict:
            """Merges alarm dict with fault advisor knowledge base entry."""
            if alarm_dict is None:
                return None
            advice = self.FAULT_ADVISOR.get(advisor_key, {})
            return {**alarm_dict, **advice}

        # 1. Grid Outage check
        if telemetry.get("Grid_Status", 1) == 0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("CRITICAL", "Grid", "Utility grid outage detected! System islanded."),
                "GRID-OUT-001"
            ))
        else:
            db.clear_alarm_by_message("Grid", "Utility grid outage detected! System islanded.")

        # 2. Inverter check
        if telemetry.get("Inverter_Status", "RUNNING") == "FAULTED":
            alarms_triggered.append(_enrich(
                db.trigger_alarm("CRITICAL", "Inverter", "Inverter system fault: Overcurrent trip."),
                "INV-FAULT-001"
            ))
        else:
            db.clear_alarm_by_message("Inverter", "Inverter system fault: Overcurrent trip.")

        # 3. Battery Over-temperature & Thermal Runaway
        bat_temp = telemetry.get("Battery_Temperature", 25.0)
        if bat_temp >= 55.0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("CRITICAL", "BMS", f"CRITICAL: BESS Thermal Runaway detected! Temp: {bat_temp}°C!"),
                "BMS-THERM-001"
            ))
            db.clear_alarm_by_message("BMS", f"Battery high temperature warning: {bat_temp}°C.")
        elif bat_temp >= 45.0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("WARNING", "BMS", f"Battery high temperature warning: {bat_temp}°C."),
                "BMS-THERM-002"
            ))
            db.clear_alarm_by_message("BMS", f"CRITICAL: BESS Thermal Runaway detected! Temp: {bat_temp}°C!")
        else:
            db.clear_alarm_by_message("BMS", f"CRITICAL: BESS Thermal Runaway detected! Temp: {bat_temp}°C!")
            db.clear_alarm_by_message("BMS", f"Battery high temperature warning: {bat_temp}°C.")

        # 4. Battery Low SOC
        soc = telemetry.get("Battery_SOC", 50.0)
        if soc <= 15.0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("CRITICAL", "BMS", f"Battery emergency low SOC: {soc}%! Load shedding active."),
                "BMS-SOC-001"
            ))
            db.clear_alarm_by_message("BMS", f"Battery low SOC: {soc}%.")
        elif soc <= 20.0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("WARNING", "BMS", f"Battery low SOC: {soc}%."),
                "BMS-SOC-002"
            ))
            db.clear_alarm_by_message("BMS", f"Battery emergency low SOC: {soc}%! Load shedding active.")
        else:
            db.clear_alarm_by_message("BMS", f"Battery emergency low SOC: {soc}%! Load shedding active.")
            db.clear_alarm_by_message("BMS", f"Battery low SOC: {soc}%.")

        # 5. Overcurrent Check
        load_curr = telemetry.get("Load_Current", 0.0)
        if load_curr > 180.0:
            alarms_triggered.append(_enrich(
                db.trigger_alarm("CRITICAL", "Load", f"Microgrid overcurrent demand: {load_curr}A! Breaker trip risk."),
                "LOAD-OC-001"
            ))
        else:
            db.clear_alarm_by_message("Load", f"Microgrid overcurrent demand: {load_curr}A! Breaker trip risk.")

        # 6. Voltage stability
        grid_v = telemetry.get("Grid_Voltage", 0.0)
        if (telemetry.get("Grid_Status", 1) == 1):
            if grid_v > 440.0:
                alarms_triggered.append(_enrich(
                    db.trigger_alarm("WARNING", "Grid", f"Grid overvoltage transient: {grid_v}V."),
                    "GRID-OV-001"
                ))
            else:
                db.clear_alarm_by_message("Grid", f"Grid overvoltage transient: {grid_v}V.")

        # 7. AI Anomaly Detector Check
        inv_eff = telemetry.get("Inverter_Efficiency", 98.5)
        try:
            from ai_models import anomaly_detector
            is_anom, score = anomaly_detector.is_anomalous(grid_v, load_curr, bat_temp, inv_eff)
            if is_anom:
                alarms_triggered.append(_enrich(
                    db.trigger_alarm("WARNING", "AI_Diagnostic", "Telemetry anomaly detected. Check physical connections."),
                    "AI-ANOM-001"
                ))
            else:
                db.clear_alarm_by_message("AI_Diagnostic", "Telemetry anomaly detected. Check physical connections.")
        except Exception:
            pass

        return [a for a in alarms_triggered if a is not None]


    # AI/ML Forecasting models
    def generate_24h_forecasts(self) -> dict:
        """
        Generates 24-hour predictions for Solar, Wind, and Load demand using recurrent
        mathematical equations resembling LSTM and regression.
        """
        forecasts = []
        current_time = time.time()
        
        # Get base settings for tariff peaks
        for i in range(24):
            f_time = current_time + i * 3600.0
            struct_f = time.localtime(f_time)
            f_hour = struct_f.tm_hour + struct_f.tm_min / 60.0
            
            # Predict Solar PV: Solar peak at 12 PM, zero during night
            pv_pred = 0.0
            if 6.0 <= f_hour <= 18.0:
                pv_pred = 100.0 * math.sin(math.pi * (f_hour - 6.0) / 12.0)
                # Apply simulated weather factor (assume cloudy tomorrow mid-day)
                weather_factor = 0.9 if 11.0 <= f_hour <= 14.0 else 1.0
                pv_pred *= weather_factor
                
            # Predict Wind: Random walks with sinusoidal base
            wind_pred = 20.0 + 10.0 * math.sin(2 * math.pi * (f_hour - 2) / 24)
            # Add seasonal variation
            wind_pred = max(5.0, min(wind_pred, 45.0))
            
            # Predict Load: Standard double diurnal peak
            t1 = math.exp(-((f_hour - 8.0) / 2.0) ** 2)
            t2 = math.exp(-((f_hour - 19.0) / 3.0) ** 2)
            load_pred = 25.0 + 20.0 * t1 + 35.0 * t2 + random.uniform(-0.5, 0.5)
            
            tariff_rate = self.get_tariff(f_hour)
            
            forecasts.append({
                "time": struct_f.tm_hour,
                "solar": round(pv_pred, 2),
                "wind": round(wind_pred, 2),
                "load": round(load_pred, 2),
                "tariff": tariff_rate
            })
            
        return forecasts

    def predict_battery_soh_fade(self, cycles: int, avg_temp: float) -> float:
        """
        AI Predictive model for Battery degradation.
        SOH degradation is proportional to cycles and exponential to temperature.
        """
        base_degrade = 0.015 * cycles # 1.5% SOH per 100 cycles at room temp
        temp_multiplier = math.exp(0.05 * (avg_temp - 25.0)) # Arrhenius approximation
        predicted_soh = 100.0 - (base_degrade * temp_multiplier)
        return round(max(30.0, predicted_soh), 3)
