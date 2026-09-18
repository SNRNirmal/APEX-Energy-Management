# System Architecture & Technical Specifications

This document defines the system components, data schemas, protocol maps, and mathematical dispatch models of the APEX Hybrid Energy Management System (EMS) and SCADA platform.

---

## 1. System Structure & Communication Flow

The physical and data connections follow this microgrid topology:

```
[ Solar PV ]   --> ( MPPT Controller ) --------\
                                                +--> [ Hybrid Inverter / PCS ] <--> [ EMS Controller ]
[ Wind Gen ]   --> ( Wind Controller ) --------/            ^                        ^
                                                            |                        | (WebSockets/REST)
[ Battery ]    <================( CAN Bus )=================+                        v
                                                            |                 [ SCADA Dashboard ]
[ Utility Grid ] <============( Modbus TCP )================+                        v
                                                                                [ Microgrid Load ]
```

---

## 2. Power Dispatch & EMS Control Logic

### Rule-based Dispatch State Machine
Let $P_{\text{solar}}$ be Solar PV power, $P_{\text{wind}}$ be Wind power, and $P_{\text{load}}$ be Load demand.
The net renewable surplus is defined as:
$$P_{\text{surplus}} = P_{\text{solar}} + P_{\text{wind}} - P_{\text{load}}$$

The EMS resolves energy balance at 1-second intervals using four power flow dispatch modes:

1. **Renewable Priority Mode ($P_{\text{surplus}} \ge 0$, Battery SOC $< 100\%$):**
   * Supplying load demand entirely from PV and Wind.
   * Direct excess renewable generation to BESS:
     $$P_{\text{batt}} = \min(P_{\text{surplus}}, P_{\text{charge\_max}})$$
   * If surplus exceeds maximum charging capacity, export balance to grid (or curtail if grid export is disabled).

2. **Grid Export Mode ($P_{\text{surplus}} \ge 0$, Battery SOC $= 100\%$):**
   * Supplying load entirely from PV and Wind.
   * Export all excess renewable generation to Grid:
     $$P_{\text{grid}} = -P_{\text{surplus}}$$

3. **Battery Support Mode ($P_{\text{surplus}} < 0$, Battery SOC $> \text{SOC}_{\text{min}}$):**
   * Discharge battery storage to cover the deficit:
     $$P_{\text{batt}} = -\min(|P_{\text{surplus}}|, P_{\text{discharge\_max}})$$
   * Balance imported from utility grid:
     $$P_{\text{grid}} = |P_{\text{surplus}}| - |P_{\text{batt}}|$$

4. **Grid Fallback Mode ($P_{\text{surplus}} < 0$, Battery SOC $\le \text{SOC}_{\text{min}}$):**
   * Battery is disabled to protect chemistry health.
   * Grid imports balance energy to support loads:
     $$P_{\text{batt}} = 0$$
     $$P_{\text{grid}} = |P_{\text{surplus}}|$$

---

## 3. Database Schema

The database layer handles configurations, alarms, and high-frequency time-series telemetry.

### Relational Schema (PostgreSQL / SQLite) — `ems_settings`
Used to manage operational settings and pricing thresholds:
* `key` (TEXT PRIMARY KEY): Settings parameter identifier (e.g. `battery_min_soc`).
* `value` (TEXT): Settings parameter value (e.g. `20.0`).

### Time-Series Schema (InfluxDB / SQLite) — `scada_historian`
Logs tag readings every second for historical analysis:
* `timestamp` (REAL PRIMARY KEY): Unix epoch timestamp.
* `solar_power` / `wind_power` / `load_demand` / `grid_power` (REAL): Active powers in kW.
* `battery_soc` / `battery_soh` (REAL): BESS percentage health metrics.
* `battery_voltage` / `battery_current` / `battery_temperature` (REAL): Physical battery state tags.
* `grid_status` (INTEGER): Grid health (0 = Outage, 1 = Normal).
* `ems_action` (TEXT): Optimization dispatch tag description.
* `electricity_cost` (REAL): Cumulative electricity charge in dollars.

### Document/Event Schema (MongoDB / SQLite) — `alarms_log`
Registers alarms and system anomalies:
* `id` (INTEGER PRIMARY KEY AUTOINCREMENT): Alarm record identifier.
* `timestamp` (REAL): Unix epoch timestamp.
* `severity` (TEXT): Alarms hazard level (`INFO`, `WARNING`, `CRITICAL`).
* `source` (TEXT): Device origin (`BMS`, `Inverter`, `Grid`, `EMS`, `Load`).
* `message` (TEXT): Descriptive alert text.
* `status` (TEXT): Operational status (`ACTIVE`, `ACKNOWLEDGED`, `CLEARED`).

