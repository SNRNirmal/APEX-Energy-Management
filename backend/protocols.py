import json
import random
import time

class ModbusTCPSimulator:
    """
    Simulates a Modbus TCP server register mapping.
    Holding Registers (16-bit unsigned integers):
    - 40001: Solar Power (kW * 10)
    - 40002: Wind Power (kW * 10)
    - 40003: Battery SOC (% * 100)
    - 40004: Inverter Power (kW * 10, signed with 32768 offset)
    - 40005: Grid Export Command (0 = Disable, 1 = Enable)
    - 40006: Battery Min SOC Setting (%)
    - 40007: Battery Temperature (C * 10, offset by +50C to prevent negatives, so value = (T + 50) * 10)
    - 40008: Load Shedding Level (0 = None, 1 = Light, 2 = Medium, 3 = Critical)
    - 40009: Active Alarm Count
    - 40010: Inverter Efficiency (% * 100)
    """
    def __init__(self):
        self.registers = {
            40001: 0,
            40002: 0,
            40003: 5000,
            40004: 32768, # 0 kW
            40005: 1,
            40006: 20,
            40007: 750,  # 25C -> (25 + 50) * 10
            40008: 0,
            40009: 0,
            40010: 9850  # 98.5%
        }

    def update_registers(self, telemetry: dict, settings: dict):
        self.registers[40001] = int(telemetry.get("Solar_Power", 0) * 10)
        self.registers[40002] = int(telemetry.get("Wind_Power", 0) * 10)
        self.registers[40003] = int(telemetry.get("Battery_SOC", 50) * 100)
        
        inv_pow = telemetry.get("Inverter_Output_Power", 0)
        self.registers[40004] = int(inv_pow * 10) + 32768
        
        self.registers[40005] = 1 if settings.get("export_enabled") == "true" else 0
        self.registers[40006] = int(float(settings.get("battery_min_soc", 20.0)))
        
        # New registers
        temp = telemetry.get("Battery_Temperature", 25.0)
        self.registers[40007] = int((temp + 50.0) * 10)
        self.registers[40008] = int(telemetry.get("load_shedding_level", 0))
        self.registers[40009] = int(telemetry.get("alarm_count", 0))
        self.registers[40010] = int(telemetry.get("Inverter_Efficiency", 98.5) * 100)

    def write_register(self, address: int, value: int) -> bool:
        if address in [40005, 40006]:
            self.registers[address] = value
            return True
        return False # Read-Only

    def read_registers(self, start_address: int, count: int) -> dict:
        result = {}
        for addr in range(start_address, start_address + count):
            if addr in self.registers:
                result[addr] = self.registers[addr]
        return result


class OPCUASimulator:
    """
    Simulates an OPC UA address space with Nodes.
    """
    def __init__(self):
        self.nodes = {
            "ns=2;s=Microgrid.Solar.Voltage": 0.0,
            "ns=2;s=Microgrid.Solar.Current": 0.0,
            "ns=2;s=Microgrid.Wind.Speed": 0.0,
            "ns=2;s=Microgrid.BESS.SOH": 100.0,
            "ns=2;s=Microgrid.Load.Demand": 0.0,
            "ns=2;s=Microgrid.Grid.Frequency": 50.0,
            "ns=2;s=Microgrid.BESS.Temperature": 25.0,
            "ns=2;s=Microgrid.Inverter.Efficiency": 98.5,
            "ns=2;s=Microgrid.EMS.LoadSheddingLevel": 0.0,
            "ns=2;s=Microgrid.EMS.AlarmCount": 0.0
        }

    def update_nodes(self, telemetry: dict):
        self.nodes["ns=2;s=Microgrid.Solar.Voltage"] = telemetry.get("Solar_Voltage", 0.0)
        self.nodes["ns=2;s=Microgrid.Solar.Current"] = telemetry.get("Solar_Current", 0.0)
        self.nodes["ns=2;s=Microgrid.Wind.Speed"] = telemetry.get("Wind_Speed", 0.0)
        self.nodes["ns=2;s=Microgrid.BESS.SOH"] = telemetry.get("Battery_SOH", 100.0)
        self.nodes["ns=2;s=Microgrid.Load.Demand"] = telemetry.get("Load_Demand", 0.0)
        self.nodes["ns=2;s=Microgrid.Grid.Frequency"] = telemetry.get("Grid_Frequency", 50.0)
        self.nodes["ns=2;s=Microgrid.BESS.Temperature"] = telemetry.get("Battery_Temperature", 25.0)
        self.nodes["ns=2;s=Microgrid.Inverter.Efficiency"] = telemetry.get("Inverter_Efficiency", 98.5)
        self.nodes["ns=2;s=Microgrid.EMS.LoadSheddingLevel"] = float(telemetry.get("load_shedding_level", 0))
        self.nodes["ns=2;s=Microgrid.EMS.AlarmCount"] = float(telemetry.get("alarm_count", 0))

    def read_node(self, node_id: str) -> float:
        return self.nodes.get(node_id, 0.0)


