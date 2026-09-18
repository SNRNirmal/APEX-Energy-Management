import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from simulator import MicrogridSimulator
from verification import apex_verifier
from fastapi.testclient import TestClient
from main import app, latest_telemetry


def test_simulator_battery_power():
    sim = MicrogridSimulator()

    # 1. Discharging test (-15 kW)
    batt_discharging = sim.update_battery_physics(-15.0)
    assert "Battery_Power" in batt_discharging, "Battery_Power missing from physics return dictionary"
    assert batt_discharging["Battery_Power"] == -15.0, f"Expected -15.0 kW, got {batt_discharging['Battery_Power']}"

    # 2. Charging test (+20 kW)
    batt_charging = sim.update_battery_physics(20.0)
    assert batt_charging["Battery_Power"] == 20.0, f"Expected 20.0 kW, got {batt_charging['Battery_Power']}"

    print("PASS: update_battery_physics correctly sets Battery_Power for charging and discharging.")


def test_original_failure_case():
    """
    Original failure case:
    Solar = 0
    Wind = 0
    Battery discharge = 15 kW (Battery_Power = -15.0)
    Grid import = 21.68 kW
    Factory load = 36.68 kW

    Expected energy balance:
    Supply = 15 + 21.68 = 36.68 kW
    Demand = 36.68 kW
    Balance Error ≈ 0 kW
    """
    global latest_telemetry
    import main

    main.latest_telemetry = {
        "Solar_Power": 0.0,
        "Wind_Power": 0.0,
        "Battery_SOC": 50.0,
        "Grid_Power": 21.68,
        "Battery_Power": -15.0,
        "Load_Demand": 36.68,
        "Grid_Status": 1
    }

    client = TestClient(app)
    res = client.get("/api/verification/status")
    assert res.status_code == 200, f"Expected HTTP 200, got {res.status_code}"
    
    data = res.json()
    assert data["valid"] is True, f"Verification failed: {data}"
    assert abs(data["balance_error_kw"]) < 0.001, f"Expected balance error ~ 0, got {data['balance_error_kw']}"
    assert data["supply_total_kw"] == 36.68, f"Expected supply 36.68 kW, got {data['supply_total_kw']}"
    assert data["demand_total_kw"] == 36.68, f"Expected demand 36.68 kW, got {data['demand_total_kw']}"
    assert data["checks"]["energy_balance"] == "PASS", "energy_balance check should be PASS"
    assert data["checks"]["battery_limits"] == "PASS", "battery_limits check should be PASS"
    assert data["checks"]["no_simultaneous_battery_action"] == "PASS", "no_simultaneous_battery_action should be PASS"

    print("PASS: Original failure case resolved! Energy balance error = 0.0 kW.")


if __name__ == "__main__":
    test_simulator_battery_power()
    test_original_failure_case()
    print("\nALL VERIFICATION REGRESSION TESTS PASSED SUCCESSFULLY!")