---

## 4. Communication Protocol Maps

APEX simulates industrial protocols by mapping telemetry to registers, nodes, and byte-frames:

### Modbus TCP (Holding Registers)
Exposed by the Hybrid Inverter controller (Port 8000 REST/WebSockets representation):
* `40001`: Solar PV generation power (kW $\times$ 10).
* `40002`: Wind turbine power (kW $\times$ 10).
* `40003`: Battery State of Charge (SOC $\%$ $\times$ 100).
* `40004`: Inverter output power (Signed integer, kW $\times$ 10 with 32768 offset).
* `40005`: Grid export command registry (0 = Disabled, 1 = Enabled).
* `40006`: Battery minimum SOC backup setting ($\%$).

### CAN Bus (BMS Telemetry)
The BMS controller emits raw telemetry frames onto the internal vehicle/battery CAN network:
* **Arbitration ID:** `0x18F009A1` (High-priority BMS Frame)
* **DLC:** 8 Bytes
* **Byte 0:** Battery SOC (0-100%).
* **Byte 1-2:** Battery Voltage ($V \times 10$ represented in 16-bit unsigned big-endian).
* **Byte 3-4:** Battery Current ($A \times 10$ with 32768 offset to support bidirectional signed measurements).
* **Byte 5:** Battery cell temperature ($^{\circ}\text{C} + 40$ offset).
* **Byte 6:** Heartbeat index counter.
* **Byte 7:** CRC Checksum of bytes 0-6.

### OPC UA
Exposes hierarchical node structure:
* `ns=2;s=Microgrid.Solar.Voltage` (Solar DC Volts)
* `ns=2;s=Microgrid.Solar.Current` (Solar DC Amps)
* `ns=2;s=Microgrid.Wind.Speed` (Wind Velocity in m/s)
* `ns=2;s=Microgrid.BESS.SOH` (Battery State of Health $\%$)
* `ns=2;s=Microgrid.Load.Demand` (Active Load Demand in kW)
* `ns=2;s=Microgrid.Grid.Frequency` (Grid Line Frequency in Hz)

### IEC 61850
Logical node mapping for utility grid substation monitoring:
* `Grid_XCBR1.Pos.stVal`: Breaker status (1 = Closed, 2 = Open).
* `Grid_XCBR1.Pos.q`: Measurement quality (Good, Bad, Questionable).
* `Inverter_MMXU1.TotW.mag.f`: Inverter active power magnitude.
* `Inverter_MMXU1.TotV.mag.f`: Grid line voltage magnitude.
* `Inverter_MMXU1.TotHz.mag.f`: Utility grid network frequency.

---

## 5. AI/ML Forecasting & Optimization Core

### Forecasting Pipeline
1. **Solar PV Forecasting**: Uses a polynomial regression model that receives weather metadata (ambient temperature, solar zenith angle, and cloud cover forecast) to predict PV hourly capacity factor.
2. **Load Demand Forecasting**: Evaluates historical time-series data using a recurrent auto-regressive model. It projects load profiles for the next 24 hours based on hour of day, day of week (weekday vs. weekend), and rolling average load.

### Reinforcement Learning Optimizer
The AI optimization mode uses **Q-Learning** to schedule BESS actions based on Time-of-Use (ToU) tariffs:
* **State Space ($S$):** $(h_{\text{bin}}, s_{\text{bin}}, p_{\text{surplus\_bin}})$
  * $h_{\text{bin}}$: Hour of day grouped in 4-hour intervals (0 to 5).
  * $s_{\text{bin}}$: Battery SOC grouped in 20% intervals (0 to 4).
  * $p_{\text{surplus\_bin}}$: Renewable surplus grouped into negative, zero, and positive categories (0 to 2).
* **Actions ($A$):** $[-20\text{ kW}, 0\text{ kW}, +20\text{ kW}]$ (Discharge, Standby, Charge).
* **Reward ($R$):**
  $$R = -(\text{Electricity Cost}) - \alpha \times |P_{\text{batt}}|$$
  where $\alpha$ is a degradation penalty coefficient penalizing heavy battery cycling.
* **Q-value Update Formula**:
  $$Q(s, a) \leftarrow Q(s, a) + \gamma \left[ R + \lambda \max_{a'} Q(s', a') - Q(s, a) \right]$$
  where $\gamma$ is the learning rate, and $\lambda$ is the discount factor.