class CANBusSimulator:
    """
    Simulates Battery Management System (BMS) communications over CAN Bus.
    Converts telemetry into simulated hex CAN frames.
    """
    def __init__(self):
        pass

    def encode_bms_frame(self, soc: float, voltage: float, current: float, temp: float) -> str:
        """
        Encodes BMS variables into an 8-byte CAN frame.
        ID: 0x18F009A1
        Byte 0: SOC (%)
        Byte 1-2: Voltage (V * 10)
        Byte 3-4: Current (A * 10 + 32768 offset)
        Byte 5: Temp (C + 40 offset)
        Byte 6-7: Checksum/Heartbeat
        """
        b_soc = int(soc) & 0xFF
        b_volt = int(voltage * 10) & 0xFFFF
        b_curr = int(current * 10 + 32768) & 0xFFFF
        b_temp = int(temp + 40) & 0xFF
        
        v_h = (b_volt >> 8) & 0xFF
        v_l = b_volt & 0xFF
        c_h = (b_curr >> 8) & 0xFF
        c_l = b_curr & 0xFF
        
        heartbeat = int(time.time()) & 0xFF
        checksum = (b_soc + v_h + v_l + c_h + c_l + b_temp + heartbeat) & 0xFF
        
        frame = f"ID: 0x18F009A1 | DLC: 8 | DATA: {b_soc:02X} {v_h:02X} {v_l:02X} {c_h:02X} {c_l:02X} {b_temp:02X} {heartbeat:02X} {checksum:02X}"
        return frame


class IEC61850Simulator:
    """
    Simulates IEC 61850 Logical Nodes for Substation Automation.
    Logical Nodes:
    - XCBR1: Circuit Breaker Status
    - MMXU1: 3-Phase Measurement
    """
    def __init__(self):
        self.logical_nodes = {
            "Grid_XCBR1.Pos.stVal": 1, # 1 = Closed, 2 = Open
            "Grid_XCBR1.Pos.q": "Good",
            "Inverter_MMXU1.TotW.mag.f": 0.0,
            "Inverter_MMXU1.TotV.mag.f": 400.0,
            "Inverter_MMXU1.TotHz.mag.f": 50.0
        }

    def update_nodes(self, telemetry: dict):
        # Map Grid Status to circuit breaker position
        # Grid Status = 1 (connected) -> breaker closed (1). Grid Status = 0 (outage) -> breaker open (2).
        self.logical_nodes["Grid_XCBR1.Pos.stVal"] = 1 if telemetry.get("Grid_Status", 1) == 1 else 2
        self.logical_nodes["Inverter_MMXU1.TotW.mag.f"] = telemetry.get("Inverter_Output_Power", 0.0)
        self.logical_nodes["Inverter_MMXU1.TotV.mag.f"] = telemetry.get("Grid_Voltage", 400.0)
        self.logical_nodes["Inverter_MMXU1.TotHz.mag.f"] = telemetry.get("Grid_Frequency", 50.0)

    def get_ln_values(self) -> dict:
        return self.logical_nodes


class MQTTBrokerMock:
    """
    Mocks an MQTT Client publishing SCADA tag topic payloads.
    """
    def __init__(self):
        self.published_messages = []

    def publish(self, topic: str, payload: dict):
        msg = {
            "topic": topic,
            "payload": json.dumps(payload),
            "timestamp": time.time()
        }
        self.published_messages.append(msg)
        # Keep list size under 50
        if len(self.published_messages) > 50:
            self.published_messages.pop(0)

    def get_last_payload(self, topic: str) -> dict:
        for msg in reversed(self.published_messages):
            if msg["topic"] == topic:
                return json.loads(msg["payload"])
        return {}


# Initialize Simulator instances
modbus_server = ModbusTCPSimulator()
opc_server = OPCUASimulator()
can_bus = CANBusSimulator()
iec_61850 = IEC61850Simulator()
mqtt_broker = MQTTBrokerMock()
