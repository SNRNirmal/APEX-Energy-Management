import unittest
import time
from database import db
from simulator import MicrogridSimulator
from ems import EMSEngine
from protocols import modbus_server, can_bus, iec_61850

class TestEMSSystem(unittest.TestCase):
    def setUp(self):
        # Reset DB settings to defaults before each test
        db.set_setting("battery_min_soc", "20.0")
        db.set_setting("battery_max_soc", "100.0")
        db.set_setting("export_enabled", "true")

    def test_database_settings(self):
        db.set_setting("test_key", "hello_world")
        self.assertEqual(db.get_setting("test_key"), "hello_world")

    def test_solar_simulation(self):
        sim = MicrogridSimulator()
        
        # Test Solar PV curve at noon (12 PM)
        # We simulate this by mocking system telemetry step
        # But we want to test direct physics curves
        telemetry_noon = sim.update_states()
        self.assertGreaterEqual(telemetry_noon["Solar_Power"], 0.0)
        self.assertGreaterEqual(telemetry_noon["Solar_Voltage"], 0.0)

    def test_wind_simulation(self):
        sim = MicrogridSimulator()
        
        # Test Wind Turbine using manual overrides
        # 1. Under cut-in speed / zero power override
        sim.manual_wind_override = 0.0
        telemetry = sim.update_states()
        self.assertEqual(telemetry["Wind_Power"], 0.0)
        self.assertEqual(telemetry["Wind_RPM"], 0.0)
        
        # 2. Positive power override
        sim.manual_wind_override = 25.0
        telemetry_override = sim.update_states()
        self.assertEqual(telemetry_override["Wind_Power"], 25.0)
        self.assertEqual(telemetry_override["Wind_RPM"], 450.0)

    def test_ems_dispatch_logic(self):
        engine = EMSEngine()
        
        # Test Case 1: Renewable Priority Mode (Surplus)
        # Solar + Wind = 80 kW, Load = 30 kW -> surplus = 50 kW
        # Battery should charge with 50 kW, Grid import = 0 kW
        telemetry = {
            "timestamp": time.time(),
            "Solar_Power": 50.0,
            "Wind_Power": 30.0,
            "Load_Demand": 30.0,
            "Grid_Status": 1
        }
        # Force SOC to 50%
        db.log_telemetry({"Battery_SOC": 50.0})
        dispatch = engine.compute_dispatch(telemetry)
        self.assertEqual(dispatch["battery_power"], 50.0)
        self.assertEqual(dispatch["grid_power"], 0.0)
        self.assertEqual(dispatch["ems_action"], "RENEWABLE_CHARGE")

        # Test Case 2: Battery Support Mode (Deficit, SOC > 20%)
        # Solar + Wind = 10 kW, Load = 40 kW -> deficit = 30 kW
        # Battery should discharge 30 kW to supply the load, Grid import = 0 kW
        telemetry = {
            "timestamp": time.time(),
            "Solar_Power": 5.0,
            "Wind_Power": 5.0,
            "Load_Demand": 40.0,
            "Grid_Status": 1
        }
        db.log_telemetry({"Battery_SOC": 50.0}) # Available BESS
        dispatch = engine.compute_dispatch(telemetry)
        self.assertEqual(dispatch["battery_power"], -30.0)
        self.assertEqual(dispatch["grid_power"], 0.0)
        self.assertEqual(dispatch["ems_action"], "BATTERY_SUPPORT")

        # Test Case 3: Grid Fallback Mode (Deficit, SOC <= 20%)
        # Solar + Wind = 0 kW, Load = 30 kW -> deficit = 30 kW
        # Battery empty. Grid should import 30 kW.
        telemetry = {
            "timestamp": time.time(),
            "Solar_Power": 0.0,
            "Wind_Power": 0.0,
            "Load_Demand": 30.0,
            "Grid_Status": 1
        }
        db.log_telemetry({"Battery_SOC": 19.5}) # Below 20%
        dispatch = engine.compute_dispatch(telemetry)
        self.assertEqual(dispatch["battery_power"], 0.0)
        self.assertEqual(dispatch["grid_power"], 30.0)
        self.assertEqual(dispatch["ems_action"], "GRID_FALLBACK")

        # Test Case 4: Grid Export Mode (Surplus, SOC = 100%)
        # Solar + Wind = 80 kW, Load = 30 kW -> surplus = 50 kW
        # Battery full. Export 50 kW to Grid.
        telemetry = {
            "timestamp": time.time(),
            "Solar_Power": 60.0,
            "Wind_Power": 20.0,
            "Load_Demand": 30.0,
            "Grid_Status": 1
        }
        db.log_telemetry({"Battery_SOC": 100.0}) # Battery full
        dispatch = engine.compute_dispatch(telemetry)
        self.assertEqual(dispatch["battery_power"], 0.0)
        self.assertEqual(dispatch["grid_power"], -50.0)
        self.assertEqual(dispatch["ems_action"], "GRID_EXPORT")

    def test_protocol_packing(self):
        # 1. Modbus packing
        telemetry = {"Solar_Power": 45.5, "Wind_Power": 12.0, "Battery_SOC": 82.5, "Inverter_Output_Power": 15.0}
        modbus_server.update_registers(telemetry, {"export_enabled": "true", "battery_min_soc": 20.0})
        registers = modbus_server.read_registers(40001, 6)
        self.assertEqual(registers[40001], 455)
        self.assertEqual(registers[40002], 120)
        self.assertEqual(registers[40003], 8250)
        
        # 2. CAN Frame verification
        frame = can_bus.encode_bms_frame(82.5, 385.4, -22.5, 31.0)
        self.assertTrue("ID: 0x18F009A1" in frame)
        self.assertTrue("DLC: 8" in frame)
        self.assertTrue("DATA:" in frame)
        
        # 3. IEC 61850 Breaker Position mapping
        telemetry_outage = {"Grid_Status": 0, "Inverter_Output_Power": 0.0}
        iec_61850.update_nodes(telemetry_outage)
        self.assertEqual(iec_61850.get_ln_values()["Grid_XCBR1.Pos.stVal"], 2) # Open

    def test_component_isolation_ems_logic(self):
        engine = EMSEngine()
        
        # Test Case 1: Battery Disabled (Manual Isolation)
        # Solar + Wind = 10 kW, Load = 40 kW -> deficit = 30 kW
        # Normally battery discharges, but battery is disabled! Grid fallback should supply all 30 kW.
        telemetry = {
            "timestamp": time.time(),
            "Solar_Power": 5.0,
            "Wind_Power": 5.0,
            "Load_Demand": 40.0,
            "Grid_Status": 1,
            "battery_enabled": False
        }
        db.log_telemetry({"Battery_SOC": 80.0}) # Battery is full but disabled
        dispatch = engine.compute_dispatch(telemetry)
        self.assertEqual(dispatch["battery_power"], 0.0)
        self.assertEqual(dispatch["grid_power"], 30.0)
        self.assertEqual(dispatch["ems_action"], "GRID_FALLBACK")

        # Test Case 2: Grid and Battery both Disabled (Islanded blackout)
        # Solar + Wind = 10 kW, Load = 40 kW -> deficit = 30 kW
        # Deficit is large, battery is disabled, grid is disconnected -> Load shedding level 3 should be triggered.
        telemetry_blackout = {
            "timestamp": time.time(),
            "Solar_Power": 5.0,
            "Wind_Power": 5.0,
            "Load_Demand": 40.0,
            "Grid_Status": 0,
            "battery_enabled": False
        }
        dispatch_blackout = engine.compute_dispatch(telemetry_blackout)
        self.assertEqual(dispatch_blackout["battery_power"], 0.0)
        self.assertEqual(dispatch_blackout["grid_power"], 0.0)
        self.assertEqual(dispatch_blackout["load_shedding_level"], 3)

    def test_simulator_attribute_error_on_battery_isolated(self):
        sim = MicrogridSimulator()
        sim.battery_enabled = False
        
        # Call update_battery_physics, should not raise AttributeError and return current=0.0
        try:
            battery_data = sim.update_battery_physics(10.0)
            self.assertEqual(battery_data["Battery_Current"], 0.0)
            self.assertEqual(battery_data["Battery_Voltage"], 368.0)
        except AttributeError as e:
            self.fail(f"AttributeError was raised during battery isolation update: {e}")

    def test_database_grid_exports(self):
        import random
        # Create a unique timestamp to avoid primary key conflict
        timestamp = time.time() - random.randint(10000, 20000)
        db.log_telemetry({
            "timestamp": timestamp,
            "Solar_Power": 10.0,
            "Wind_Power": 5.0,
            "Battery_SOC": 90.0,
            "Grid_Power": -25.0,  # Negative grid power indicates export
            "Load_Demand": 5.0
        })
        
        with db.lock:
            cursor = db.conn.cursor()
            cursor.execute("SELECT * FROM scada_historian WHERE grid_power < 0 AND timestamp = ?", (timestamp,))
            row = cursor.fetchone()
            
        self.assertIsNotNone(row)
        self.assertEqual(row["grid_power"], -25.0)

    def test_fan_manual_override(self):
        sim = MicrogridSimulator()
        
        # 1. Test AUTO fan control (temp < 35C -> OFF)
        sim.battery_temp = 25.0
        sim.manual_fan_override = None
        data = sim.update_battery_physics(0.0)
        self.assertEqual(data["Battery_Fan_Status"], "OFF")
        
        # 2. Test AUTO fan control (temp >= 35C -> ON)
        sim.battery_temp = 38.0
        sim.manual_fan_override = None
        data = sim.update_battery_physics(0.0)
        self.assertEqual(data["Battery_Fan_Status"], "ON")
        
        # 3. Test Manual ON override (even if temp < 35C)
        sim.battery_temp = 25.0
        sim.manual_fan_override = "ON"
        data = sim.update_battery_physics(0.0)
        self.assertEqual(data["Battery_Fan_Status"], "ON")
        
        # 4. Test Manual OFF override (even if temp >= 35C)
        sim.battery_temp = 42.0
        sim.manual_fan_override = "OFF"
        data = sim.update_battery_physics(0.0)
        self.assertEqual(data["Battery_Fan_Status"], "OFF")
        
        # 5. Test Fan Failure overrides manual setting
        sim.manual_fan_override = "ON"
        sim.simulate_failure("FAN_FAILURE", True)
        data = sim.update_battery_physics(0.0)
        self.assertEqual(data["Battery_Fan_Status"], "FAULTED")

    def test_battery_low_temperature_constraints(self):
        engine = EMSEngine()
        
        # 1. Freezing limit (<= 0.0°C): Cannot charge, but can discharge
        # Test Charge attempt at -2°C
        telemetry_freeze = {
            "timestamp": time.time(),
            "Solar_Power": 50.0,
            "Wind_Power": 30.0,
            "Load_Demand": 30.0,  # Surplus = 50kW
            "Grid_Status": 1,
            "Battery_Temperature": -2.0,
            "battery_enabled": True
        }
        db.log_telemetry({"Battery_SOC": 50.0})
        dispatch = engine.compute_dispatch(telemetry_freeze)
        self.assertEqual(dispatch["battery_power"], 0.0) # Freezing, should not charge
        self.assertEqual(dispatch["grid_power"], -50.0)  # Export instead
        
        # Test Discharge attempt at -2°C (should be allowed up to derated 30kW limit)
        telemetry_freeze_deficit = {
            "timestamp": time.time(),
            "Solar_Power": 0.0,
            "Wind_Power": 0.0,
            "Load_Demand": 40.0,  # Deficit = 40kW
            "Grid_Status": 1,
            "Battery_Temperature": -2.0,
            "battery_enabled": True
        }
        db.log_telemetry({"Battery_SOC": 50.0})
        dispatch = engine.compute_dispatch(telemetry_freeze_deficit)
        self.assertEqual(dispatch["battery_power"], -30.0) # Freezing derating max discharge is 30.0
        self.assertEqual(dispatch["grid_power"], 10.0)

        # 2. Critical Cold limit (<= -10.0°C): Battery shutdown
        telemetry_extreme_cold = {
            "timestamp": time.time(),
            "Solar_Power": 0.0,
            "Wind_Power": 0.0,
            "Load_Demand": 40.0,  # Deficit = 40kW
            "Grid_Status": 1,
            "Battery_Temperature": -12.0,
            "battery_enabled": True
        }
        db.log_telemetry({"Battery_SOC": 50.0})
        dispatch = engine.compute_dispatch(telemetry_extreme_cold)
        self.assertEqual(dispatch["battery_power"], 0.0) # Shutdown entirely
        self.assertEqual(dispatch["grid_power"], 40.0) # Grid covers all load

    def test_live_data_ingestion_endpoint(self):
        import asyncio
        from main import receive_live_data, LiveDataModel, simulator
        
        payload = LiveDataModel(
            solar_power=60.0,
            wind_power=20.0,
            battery_temp=28.5,
            battery_current=-15.0,
            load_demand=50.0,
            grid_power=10.0,
            grid_status=1,
            battery_soc=55.0,
            battery_voltage=372.0
        )
        
        # Test synchronous call to receive_live_data coroutine
        loop = asyncio.get_event_loop()
        resp = loop.run_until_complete(receive_live_data(payload, "Bearer mock-jwt-token-admin-12345"))
        
        self.assertEqual(resp["status"], "SUCCESS")
        self.assertEqual(resp["telemetry"]["Solar_Power"], 60.0)
        self.assertEqual(resp["telemetry"]["Battery_SOC"], 55.0)
        self.assertEqual(resp["telemetry"]["Battery_Current"], -15.0)
        self.assertEqual(simulator.simulation_mode, "LIVE")

    def test_realtime_database_logging(self):
        # Log solar real-time
        db.log_solar_realtime({"irradiance": 800.0, "panel_temp": 45.0, "ac_power": 45.0})
        history = db.get_realtime_history("solar", limit=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["irradiance"], 800.0)
        self.assertEqual(history[0]["panel_temp"], 45.0)

        # Log wind real-time
        db.log_wind_realtime({"wind_speed": 12.0, "generated_power": 35.0})
        history_wind = db.get_realtime_history("wind", limit=1)
        self.assertEqual(len(history_wind), 1)
        self.assertEqual(history_wind[0]["wind_speed"], 12.0)

        # Log battery real-time
        db.log_battery_realtime({"soc": 78.5, "temperature": 32.0})
        history_bat = db.get_realtime_history("battery", limit=1)
        self.assertEqual(len(history_bat), 1)
        self.assertEqual(history_bat[0]["soc"], 78.5)

    def test_asset_acquisition_endpoints(self):
        import asyncio
        from main import connect_asset, disconnect_asset, update_asset_protocol, ProtocolModel, assets_state
        
        # Test protocol update
        update_asset_protocol("solar", ProtocolModel(protocol="Modbus TCP"), "Bearer mock-jwt-token-admin-12345")
        self.assertEqual(assets_state["solar"]["protocol"], "Modbus TCP")

        # Test connect
        loop = asyncio.get_event_loop()
        loop.run_until_complete(connect_asset("solar", "Bearer mock-jwt-token-admin-12345"))
        self.assertEqual(assets_state["solar"]["status"], "CONNECTING")

        # Test disconnect
        disconnect_asset("solar", "Bearer mock-jwt-token-admin-12345")
        self.assertEqual(assets_state["solar"]["status"], "DISCONNECTED")
        self.assertEqual(assets_state["solar"]["collecting"], False)

    def test_predictions_endpoint(self):
        from main import get_assets_predictions
        preds = get_assets_predictions()
        self.assertIn("solar", preds)
        self.assertIn("wind", preds)
        self.assertIn("battery", preds)
        self.assertIn("load", preds)
        self.assertIn("predicted", preds["solar"])
        self.assertIn("confidence", preds["solar"])

if __name__ == "__main__":
    unittest.main()


