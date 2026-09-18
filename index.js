// Core SCADA and EMS Frontend Logic
let isConnected = false;
let socket = null;
let activeTab = "can";
let navActiveTab = "dashboard";

// Real-time assets status state
let assetsState = {
  solar: { status: "DISCONNECTED", protocol: "MQTT", collecting: false, last_updated: 0.0, sensor_values: {} },
  wind: { status: "DISCONNECTED", protocol: "MQTT", collecting: false, last_updated: 0.0, sensor_values: {} },
  battery: { status: "DISCONNECTED", protocol: "REST API", collecting: false, last_updated: 0.0, sensor_values: {} },
  grid: { status: "DISCONNECTED", protocol: "Modbus TCP", collecting: false, last_updated: 0.0, sensor_values: {} },
  load: { status: "DISCONNECTED", protocol: "Modbus TCP", collecting: false, last_updated: 0.0, sensor_values: {} }
};

// Shared Microgrid State (Local Simulator fallback)
let telemetry = {
  Solar_Power: 0, Solar_Voltage: 0, Solar_Current: 0, Solar_Temperature: 25,
  Wind_Power: 0, Wind_Speed: 7.0, Wind_RPM: 0,
  Battery_SOC: 50.0, Battery_SOH: 100.0, Battery_Voltage: 380, Battery_Current: 0, Battery_Temperature: 25,
  Grid_Status: 1, Grid_Voltage: 400, Grid_Frequency: 50.0, Grid_Power: 0,
  Load_Demand: 25.0, Load_Voltage: 230, Load_Current: 108,
  Inverter_Status: "RUNNING", Inverter_Efficiency: 98.5, Inverter_Output_Power: 0,
  ems_action: "STANDBY", electricity_cost: 0,
  timestamp: Date.now() / 1000, hour: 12
};

let activeAlarms = [];
let localAlarms = []; // Cache for offline alarms

// Section-level local CSV files parsed in browser
let localDatasets = {
  solar: [],
  wind: [],
  battery: [],
  inverter: [],
  load: [],
  grid: []
};
let localIndices = {
  solar: 0,
  wind: 0,
  battery: 0,
  inverter: 0,
  load: 0,
  grid: 0
};
let localReplayActive = false;
let simulationMode = "NORMAL";

// Manual overrides
let overrides = {
  solar: null,
  wind: null,
  load: null
};

let currentFaceplateSection = null;

// Protocol caching
let protocolData = {
  can: "ID: 0x18F009A1 | DLC: 8 | DATA: 32 0F 0E 7D F1 41 8A B3",
  modbus: { 40001: 0, 40002: 0, 40003: 5000, 40004: 32768, 40005: 1, 40006: 20 },
  opc: {
    "ns=2;s=Microgrid.Solar.Voltage": 0.0,
    "ns=2;s=Microgrid.Solar.Current": 0.0,
    "ns=2;s=Microgrid.Wind.Speed": 7.0,
    "ns=2;s=Microgrid.BESS.SOH": 100.0,
    "ns=2;s=Microgrid.Load.Demand": 25.0,
    "ns=2;s=Microgrid.Grid.Frequency": 50.0
  },
  iec: {
    "Grid_XCBR1.Pos.stVal": 1,
    "Grid_XCBR1.Pos.q": "Good",
    "Inverter_MMXU1.TotW.mag.f": 0.0,
    "Inverter_MMXU1.TotHz.mag.f": 50.0
  }
};

// Initialize Chart.js
const ctx = document.getElementById('liveTrendChart').getContext('2d');
const trendChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Solar Power (kW)', data: [], borderColor: '#eab308', backgroundColor: 'rgba(234, 179, 8, 0.05)', borderWidth: 1.5, fill: true, tension: 0.3 },
      { label: 'Wind Power (kW)', data: [], borderColor: '#a855f7', backgroundColor: 'rgba(168, 85, 247, 0.05)', borderWidth: 1.5, fill: true, tension: 0.3 },
      { label: 'Load Demand (kW)', data: [], borderColor: '#f43f5e', backgroundColor: 'rgba(244, 63, 94, 0.05)', borderWidth: 1.5, fill: true, tension: 0.3 },
      { label: 'Battery SOC (%)', data: [], borderColor: '#10b981', borderWidth: 2, pointRadius: 0, tension: 0.3 },
      { label: 'Grid Power (kW)', data: [], borderColor: '#3b82f6', borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0 }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94a3b8', font: { family: 'Outfit', size: 10 } } }
    },
    scales: {
      x: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#64748b', font: { size: 9 } } },
      y: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#64748b', font: { size: 9 } } }
    }
  }
});

// Update Trend Charts
function updateChart(timeLabel, solar, wind, load, battery, grid) {
  trendChart.data.labels.push(timeLabel);
  trendChart.data.datasets[0].data.push(solar);
  trendChart.data.datasets[1].data.push(wind);
  trendChart.data.datasets[2].data.push(load);
  trendChart.data.datasets[3].data.push(battery);
  trendChart.data.datasets[4].data.push(grid);

  if (trendChart.data.labels.length > 25) {
    trendChart.data.labels.shift();
    trendChart.data.datasets.forEach(dataset => dataset.data.shift());
  }
  trendChart.update('none');
}

// ----------------------------------------------------
// WEBSOCKET NETWORKING
// ----------------------------------------------------
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname === "localhost" ? "localhost:8000" : `${window.location.hostname}:8000`;
  
  socket = new WebSocket(`${protocol}//${host}/ws`);

  socket.onopen = () => {
    isConnected = true;
    document.getElementById("conn-badge").classList.remove("offline");
    document.getElementById("conn-status-text").innerText = "TELEMETRY LIVE";
    console.log("Supervisory WebSocket Connected");
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.telemetry) {
        telemetry = data.telemetry;
        updateHMI(telemetry);
      }
      if (data.alarms) {
        activeAlarms = data.alarms;
        renderAlarms(activeAlarms);
      }
      if (data.protocols) {
        protocolData = data.protocols;
        updateTerminal();
      }
      if (data.assets_state) {
        assetsState = data.assets_state;
        if (navActiveTab === "data-sources") {
          updateAssetsUI(assetsState);
        } else if (navActiveTab === "live-display") {
          updateLiveDisplayUI(assetsState);
        }
      }
    } catch (e) {
      console.error("Error parsing WebSocket packet:", e);
    }
  };

  socket.onclose = () => {
    isConnected = false;
    document.getElementById("conn-badge").classList.add("offline");
    document.getElementById("conn-status-text").innerText = "LOCAL SIMULATOR";
    console.log("WebSocket Disconnected. Entering Local Sim fallback mode.");
    setTimeout(connectWebSocket, 4000);
  };
}

// Start WebSocket connection attempts
connectWebSocket();

// ----------------------------------------------------
// LOCAL SIMULATION FALLBACK (Runs when offline)
// ----------------------------------------------------
setInterval(() => {
  if (isConnected) {
    // If backend is active, update chart from the streaming telemetry cache
    const timeStr = new Date(telemetry.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    updateChart(timeStr, telemetry.Solar_Power, telemetry.Wind_Power, telemetry.Load_Demand, telemetry.Battery_SOC, telemetry.Grid_Power);
    return;
  }
  
  // 1. Run local physics simulation steps
  const now = new Date();
  const hour = now.getHours() + now.getMinutes() / 60 + now.getSeconds() / 3600;
  
  let solar_power = 0;
  let wind_power = 0;
  let load_demand = 15;
  let battery_soc = telemetry.Battery_SOC;
  let grid_status = (simulationMode === "GRID_OUTAGE") ? 0 : 1;
  let temp = 22.0 + 8.0 * Math.sin(2 * Math.PI * (hour - 9) / 24) + (Math.random() - 0.5);

  // Replay slot override checks
  if (localReplayActive) {
    // Solar
    if (localDatasets.solar.length > 0) {
      let r = localDatasets.solar[localIndices.solar];
      localIndices.solar = (localIndices.solar + 1) % localDatasets.solar.length;
      solar_power = parseFloat(r.solar_power || r.pv_power || r.power || r.solar_kw || 0);
      temp = parseFloat(r.temperature || r.panel_temperature || temp);
      document.getElementById("badge-solar").innerText = `Replaying (${localIndices.solar}/${localDatasets.solar.length})`;
    }
    // Wind
    if (localDatasets.wind.length > 0) {
      let r = localDatasets.wind[localIndices.wind];
      localIndices.wind = (localIndices.wind + 1) % localDatasets.wind.length;
      wind_power = parseFloat(r.wind_power || r.power || r.wind_kw || 0);
      document.getElementById("badge-wind").innerText = `Replaying (${localIndices.wind}/${localDatasets.wind.length})`;
    }
    // Load
    if (localDatasets.load.length > 0) {
      let r = localDatasets.load[localIndices.load];
      localIndices.load = (localIndices.load + 1) % localDatasets.load.length;
      load_demand = parseFloat(r.load_demand || r.load || r.demand || r.load_kw || 15);
      document.getElementById("badge-load").innerText = `Replaying (${localIndices.load}/${localDatasets.load.length})`;
    }
    
    // Update badge-master too if both are replaying from master
    const masterBadge = document.getElementById("badge-master");
    if (masterBadge && localDatasets.solar === localDatasets.wind && localDatasets.solar.length > 0) {
      masterBadge.innerText = `Replaying (${localIndices.solar}/${localDatasets.solar.length})`;
    }
  }

  // Stochastic simulation (if not replayed or overridden)
  if (!localReplayActive || localDatasets.solar.length === 0) {
    if (6.0 <= hour && hour <= 18.0) {
      solar_power = 80.0 * Math.sin(Math.PI * (hour - 6.0) / 12.0) * (simulationMode === "HIGH_RENEWABLES" ? 1.2 : 0.8) + (Math.random() - 0.5);
      solar_power = Math.max(0.0, solar_power);
    }
  }
  if (!localReplayActive || localDatasets.wind.length === 0) {
    wind_power = 15.0 + 8.0 * Math.sin(2 * Math.PI * (hour - 4) / 24) + (Math.random() * 4 - 2);
    if (simulationMode === "HIGH_RENEWABLES") wind_power += 15;
    if (simulationMode === "LOW_RENEWABLES") wind_power = Math.random() * 2;
    wind_power = Math.max(0.0, wind_power);
  }
  if (!localReplayActive || localDatasets.load.length === 0) {
    const t1 = Math.exp(-Math.pow((hour - 8.0) / 2.0, 2));
    const t2 = Math.exp(-Math.pow((hour - 19.0) / 3.0, 2));
    load_demand = 20.0 + 20.0 * t1 + 35.0 * t2 + (Math.random() * 2 - 1);
    if (simulationMode === "PEAK_LOAD") load_demand += 40;
  }

  // Handle Manual overrides
  if (overrides.solar !== null) solar_power = overrides.solar;
  if (overrides.wind !== null) wind_power = overrides.wind;
  if (overrides.load !== null) load_demand = overrides.load;

  // 2. EMS Dispatch Controller rules (client-side JS)
  let p_renewable = solar_power + wind_power;
  let surplus = p_renewable - load_demand;
  let battery_power = 0;
  let grid_power = 0;
  let ems_action = "STANDBY";

  const min_soc = 20.0;
  const max_soc = 95.0;
  const dt = 1.0 / 3600.0; // 1s loop step

  // Retrieve previous temperature for safety derating
  let prev_temp = (typeof telemetry !== "undefined" && telemetry && telemetry.Battery_Temperature !== undefined) ? telemetry.Battery_Temperature : 25.0;
  let max_charge_rate = 50.0;
  let max_discharge_rate = 60.0;
  
  if (!batteryEnabled) {
    max_charge_rate = 0.0;
    max_discharge_rate = 0.0;
  } else if (prev_temp >= 55.0 || prev_temp <= -10.0) {
    max_charge_rate = 0.0;
    max_discharge_rate = 0.0;
  } else if (prev_temp >= 50.0) {
    max_charge_rate = 10.0;
    max_discharge_rate = 15.0;
  } else if (prev_temp >= 45.0) {
    max_charge_rate = 25.0;
    max_discharge_rate = 30.0;
  } else if (prev_temp <= 0.0) {
    max_charge_rate = 0.0;
    max_discharge_rate = 30.0;
  }

  if (grid_status === 0) {
    // Islanding Mode
    if (surplus >= 0) {
      if (battery_soc < max_soc) {
        battery_power = Math.min(surplus, max_charge_rate);
        battery_soc += (battery_power * 0.95 * dt) / 200.0 * 100.0;
        ems_action = "ISLAND_CHARGE";
      } else {
        battery_power = 0;
        ems_action = "ISLAND_BALANCED";
      }
    } else {
      if (battery_soc > min_soc && max_discharge_rate > 0) {
        battery_power = -Math.min(Math.abs(surplus), max_discharge_rate);
        battery_soc += (battery_power * (1 / 0.95) * dt) / 200.0 * 100.0;
        ems_action = "ISLAND_DISCHARGE";
      } else {
        battery_power = 0;
        ems_action = "ISLAND_LOAD_SHED";
      }
    }
  } else {
    // Grid Connected Mode
    if (surplus >= 0) {
      if (battery_soc < max_soc) {
        battery_power = Math.min(surplus, max_charge_rate);
        battery_soc += (battery_power * 0.95 * dt) / 200.0 * 100.0;
        grid_power = -(surplus - battery_power);
        ems_action = "RENEWABLE_CHARGE";
      } else {
        grid_power = -surplus;
        ems_action = "GRID_EXPORT";
      }
    } else {
      const deficit = Math.abs(surplus);
      const is_peak = (14.0 <= hour && hour <= 20.0);
      
      if (battery_soc > min_soc && max_discharge_rate > 0) {
        let discharge = Math.min(deficit, max_discharge_rate);
        battery_power = -discharge;
        battery_soc += (battery_power * (1 / 0.95) * dt) / 200.0 * 100.0;
        grid_power = deficit - discharge;
        ems_action = grid_power > 0 ? "BATTERY_GRID_SUPPORT" : "BATTERY_SUPPORT";
      } else {
        battery_power = 0;
        grid_power = deficit;
        ems_action = "GRID_FALLBACK";
      }
    }
  }

  battery_soc = Math.max(0.0, Math.min(battery_soc, 100.0));

  // Synthesize dynamic voltages
  let solar_voltage = solar_power > 0 ? 380 + Math.random() * 15 : 0;
  let solar_current = solar_voltage > 0 ? (solar_power * 1000) / solar_voltage : 0;
  let wind_rpm = wind_power > 0 ? 120 + wind_power * 7 : 0;
  let load_voltage = 230 + (Math.random() - 0.5);
  let load_current = (load_demand * 1000) / load_voltage;
  let battery_voltage = 320 + 95 * (battery_soc / 100);
  let battery_current = (battery_power * 1000) / battery_voltage;

  telemetry = {
    Solar_Power: Math.round(solar_power * 100) / 100,
    Solar_Voltage: Math.round(solar_voltage * 10) / 10,
    Solar_Current: Math.round(solar_current * 10) / 10,
    Solar_Temperature: Math.round(temp * 10) / 10,
    Wind_Power: Math.round(wind_power * 100) / 100,
    Wind_Speed: Math.round((7.0 + Math.sin(hour)) * 10) / 10,
    Wind_RPM: Math.round(wind_rpm),
    Battery_SOC: Math.round(battery_soc * 100) / 100,
    Battery_SOH: 99.8,
    Battery_Voltage: Math.round(battery_voltage * 10) / 10,
    Battery_Current: Math.round(battery_current * 10) / 10,
    Battery_Temperature: Math.round((25 + Math.abs(battery_current) * 0.05) * 10) / 10,
    Grid_Status: grid_status,
    Grid_Voltage: grid_status === 1 ? Math.round(400 + (Math.random() * 4 - 2)) : 0.0,
    Grid_Frequency: grid_status === 1 ? Math.round((50.0 + (Math.random() - 0.5) * 0.02) * 1000) / 1000 : 0.0,
    Grid_Power: Math.round(grid_power * 100) / 100,
    Load_Demand: Math.round(load_demand * 100) / 100,
    Load_Voltage: Math.round(load_voltage * 10) / 10,
    Load_Current: Math.round(load_current * 10) / 10,
    Inverter_Status: (simulationMode === "FAULT") ? "FAULTED" : "RUNNING",
    Inverter_Efficiency: 98.5,
    Inverter_Output_Power: Math.round(load_demand * 100) / 100,
    ems_action: ems_action,
    electricity_cost: Math.max(0.0, grid_power) * 0.12 * dt,
    timestamp: Date.now() / 1000,
    hour: hour
  };

  // Local Alarms Generator
  localAlarms = [];
  if (telemetry.Grid_Status === 0) {
    localAlarms.push({ id: 1, timestamp: Date.now() / 1000, severity: "CRITICAL", source: "Grid", message: "Utility grid outage detected! System islanded.", status: "ACTIVE" });
  }
  if (telemetry.Inverter_Status === "FAULTED") {
    localAlarms.push({ id: 2, timestamp: Date.now() / 1000, severity: "CRITICAL", source: "Inverter", message: "Inverter system fault: Overcurrent trip.", status: "ACTIVE" });
  }
  if (telemetry.Battery_SOC <= 15.0) {
    localAlarms.push({ id: 3, timestamp: Date.now() / 1000, severity: "CRITICAL", source: "BMS", message: `Battery emergency low SOC: ${telemetry.Battery_SOC}%!`, status: "ACTIVE" });
  } else if (telemetry.Battery_SOC <= 20.0) {
    localAlarms.push({ id: 4, timestamp: Date.now() / 1000, severity: "WARNING", source: "BMS", message: `Battery low SOC: ${telemetry.Battery_SOC}%.`, status: "ACTIVE" });
  }
  if (telemetry.Battery_Temperature > 55.0) {
    localAlarms.push({ id: 5, timestamp: Date.now() / 1000, severity: "CRITICAL", source: "BMS", message: `Battery critical high temperature: ${telemetry.Battery_Temperature}°C!`, status: "ACTIVE" });
  }

  // Parse Local Protocol Telemetry package
  const hexSOC = Math.round(telemetry.Battery_SOC).toString(16).toUpperCase().padStart(2, '0');
  const hexV = Math.round(telemetry.Battery_Voltage * 10).toString(16).toUpperCase().padStart(4, '0');
  const hexI = Math.round(telemetry.Battery_Current * 10 + 32768).toString(16).toUpperCase().padStart(4, '0');
  const hexT = Math.round(telemetry.Battery_Temperature + 40).toString(16).toUpperCase().padStart(2, '0');
  
  protocolData = {
    can: `ID: 0x18F009A1 | DLC: 8 | DATA: ${hexSOC} ${hexV.slice(0, 2)} ${hexV.slice(2, 4)} ${hexI.slice(0, 2)} ${hexI.slice(2, 4)} ${hexT} 0A FC`,
    modbus: {
      40001: Math.round(telemetry.Solar_Power * 10),
      40002: Math.round(telemetry.Wind_Power * 10),
      40003: Math.round(telemetry.Battery_SOC * 100),
      40004: Math.round(telemetry.Inverter_Output_Power * 10) + 32768,
      40005: 1,
      40006: 20
    },
    opc: {
      "ns=2;s=Microgrid.Solar.Voltage": telemetry.Solar_Voltage,
      "ns=2;s=Microgrid.Solar.Current": telemetry.Solar_Current,
      "ns=2;s=Microgrid.Wind.Speed": telemetry.Wind_Speed,
      "ns=2;s=Microgrid.BESS.SOH": telemetry.Battery_SOH,
      "ns=2;s=Microgrid.Load.Demand": telemetry.Load_Demand,
      "ns=2;s=Microgrid.Grid.Frequency": telemetry.Grid_Frequency
    },
    iec: {
      "Grid_XCBR1.Pos.stVal": telemetry.Grid_Status === 1 ? 1 : 2,
      "Grid_XCBR1.Pos.q": "Good",
      "Inverter_MMXU1.TotW.mag.f": telemetry.Inverter_Output_Power,
      "Inverter_MMXU1.TotHz.mag.f": telemetry.Grid_Frequency
    }
  };

  updateHMI(telemetry);
  renderAlarms(localAlarms);
  updateTerminal();

  // Local fallback assetsState update
  if (!isConnected) {
    if (assetsState.solar.collecting) {
      assetsState.solar.sensor_values = {
        irradiance: Math.round(solar_power * 12.5),
        ambient_temp: Math.round(temp * 10) / 10,
        panel_temp: Math.round((temp + solar_power * 0.25) * 10) / 10,
        dc_voltage: Math.round(solar_voltage * 10) / 10,
        dc_current: Math.round(solar_current * 100) / 100,
        ac_power: Math.round(solar_power * 0.985 * 100) / 100,
        inverter_status: solar_power > 0 ? "RUNNING" : "STANDBY",
        inverter_efficiency: 98.5
      };
      assetsState.solar.last_updated = Date.now() / 1000;
    }
    if (assetsState.wind.collecting) {
      assetsState.wind.sensor_values = {
        wind_speed: Math.round((7.0 + Math.sin(hour)) * 10) / 10,
        wind_direction: Math.round((Date.now() / 10000) % 360),
        air_density: 1.225,
        blade_angle: wind_power > 12 ? Math.round((wind_power - 12) * 3) : 0,
        turbine_rpm: Math.round(wind_rpm),
        generator_voltage: wind_power > 0 ? 400.0 : 0.0,
        generator_current: wind_power > 0 ? Math.round((wind_power * 1000) / (400 * 1.73 * 0.95) * 100) / 100 : 0.0,
        generated_power: Math.round(wind_power * 100) / 100
      };
      assetsState.wind.last_updated = Date.now() / 1000;
    }
    if (assetsState.battery.collecting) {
      assetsState.battery.sensor_values = {
        soc: Math.round(battery_soc * 100) / 100,
        soh: 99.8,
        voltage: Math.round(battery_voltage * 10) / 10,
        current: Math.round(battery_current * 100) / 100,
        temperature: Math.round(temp * 10) / 10,
        cell_voltage: Math.round((battery_voltage / 120.0) * 1000) / 1000,
        cell_temperature: Math.round(temp * 10) / 10,
        charge_rate: battery_power > 0 ? Math.round(battery_power * 100) / 100 : 0.0,
        discharge_rate: battery_power < 0 ? Math.round(Math.abs(battery_power) * 100) / 100 : 0.0
      };
      assetsState.battery.last_updated = Date.now() / 1000;
    }
    if (assetsState.grid.collecting) {
      assetsState.grid.sensor_values = {
        voltage: grid_status === 1 ? Math.round(400 + (Math.random() * 4 - 2)) : 0.0,
        current: grid_status === 1 ? Math.round((Math.abs(grid_power) * 1000) / (400 * 1.73) * 100) / 100 : 0.0,
        frequency: grid_status === 1 ? Math.round((50.0 + (Math.random() - 0.5) * 0.02) * 1000) / 1000 : 0.0,
        power_factor: grid_status === 1 ? 0.98 : 0.0,
        import_power: grid_power > 0 ? Math.round(grid_power * 100) / 100 : 0.0,
        export_power: grid_power < 0 ? Math.round(Math.abs(grid_power) * 100) / 100 : 0.0
      };
      assetsState.grid.last_updated = Date.now() / 1000;
    }
    if (assetsState.load.collecting) {
      assetsState.load.sensor_values = {
        load_voltage: Math.round(load_voltage * 10) / 10,
        load_current: Math.round(load_current * 10) / 10,
        active_power: Math.round(load_demand * 100) / 100,
        reactive_power: Math.round((load_demand * 0.42) * 100) / 100,
        apparent_power: Math.round((Math.sqrt(load_demand**2 + (load_demand * 0.42)**2)) * 100) / 100,
        energy_consumption: Math.round((load_demand / 3600.0) * 1000) / 1000
      };
      assetsState.load.last_updated = Date.now() / 1000;
    }
  }

  // Periodic REST poll & UI update checks
  if (typeof window.pollCounter === "undefined") {
    window.pollCounter = 0;
  }
  window.pollCounter++;
  
  if (window.pollCounter % 3 === 0) {
    if (navActiveTab === "data-sources" || navActiveTab === "live-display") {
      pollAssetsStatus();
    }
  } else {
    // If not polling, at least refresh UI elements locally
    if (navActiveTab === "data-sources") {
      updateAssetsUI(assetsState);
    } else if (navActiveTab === "live-display") {
      updateLiveDisplayUI(assetsState);
    }
  }

  // Update live trend chart index
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  updateChart(timeStr, telemetry.Solar_Power, telemetry.Wind_Power, telemetry.Load_Demand, telemetry.Battery_SOC, telemetry.Grid_Power);
}, 1000);

// ----------------------------------------------------
// HMI UPDATE FUNCTIONS
// ----------------------------------------------------
function updateHMI(t) {
  // Update Header Badges
  document.getElementById("mode-badge").innerText = `${simulationMode} (${isConnected ? 'ONLINE' : 'SIM'})`;
  document.getElementById("time-badge").innerText = formatHour(t.hour);
  document.getElementById("tariff-badge").innerText = `$${(14.0 <= t.hour && t.hour <= 20.0 ? 0.35 : 0.12).toFixed(2)}/kWh`;

  // Update Tag values
  document.getElementById("tag-solar-power").innerText = t.Solar_Power.toFixed(2);
  document.getElementById("tag-solar-temp").innerText = `${t.Solar_Temperature.toFixed(1)}°C Panel`;
  
  document.getElementById("tag-wind-power").innerText = t.Wind_Power.toFixed(2);
  document.getElementById("tag-wind-rpm").innerText = `${t.Wind_RPM} RPM`;
  
  document.getElementById("tag-battery-soc").innerText = t.Battery_SOC.toFixed(1);
  document.getElementById("tag-battery-soh").innerText = `SOH: ${Math.round(t.Battery_SOH)}%`;
  document.getElementById("tag-battery-fill").style.height = `${t.Battery_SOC}%`;
  
  const bFill = document.getElementById("tag-battery-fill");
  bFill.classList.remove("warning", "critical");
  if (t.Battery_SOC <= 15) bFill.classList.add("critical");
  else if (t.Battery_SOC <= 30) bFill.classList.add("warning");

  document.getElementById("tag-grid-power").innerText = t.Grid_Power > 0 ? `+${t.Grid_Power.toFixed(2)}` : t.Grid_Power.toFixed(2);
  document.getElementById("tag-grid-voltage").innerText = `${t.Grid_Voltage}V / ${t.Grid_Frequency.toFixed(2)}Hz`;
  
  const gridDot = document.getElementById("tag-grid-dot");
  gridDot.className = "status-dot";
  if (t.Grid_Status === 0) gridDot.style.backgroundColor = "var(--rose)";
  else gridDot.style.backgroundColor = "var(--blue)";

  document.getElementById("tag-load-power").innerText = t.Load_Demand.toFixed(2);
  document.getElementById("tag-load-current").innerText = `${t.Load_Voltage}V / ${t.Load_Current.toFixed(1)}A`;
  
  document.getElementById("tag-pcs-power").innerText = t.Inverter_Output_Power.toFixed(2);
  document.getElementById("tag-pcs-status").innerText = `${t.Inverter_Status} (${t.Inverter_Efficiency}%)`;

  // Synoptic Diagram text updates
  document.getElementById("node-solar-power").textContent = `${t.Solar_Power} kW`;
  document.getElementById("node-solar-meta").textContent = `${t.Solar_Voltage}V / ${t.Solar_Current}A`;
  
  document.getElementById("node-wind-power").textContent = `${t.Wind_Power} kW`;
  document.getElementById("node-wind-meta").textContent = `${t.Wind_Speed} m/s | ${t.Wind_RPM} RPM`;
  
  document.getElementById("node-pcs-power").textContent = `${t.Inverter_Output_Power} kW`;
  document.getElementById("node-pcs-status").textContent = t.Inverter_Status;
  document.getElementById("node-pcs-status").setAttribute("fill", t.Inverter_Status === "FAULTED" ? "var(--rose)" : "var(--emerald)");
  
  document.getElementById("node-battery-soc").textContent = `${Math.round(t.Battery_SOC)}%`;
  document.getElementById("node-battery-current").textContent = `${t.Battery_Current > 0 ? `+${t.Battery_Current}` : t.Battery_Current} A`;
  document.getElementById("node-battery-soh").textContent = `S:${Math.round(t.Battery_SOH)}%`;
  
  document.getElementById("node-grid-power").textContent = t.Grid_Power > 0 ? `Import: ${t.Grid_Power}` : t.Grid_Power < 0 ? `Export: ${Math.abs(t.Grid_Power)}` : "0.0 kW";
  document.getElementById("node-grid-meta").textContent = `${t.Grid_Voltage}V / ${t.Grid_Frequency}Hz`;
  
  document.getElementById("node-load-power").textContent = `${t.Load_Demand} kW`;
  document.getElementById("node-load-meta").textContent = `${t.Load_Voltage}V / ${t.Load_Current.toFixed(1)}A`;
  
  document.getElementById("node-ems-action").textContent = `EMS: ${t.ems_action}`;

  // Flow line animation velocities
  updateFlowAnimation("flow-solar", t.Solar_Power, false);
  updateFlowAnimation("flow-wind", t.Wind_Power, false);
  updateFlowAnimation("flow-battery", t.Battery_Current, true); // bidirectional
  updateFlowAnimation("flow-grid", t.Grid_Power, false); // bidirectional
  updateFlowAnimation("flow-load", t.Load_Demand, false);

  // Render open faceplate content
  if (currentFaceplateSection) {
    renderFaceplateContent(currentFaceplateSection, t);
  }
}

function updateFlowAnimation(elementId, value, isBidirectional) {
  const line = document.getElementById(elementId);
  if (!line) return;
  
  if (value === 0) {
    line.className.baseVal = "flow-line inactive";
    return;
  }
  
  line.className.baseVal = "flow-line";
  
  // Calculate dash offset speed proportional to power magnitude
  const absVal = Math.abs(value);
  const duration = Math.max(0.3, Math.min(3.0, 15.0 / absVal)); // smaller duration = faster
  line.style.animationDuration = `${duration}s`;
  
  if (isBidirectional) {
    if (value > 0) line.classList.add("reverse"); // charge / import direction
    else line.classList.remove("reverse");
  } else {
    // If grid export (power < 0), reverse line
    if (elementId === "flow-grid" && value < 0) {
      line.classList.add("reverse");
    } else {
      line.classList.remove("reverse");
    }
  }
}

function formatHour(hourDecimal) {
  const h = Math.floor(hourDecimal);
  const m = Math.floor((hourDecimal - h) * 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

// ----------------------------------------------------
// ALARMS RENDERING
// ----------------------------------------------------
function renderAlarms(alarms) {
  const container = document.getElementById("active-alarms-container");
  document.getElementById("alarm-count-badge").innerText = alarms.length;
  
  if (alarms.length === 0) {
    container.innerHTML = `
      <div class="empty-alarm-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #475569; margin-bottom: 8px;"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        No active alarms detected. System status nominal.
      </div>`;
    return;
  }
  
  let html = "";
  alarms.forEach(alarm => {
    const isCritical = alarm.severity === "CRITICAL";
    const statusLabel = alarm.status === "ACKNOWLEDGED" ? "ACKED" : "ACK";
    
    html += `
      <div class="alarm-item ${isCritical ? '' : 'warning'}">
        <div class="alarm-item-body">
          <h4>${alarm.source.toUpperCase()} [${alarm.severity}]</h4>
          <p>${alarm.message}</p>
          <div class="alarm-item-time">${new Date(alarm.timestamp * 1000).toLocaleTimeString()}</div>
        </div>
        <div class="alarm-actions">
          ${alarm.status === "ACTIVE" ? `
            <button class="btn-action" onclick="ackAlarmAction(${alarm.id})">Acknowledge</button>
          ` : `
            <span style="font-size: 0.6rem; color: var(--text-secondary); font-weight: bold; padding: 4px; border: 1px solid var(--border-light); border-radius: 4px;">ACKED</span>
          `}
          <button class="btn-action" onclick="clearAlarmAction(${alarm.id})">Clear</button>
        </div>
      </div>`;
  });
  container.innerHTML = html;
}

function ackAlarmAction(id) {
  if (isConnected) {
    fetch("http://localhost:8000/api/alarms/acknowledge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alarm_id: id })
    });
  } else {
    // Local Ack
    const alarm = localAlarms.find(a => a.id === id);
    if (alarm) alarm.status = "ACKNOWLEDGED";
    renderAlarms(localAlarms);
  }
}

function clearAlarmAction(id) {
  if (isConnected) {
    fetch("http://localhost:8000/api/alarms/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alarm_id: id })
    });
  } else {
    // Local Clear
    localAlarms = localAlarms.filter(a => a.id !== id);
    renderAlarms(localAlarms);
  }
}

// ----------------------------------------------------
// SUPERVISORY COMMAND LISTENERS
// ----------------------------------------------------
document.getElementById("btn-apply-overrides").addEventListener("click", () => {
  const sim = document.getElementById("simulation-scenario").value;
  const sol = document.getElementById("override-solar").value;
  const wnd = document.getElementById("override-wind").value;
  const lod = document.getElementById("override-load").value;
  
  const payload = {
    simulation_mode: sim,
    solar_override: sol !== "" ? parseFloat(sol) : null,
    wind_override: wnd !== "" ? parseFloat(wnd) : null,
    load_override: lod !== "" ? parseFloat(lod) : null
  };
  
  if (isConnected) {
    fetch("http://localhost:8000/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } else {
    // Local updates
    simulationMode = sim;
    overrides.solar = payload.solar_override;
    overrides.wind = payload.wind_override;
    overrides.load = payload.load_override;
    
    if (sim === "REPLAY") {
      localReplayActive = true;
      document.getElementById("replay-state-indicator").innerText = "REPLAYING";
      document.getElementById("btn-toggle-replay").innerText = "Pause Replay";
    } else {
      localReplayActive = false;
      document.getElementById("replay-state-indicator").innerText = "SIMULATING";
    }
  }
});

document.getElementById("btn-clear-overrides").addEventListener("click", () => {
  document.getElementById("override-solar").value = "";
  document.getElementById("override-wind").value = "";
  document.getElementById("override-load").value = "";
  document.getElementById("simulation-scenario").value = "NORMAL";
  
  if (isConnected) {
    fetch("http://localhost:8000/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_mode: "NORMAL" })
    });
  } else {
    simulationMode = "NORMAL";
    overrides.solar = null;
    overrides.wind = null;
    overrides.load = null;
    localReplayActive = false;
    document.getElementById("replay-state-indicator").innerText = "SIMULATING";
  }
});

document.getElementById("btn-ingest-live").addEventListener("click", () => {
  const solar = parseFloat(document.getElementById("live-solar").value) || 0.0;
  const wind = parseFloat(document.getElementById("live-wind").value) || 0.0;
  const load = parseFloat(document.getElementById("live-load").value) || 0.0;
  const grid = parseFloat(document.getElementById("live-grid").value) || 0.0;
  const temp = parseFloat(document.getElementById("live-temp").value) || 25.0;
  const current = parseFloat(document.getElementById("live-current").value) || 0.0;
  const grid_status = parseInt(document.getElementById("live-grid-status").value) === 0 ? 0 : 1;
  const soc = document.getElementById("live-soc").value !== "" ? parseFloat(document.getElementById("live-soc").value) : null;

  const payload = {
    solar_power: solar,
    wind_power: wind,
    load_demand: load,
    grid_power: grid,
    battery_temp: temp,
    battery_current: current,
    grid_status: grid_status,
    battery_soc: soc
  };

  if (isConnected) {
    fetch("http://localhost:8000/api/live-data", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": "Bearer mock-jwt-token-admin-12345"
      },
      body: JSON.stringify(payload)
    }).then(res => {
      if (res.ok) {
        return res.json();
      } else {
        alert("Ingestion endpoint returned error status.");
      }
    }).then(data => {
      if (data) {
        simulationMode = "LIVE";
        document.getElementById("mode-badge").innerText = `LIVE (${isConnected ? 'ONLINE' : 'SIM'})`;
        updateTelemetryView(data.telemetry);
      }
    });
  } else {
    simulationMode = "LIVE";
    document.getElementById("mode-badge").innerText = "LIVE (SIM)";
    
    let calculated_soc = soc !== null ? soc : telemetry.Battery_SOC;
    let calculated_volt = 320 + 95 * (calculated_soc / 100);
    
    telemetry = {
      ...telemetry,
      hour: (new Date().getHours() + new Date().getMinutes()/60.0),
      timestamp: Date.now() / 1000,
      Solar_Power: solar,
      Solar_Voltage: solar > 0 ? 385.0 : 0.0,
      Solar_Current: solar > 0 ? (solar * 1000)/385.0 : 0.0,
      Wind_Power: wind,
      Wind_RPM: wind > 0 ? 300.0 : 0.0,
      Battery_SOC: Math.round(calculated_soc * 100) / 100,
      Battery_Voltage: Math.round(calculated_volt * 10) / 10,
      Battery_Current: current,
      Battery_Temperature: temp,
      Load_Demand: load,
      Grid_Power: grid,
      Grid_Status: grid_status,
      Inverter_Output_Power: Math.max(0.0, load - grid),
      ems_action: "LIVE_EXTERNAL_PUSH"
    };
    
    updateTelemetryView(telemetry);
    alert("Live telemetry ingested locally (Offline).");
  }
});

// ----------------------------------------------------
// LOCAL CSV PARSING AND DATASET ATTACHMENT
// ----------------------------------------------------
function uploadSectionCSV(section, file) {
  if (!file) return;
  
  if (isConnected) {
    // If online, post file to FastAPI backend section endpoint
    const formData = new FormData();
    formData.append("file", file);
    
    fetch(`http://localhost:8000/api/upload-dataset/${section}`, {
      method: "POST",
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      document.getElementById(`badge-${section}`).innerText = `Parsed ${data.replay_dataset_size} rows`;
      document.getElementById(`badge-${section}`).classList.remove("simulated");
      document.getElementById("btn-toggle-replay").removeAttribute("disabled");
    })
    .catch(err => {
      alert(`API Upload error: ${err.message}`);
    });
    
  } else {
    // Parse CSV locally in the browser!
    const reader = new FileReader();
    reader.onload = function(e) {
      const text = e.target.result;
      const parsed = parseCSVText(text);
      if (parsed.length > 0) {
        if (section === "master") {
          ["solar", "wind", "load"].forEach(sec => {
            localDatasets[sec] = parsed;
            localIndices[sec] = 0;
            const badge = document.getElementById(`badge-${sec}`);
            if (badge) {
              badge.innerText = `Parsed ${parsed.length} rows`;
              badge.classList.remove("simulated");
            }
          });
          const masterBadge = document.getElementById("badge-master");
          if (masterBadge) {
            masterBadge.innerText = `Parsed ${parsed.length} rows`;
            masterBadge.classList.remove("simulated");
          }
        } else {
          localDatasets[section] = parsed;
          localIndices[section] = 0;
          const badge = document.getElementById(`badge-${section}`);
          if (badge) {
            badge.innerText = `Parsed ${parsed.length} rows`;
            badge.classList.remove("simulated");
          }
        }
        
        // Enable toggle replay button
        document.getElementById("btn-toggle-replay").removeAttribute("disabled");
        // Automatically activate replay
        localReplayActive = true;
        simulationMode = "REPLAY";
        document.getElementById("simulation-scenario").value = "REPLAY";
        document.getElementById("replay-state-indicator").innerText = "REPLAYING";
        document.getElementById("btn-toggle-replay").innerText = "Pause Replay";
      } else {
        alert("Parsed CSV is empty or invalid format.");
      }
    };
    reader.readAsText(file);
  }
}

function parseCSVText(text) {
  const lines = text.split("\n");
  if (lines.length < 2) return [];
  
  const headers = lines[0].split(",").map(h => h.trim().toLowerCase());
  const rows = [];
  
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    if (cols.length === headers.length) {
      const row = {};
      headers.forEach((h, idx) => {
        row[h] = cols[idx].trim();
      });
      rows.push(row);
    }
  }
  return rows;
}

document.getElementById("btn-toggle-replay").addEventListener("click", () => {
  if (isConnected) {
    fetch("http://localhost:8000/api/toggle-replay", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("replay-state-indicator").innerText = data.replay_active ? "REPLAYING" : "PAUSED";
      document.getElementById("btn-toggle-replay").innerText = data.replay_active ? "Pause Replay" : "Resume Replay";
      simulationMode = data.replay_active ? "REPLAY" : "NORMAL";
      document.getElementById("simulation-scenario").value = simulationMode;
    });
  } else {
    // Local toggle
    localReplayActive = !localReplayActive;
    document.getElementById("replay-state-indicator").innerText = localReplayActive ? "REPLAYING" : "PAUSED";
    document.getElementById("btn-toggle-replay").innerText = localReplayActive ? "Pause Replay" : "Resume Replay";
    simulationMode = localReplayActive ? "REPLAY" : "NORMAL";
    document.getElementById("simulation-scenario").value = simulationMode;
  }
});

// ----------------------------------------------------
// COMMUNICATION TERMINAL TAB SWITCHER
// ----------------------------------------------------
function switchTerminalTab(tab) {
  activeTab = tab;
  // Toggle tab buttons
  document.querySelectorAll(".terminal-tab-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  // Add active class (approximate button by text)
  event.target.classList.add("active");
  updateTerminal();
}

function updateTerminal() {
  const body = document.getElementById("protocol-body");
  if (activeTab === "can") {
    body.textContent = protocolData.can;
  } else if (activeTab === "modbus") {
    let str = "// Holding Registers Block:\n";
    Object.entries(protocolData.modbus).forEach(([k, v]) => {
      str += `Register ${k}: ${v} (dec)\n`;
    });
    body.textContent = str;
  } else if (activeTab === "opcua") {
    let str = "// OPC UA Address Node values:\n";
    Object.entries(protocolData.opc).forEach(([k, v]) => {
      str += `Node ${k} => Value: ${v}\n`;
    });
    body.textContent = str;
  } else if (activeTab === "iec") {
    let str = "// IEC 61850 Substation automation tree:\n";
    Object.entries(protocolData.iec).forEach(([k, v]) => {
      str += `LogicalNode path: ${k} => stVal: ${v}\n`;
    });
    body.textContent = str;
  }
}

// ----------------------------------------------------
// SCADA HMI BLOCK FACEPLATE INTERACTION
// ----------------------------------------------------
function openFaceplate(section) {
  currentFaceplateSection = section;
  const overlay = document.getElementById("faceplate-overlay");
  const modal = document.getElementById("faceplate-modal");
  
  overlay.style.display = "block";
  modal.style.display = "block";
  
  setTimeout(() => {
    overlay.classList.add("active");
    modal.classList.add("active");
  }, 10);
  
  renderFaceplateContent(section, telemetry);
}

function closeFaceplate() {
  currentFaceplateSection = null;
  const overlay = document.getElementById("faceplate-overlay");
  const modal = document.getElementById("faceplate-modal");
  
  overlay.classList.remove("active");
  modal.classList.remove("active");
  
  setTimeout(() => {
    overlay.style.display = "none";
    modal.style.display = "none";
  }, 250);
}

function getFaceplateIcon(section) {
  const yellow = "var(--yellow)";
  const purple = "var(--purple)";
  const emerald = "var(--emerald)";
  const slate = "var(--text-primary)";
  const blue = "var(--blue)";
  const rose = "var(--rose)";
  
  if (section === 'solar') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${yellow}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="M6.34 17.66l-1.41 1.41"></path><path d="M19.07 4.93l-1.41 1.41"></path></svg>`;
  } else if (section === 'wind') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${purple}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.8 19.6A2 2 0 1 0 14 16H2"></path><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2"></path><path d="M9.8 4.4A2 2 0 1 1 11 8H2"></path></svg>`;
  } else if (section === 'battery') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${emerald}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="16" height="10" rx="2" ry="2"></rect><line x1="22" y1="11" x2="22" y2="13"></line></svg>`;
  } else if (section === 'inverter') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${slate}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"></rect><rect width="6" height="6" x="9" y="9" rx="1"></rect><path d="M9 1v3"></path><path d="M15 1v3"></path><path d="M9 20v3"></path><path d="M15 20v3"></path><path d="M20 9h3"></path><path d="M20 15h3"></path><path d="M1 9h3"></path><path d="M1 15h3"></path></svg>`;
  } else if (section === 'grid') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${blue}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>`;
  } else if (section === 'load') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${rose}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>`;
  }
  return "";
}

function renderFaceplateContent(section, t) {
  const title = document.getElementById("faceplate-title");
  const iconContainer = document.getElementById("faceplate-icon-container");
  const statusBadge = document.getElementById("faceplate-status-badge");
  const gridContent = document.getElementById("faceplate-grid-content");
  const assetContent = document.getElementById("faceplate-asset-content");
  
  if (!title || !iconContainer || !statusBadge || !gridContent || !assetContent) return;
  
  iconContainer.innerHTML = getFaceplateIcon(section);
  
  let gridHtml = "";
  let assetHtml = "";
  
  if (section === 'solar') {
    title.innerText = "Solar PV Array Details";
    const generating = t.Solar_Power > 0;
    statusBadge.innerText = generating ? "STATUS: GENERATING" : "STATUS: STANDBY (NIGHT)";
    statusBadge.className = "faceplate-status-badge" + (generating ? "" : " warning");
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Array Output Power</span>
        <div class="faceplate-metric-value">${t.Solar_Power.toFixed(2)}<span class="faceplate-metric-unit">kW</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">MPPT DC Voltage</span>
        <div class="faceplate-metric-value">${t.Solar_Voltage.toFixed(1)}<span class="faceplate-metric-unit">V</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Solar DC Current</span>
        <div class="faceplate-metric-value">${t.Solar_Current.toFixed(2)}<span class="faceplate-metric-unit">A</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Module Temperature</span>
        <div class="faceplate-metric-value">${t.Solar_Temperature.toFixed(1)}<span class="faceplate-metric-unit">°C</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Solar Irradiance</span>
        <div class="faceplate-metric-value">${(t.Solar_Power * 12.5).toFixed(0)}<span class="faceplate-metric-unit">W/m²</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">PV Cell Health (SOH)</span>
        <div class="faceplate-metric-value">94.2<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card" style="grid-column: span 2;">
        <span class="faceplate-metric-label">MPPT Converter Efficiency</span>
        <div class="faceplate-metric-value" style="color: var(--emerald);">99.1<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Manufacturer:</span><span class="faceplate-asset-value">Apex Solar Tech</span>
      <span class="faceplate-asset-label">Model:</span><span class="faceplate-asset-value">APX-Mono-540W-Bifacial</span>
      <span class="faceplate-asset-label">Installed Capacity:</span><span class="faceplate-asset-value">80.0 kWp</span>
      <span class="faceplate-asset-label">Cell Technology:</span><span class="faceplate-asset-value">Monocrystalline PERC</span>
      <span class="faceplate-asset-label">Degradation Index:</span><span class="faceplate-asset-value">0.55% / Year</span>
      <span class="faceplate-asset-label">Installation Date:</span><span class="faceplate-asset-value">2024-04-12</span>
    `;
  } else if (section === 'wind') {
    title.innerText = "Wind Turbine Details";
    const generating = t.Wind_Power > 0;
    statusBadge.innerText = generating ? "STATUS: GENERATING" : "STATUS: STANDBY (CALM)";
    statusBadge.className = "faceplate-status-badge" + (generating ? "" : " warning");
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Turbine Power Output</span>
        <div class="faceplate-metric-value">${t.Wind_Power.toFixed(2)}<span class="faceplate-metric-unit">kW</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Rotor Speed</span>
        <div class="faceplate-metric-value">${t.Wind_RPM}<span class="faceplate-metric-unit">RPM</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Wind Speed</span>
        <div class="faceplate-metric-value">${t.Wind_Speed.toFixed(1)}<span class="faceplate-metric-unit">m/s</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Cp (Power Coefficient)</span>
        <div class="faceplate-metric-value">0.42<span class="faceplate-metric-unit"></span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Generator Temp</span>
        <div class="faceplate-metric-value">${(40 + t.Wind_Power * 0.1).toFixed(1)}<span class="faceplate-metric-unit">°C</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Mechanical SOH</span>
        <div class="faceplate-metric-value">96.8<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card" style="grid-column: span 2;">
        <span class="faceplate-metric-label">Converter Efficiency</span>
        <div class="faceplate-metric-value" style="color: var(--emerald);">94.5<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Manufacturer:</span><span class="faceplate-asset-value">AeroWind Systems</span>
      <span class="faceplate-asset-label">Model:</span><span class="faceplate-asset-value">DMSG-1.5MW-VarPitch</span>
      <span class="faceplate-asset-label">Blade Diameter:</span><span class="faceplate-asset-value">22.5 meters</span>
      <span class="faceplate-asset-label">Generator Type:</span><span class="faceplate-asset-value">Direct Drive PM Sync</span>
      <span class="faceplate-asset-label">Cut-in Wind Speed:</span><span class="faceplate-asset-value">2.5 m/s</span>
      <span class="faceplate-asset-label">Pitch Mechanism:</span><span class="faceplate-asset-value">Hydraulic Active Pitch</span>
    `;
  } else if (section === 'battery') {
    title.innerText = "Battery BESS Details";
    const mode = t.Battery_Current > 0 ? "charging" : t.Battery_Current < 0 ? "discharging" : "standby";
    const power = (t.Battery_Voltage * t.Battery_Current / 1000).toFixed(2);
    
    if (mode === "charging") {
      statusBadge.innerText = "STATUS: CHARGING";
      statusBadge.className = "faceplate-status-badge warning";
    } else if (mode === "discharging") {
      statusBadge.innerText = "STATUS: DISCHARGING";
      statusBadge.className = "faceplate-status-badge";
    } else {
      statusBadge.innerText = "STATUS: STANDBY";
      statusBadge.className = "faceplate-status-badge warning";
    }
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Active Power (DC)</span>
        <div class="faceplate-metric-value" style="color: ${t.Battery_Current > 0 ? 'var(--emerald)' : t.Battery_Current < 0 ? 'var(--rose)' : 'var(--text-primary)'}">${power}<span class="faceplate-metric-unit">kW</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">State of Charge (SOC)</span>
        <div class="faceplate-metric-value">${t.Battery_SOC.toFixed(1)}<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Pack DC Voltage</span>
        <div class="faceplate-metric-value">${t.Battery_Voltage.toFixed(1)}<span class="faceplate-metric-unit">V</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Pack DC Current</span>
        <div class="faceplate-metric-value" style="color: ${t.Battery_Current > 0 ? 'var(--amber)' : t.Battery_Current < 0 ? 'var(--rose)' : 'var(--text-primary)'}">${t.Battery_Current.toFixed(1)}<span class="faceplate-metric-unit">A</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">BESS Temperature</span>
        <div class="faceplate-metric-value">${t.Battery_Temperature.toFixed(1)}<span class="faceplate-metric-unit">°C</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">State of Health (SOH)</span>
        <div class="faceplate-metric-value">${Math.round(t.Battery_SOH)}<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Battery Cycle Count</span>
        <div class="faceplate-metric-value">142<span class="faceplate-metric-unit">cyc</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Round-Trip Efficiency</span>
        <div class="faceplate-metric-value">95.0<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Chemistry:</span><span class="faceplate-asset-value">Lithium Iron Phosphate (LFP)</span>
      <span class="faceplate-asset-label">Nominal Energy Capacity:</span><span class="faceplate-asset-value">200 kWh</span>
      <span class="faceplate-asset-label">Power Rating:</span><span class="faceplate-asset-value">100 kW Continuous</span>
      <span class="faceplate-asset-label">Cell Configuration:</span><span class="faceplate-asset-value">120S 4P Rack System</span>
      <span class="faceplate-asset-label">BMS Controller:</span><span class="faceplate-asset-value">BMS-SAE-J1939 v2.4</span>
      <span class="faceplate-asset-label">Thermal Management:</span><span class="faceplate-asset-value">Liquid Glycol Loops</span>
    `;
  } else if (section === 'inverter') {
    title.innerText = "Hybrid PCS Inverter Details";
    const faulted = t.Inverter_Status === "FAULTED";
    statusBadge.innerText = "STATUS: " + t.Inverter_Status;
    statusBadge.className = "faceplate-status-badge" + (faulted ? " critical" : t.Inverter_Status === "RUNNING" ? "" : " warning");
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Inverter Output (AC)</span>
        <div class="faceplate-metric-value">${t.Inverter_Output_Power.toFixed(2)}<span class="faceplate-metric-unit">kW</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Conversion Efficiency</span>
        <div class="faceplate-metric-value" style="color: var(--emerald);">${t.Inverter_Efficiency.toFixed(1)}<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Heatsink Temperature</span>
        <div class="faceplate-metric-value">${(40 + Math.abs(t.Inverter_Output_Power) * 0.15).toFixed(1)}<span class="faceplate-metric-unit">°C</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">DC Link Bus Voltage</span>
        <div class="faceplate-metric-value">680.0<span class="faceplate-metric-unit">V</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">AC Frequency</span>
        <div class="faceplate-metric-value">${t.Grid_Frequency.toFixed(3)}<span class="faceplate-metric-unit">Hz</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Thermal SOH (Health)</span>
        <div class="faceplate-metric-value">98.2<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">PWM Switching Freq</span>
        <div class="faceplate-metric-value">8.0<span class="faceplate-metric-unit">kHz</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Output Voltage THD</span>
        <div class="faceplate-metric-value">1.2<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Manufacturer:</span><span class="faceplate-asset-value">Apex Power Conversion</span>
      <span class="faceplate-asset-label">Model:</span><span class="faceplate-asset-value">APX-PCS-120kVA-GF</span>
      <span class="faceplate-asset-label">Inverter Topology:</span><span class="faceplate-asset-value">3-Level T-Type NPC</span>
      <span class="faceplate-asset-label">Grid Compliance:</span><span class="faceplate-asset-value">IEEE 1547 / UL 1741 SB</span>
      <span class="faceplate-asset-label">Cooling Mode:</span><span class="faceplate-asset-value">Forced Air Cooling (Dual Fan)</span>
      <span class="faceplate-asset-label">Firmware Version:</span><span class="faceplate-asset-value">v4.92.1-DSP</span>
    `;
  } else if (section === 'grid') {
    title.innerText = "Utility Grid Interconnection";
    const connected = t.Grid_Status === 1;
    statusBadge.innerText = connected ? "STATUS: CONNECTED" : "STATUS: ISLANDED (OUTAGE)";
    statusBadge.className = "faceplate-status-badge" + (connected ? "" : " critical");
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Tie-Line Active Power</span>
        <div class="faceplate-metric-value" style="color: ${t.Grid_Power > 0 ? 'var(--blue)' : t.Grid_Power < 0 ? 'var(--emerald)' : 'var(--text-primary)'}">
          ${t.Grid_Power > 0 ? 'Import: ' + t.Grid_Power.toFixed(2) : t.Grid_Power < 0 ? 'Export: ' + Math.abs(t.Grid_Power).toFixed(2) : '0.00'}
          <span class="faceplate-metric-unit">kW</span>
        </div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Line Voltage (Ph-Ph)</span>
        <div class="faceplate-metric-value">${t.Grid_Voltage}<span class="faceplate-metric-unit">V</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Grid Frequency</span>
        <div class="faceplate-metric-value">${t.Grid_Frequency.toFixed(3)}<span class="faceplate-metric-unit">Hz</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Active Power Factor</span>
        <div class="faceplate-metric-value">0.98<span class="faceplate-metric-unit"></span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Billing Tariff Rate</span>
        <div class="faceplate-metric-value" style="color: var(--amber);">$${(14.0 <= t.hour && t.hour <= 20.0 ? 0.35 : 0.12).toFixed(2)}<span class="faceplate-metric-unit">/kWh</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Power Quality Index</span>
        <div class="faceplate-metric-value">99.9<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Interconnection Node:</span><span class="faceplate-asset-value">Substation Feeder #4B</span>
      <span class="faceplate-asset-label">Utility Operator:</span><span class="faceplate-asset-value">Metro Grid Power Co.</span>
      <span class="faceplate-asset-label">Protective Relay:</span><span class="faceplate-asset-value">SEL-751 Feeder Relay</span>
      <span class="faceplate-asset-label">Logical Node Path:</span><span class="faceplate-asset-value">Grid_XCBR1.Pos</span>
      <span class="faceplate-asset-label">Max Power Import Limit:</span><span class="faceplate-asset-value">150.0 kW</span>
      <span class="faceplate-asset-label">Line Active Impedance:</span><span class="faceplate-asset-value">0.15 + j0.08 Ω</span>
    `;
  } else if (section === 'load') {
    title.innerText = "Load Feeder Details";
    statusBadge.innerText = "STATUS: ONLINE";
    statusBadge.className = "faceplate-status-badge";
    
    gridHtml = `
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Active Power Demand</span>
        <div class="faceplate-metric-value" style="color: var(--rose);">${t.Load_Demand.toFixed(2)}<span class="faceplate-metric-unit">kW</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Feeder AC Voltage</span>
        <div class="faceplate-metric-value">${t.Load_Voltage}<span class="faceplate-metric-unit">V</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Feeder AC Current</span>
        <div class="faceplate-metric-value">${t.Load_Current.toFixed(1)}<span class="faceplate-metric-unit">A</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Average Power Factor</span>
        <div class="faceplate-metric-value">0.92<span class="faceplate-metric-unit">lag</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Reactive Power (VAR)</span>
        <div class="faceplate-metric-value">${(t.Load_Demand * 0.42).toFixed(2)}<span class="faceplate-metric-unit">kVAR</span></div>
      </div>
      <div class="faceplate-metric-card">
        <span class="faceplate-metric-label">Current THDi (Distortion)</span>
        <div class="faceplate-metric-value">2.5<span class="faceplate-metric-unit">%</span></div>
      </div>
      <div class="faceplate-metric-card" style="grid-column: span 2;">
        <span class="faceplate-metric-label">Feeder Insulation SOH</span>
        <div class="faceplate-metric-value">99.5<span class="faceplate-metric-unit">%</span></div>
      </div>
    `;
    
    assetHtml = `
      <span class="faceplate-asset-label">Feeder Designation:</span><span class="faceplate-asset-value">Feeder #A (Factory Load)</span>
      <span class="faceplate-asset-label">Main Breaker Type:</span><span class="faceplate-asset-value">Air Circuit Breaker (ACB)</span>
      <span class="faceplate-asset-label">Protective Setting:</span><span class="faceplate-asset-value">Overcurrent / Earth Fault</span>
      <span class="faceplate-asset-label">Smart Meter Protocol:</span><span class="faceplate-asset-value">OPC UA Client (Nodes ns=2)</span>
      <span class="faceplate-asset-label">Connected Phase:</span><span class="faceplate-asset-value">3-Phase 3-Wire Delta</span>
    `;
  }
  
  gridContent.innerHTML = gridHtml;
  assetContent.innerHTML = assetHtml;
}

// ----------------------------------------------------
// NEW SCADA TABS AND INDIVIDUAL ACQUISITION MODULES
// ----------------------------------------------------
function switchNavTab(tabName) {
  navActiveTab = tabName;
  
  // Toggle nav buttons
  document.querySelectorAll(".nav-tab").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
  
  // Toggle tab contents
  document.querySelectorAll(".tab-content").forEach(content => {
    if (content.getAttribute("id") === `tab-${tabName}`) {
      content.classList.add("active-tab-content");
      content.style.display = "block";
    } else {
      content.classList.remove("active-tab-content");
      content.style.display = "none";
    }
  });
  
  // Perform immediate updates
  if (tabName === "data-sources") {
    pollAssetsStatus();
  } else if (tabName === "live-display") {
    pollAssetsStatus();
  }
}

function connectAssetBtn(asset) {
  const protocol = document.getElementById(`${asset}-protocol-select`).value;
  
  if (isConnected) {
    // Post protocol updates first
    fetch(`http://localhost:8000/api/assets/${asset}/protocol`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer mock-jwt-token-admin-12345"
      },
      body: JSON.stringify({ protocol: protocol })
    })
    .then(() => {
      return fetch(`http://localhost:8000/api/assets/${asset}/connect`, {
        method: "POST",
        headers: {
          "Authorization": "Bearer mock-jwt-token-admin-12345"
        }
      });
    })
    .then(res => res.json())
    .then(() => {
      pollAssetsStatus();
    });
  } else {
    // Local simulated transition
    assetsState[asset].status = "CONNECTING";
    assetsState[asset].protocol = protocol;
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
    setTimeout(() => {
      if (assetsState[asset].status === "CONNECTING") {
        assetsState[asset].status = "CONNECTED";
        assetsState[asset].collecting = true; // start automatically
        updateAssetsUI(assetsState);
        updateLiveDisplayUI(assetsState);
      }
    }, 1000);
  }
}

function disconnectAssetBtn(asset) {
  if (isConnected) {
    fetch(`http://localhost:8000/api/assets/${asset}/disconnect`, {
      method: "POST",
      headers: {
        "Authorization": "Bearer mock-jwt-token-admin-12345"
      }
    })
    .then(res => res.json())
    .then(() => {
      pollAssetsStatus();
    });
  } else {
    assetsState[asset].status = "DISCONNECTED";
    assetsState[asset].collecting = false;
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
  }
}

function startIngestBtn(asset) {
  if (isConnected) {
    fetch(`http://localhost:8000/api/assets/${asset}/start`, {
      method: "POST",
      headers: {
        "Authorization": "Bearer mock-jwt-token-admin-12345"
      }
    })
    .then(res => res.json())
    .then(() => {
      pollAssetsStatus();
    });
  } else {
    assetsState[asset].collecting = true;
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
  }
}

function stopIngestBtn(asset) {
  if (isConnected) {
    fetch(`http://localhost:8000/api/assets/${asset}/stop`, {
      method: "POST",
      headers: {
        "Authorization": "Bearer mock-jwt-token-admin-12345"
      }
    })
    .then(res => res.json())
    .then(() => {
      pollAssetsStatus();
    });
  } else {
    assetsState[asset].collecting = false;
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
  }
}

function pollAssetsStatus() {
  if (!isConnected) {
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
    return;
  }
  fetch("http://localhost:8000/api/assets/status")
  .then(res => res.json())
  .then(data => {
    assetsState = data;
    updateAssetsUI(assetsState);
    updateLiveDisplayUI(assetsState);
  });
}


function updateAssetsUI(state) {
  let activeChannels = 0;
  
  Object.entries(state).forEach(([asset, data]) => {
    const isConnectedAsset = data.status === "CONNECTED";
    const isConnectingAsset = data.status === "CONNECTING";
    const isDisconnectedAsset = data.status === "DISCONNECTED";
    
    if (isConnectedAsset) activeChannels++;
    
    // Update status dot and text
    const dot = document.getElementById(`${asset}-status-dot`);
    const txt = document.getElementById(`${asset}-status-text`);
    
    if (dot && txt) {
      dot.className = "status-dot " + data.status.toLowerCase();
      txt.innerText = data.status;
    }
    
    // Update select disabled state
    const select = document.getElementById(`${asset}-protocol-select`);
    if (select) {
      select.value = data.protocol || select.value;
      select.disabled = !isDisconnectedAsset;
    }
    
    // Update stats
    const activeTags = document.getElementById(`${asset}-active-tags`);
    const dataRate = document.getElementById(`${asset}-data-rate`);
    const lastUpdate = document.getElementById(`${asset}-last-update`);
    
    const totalTagsCount = asset === 'solar' ? 8 : (asset === 'wind' ? 8 : (asset === 'battery' ? 9 : 6));
    if (activeTags) {
      activeTags.innerText = (isConnectedAsset && data.collecting) ? `${totalTagsCount} Tags` : "0 Tags";
    }
    if (dataRate) {
      dataRate.innerText = data.collecting ? (data.protocol === "Modbus RTU" ? "1.0 Hz" : "5.0 Hz") : "0.0 Hz";
    }
    if (lastUpdate) {
      lastUpdate.innerText = (data.last_updated && data.last_updated > 0) 
        ? new Date(data.last_updated * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : "Never";
    }
    
    // Activity bar
    const activity = document.getElementById(`${asset}-activity-container`);
    if (activity) {
      activity.style.display = data.collecting ? "block" : "none";
    }
    
    // Action buttons
    const actions = document.getElementById(`${asset}-actions-container`);
    if (actions) {
      if (isDisconnectedAsset) {
        actions.className = "card-actions-grid";
        actions.innerHTML = `<button class="btn btn-connect" onclick="connectAssetBtn('${asset}')">Connect</button>`;
      } else if (isConnectingAsset) {
        actions.className = "card-actions-grid";
        actions.innerHTML = `<button class="btn btn-secondary" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);" disabled>Connecting...</button>`;
      } else {
        actions.className = "card-actions-grid split";
        const ingestBtnHtml = data.collecting 
          ? `<button class="btn btn-stop-ingest" onclick="stopIngestBtn('${asset}')">Stop Ingest</button>`
          : `<button class="btn btn-start-ingest" onclick="startIngestBtn('${asset}')">Start Ingest</button>`;
        actions.innerHTML = `
          <button class="btn btn-disconnect" onclick="disconnectAssetBtn('${asset}')">Disconnect</button>
          ${ingestBtnHtml}
        `;
      }
    }
  });
  
  const activeCountBadge = document.getElementById("active-channels-count");
  if (activeCountBadge) {
    activeCountBadge.innerText = `${activeChannels} ACTIVE CHANNELS`;
  }
}

function updateLiveDisplayUI(state) {
  Object.entries(state).forEach(([asset, data]) => {
    const card = document.getElementById(`live-card-${asset}`);
    if (!card) return;
    
    if (!data.collecting) {
      // Show offline template
      let iconHtml = "";
      if (asset === 'solar') iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--yellow)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="M6.34 17.66l-1.41 1.41"></path><path d="M19.07 4.93l-1.41 1.41"></path></svg>`;
      if (asset === 'wind') iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.8 19.6A2 2 0 1 0 14 16H2"></path><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2"></path><path d="M9.8 4.4A2 2 0 1 1 11 8H2"></path></svg>`;
      if (asset === 'battery') iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--emerald)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="16" height="10" rx="2" ry="2"></rect><line x1="22" y1="11" x2="22" y2="13"></line></svg>`;
      if (asset === 'grid') iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>`;
      if (asset === 'load') iconHtml = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--rose)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>`;
      
      card.innerHTML = `
        <div class="live-placeholder">
          ${iconHtml}
          <p style="font-weight: bold; margin-top: 8px;">Asset Offline</p>
          <p style="color: var(--text-secondary); font-size: 0.65rem; margin-top: 4px;">
            Connect to ${asset} sensors in "Data Sources" to activate live telemetry stream.
          </p>
        </div>
      `;
      return;
    }
    
    // Asset is actively collecting! Update live tags
    const vals = data.sensor_values || {};
    
    if (asset === 'solar') {
      const irradiance = parseFloat(vals.irradiance || 0).toFixed(0);
      const panelTemp = parseFloat(vals.panel_temp || 0).toFixed(1);
      const dcVolt = parseFloat(vals.dc_voltage || 0).toFixed(1);
      const acPower = parseFloat(vals.ac_power || 0).toFixed(2);
      
      card.innerHTML = `
        <div class="asset-card-header">
          <div class="asset-card-title text-yellow" style="color: var(--yellow);">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="M6.34 17.66l-1.41 1.41"></path><path d="M19.07 4.93l-1.41 1.41"></path></svg>
            <span>Solar Array</span>
          </div>
          <span style="font-size: 0.65rem; font-family: monospace; color: var(--emerald);">STREAMING</span>
        </div>
        
        <div class="spinning-dial-outer">
          <div class="spinning-dial-ring solar-theme"></div>
          <span class="spinning-dial-val">${irradiance}</span>
        </div>
        <p style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); text-align: center; margin-top: -6px; font-weight: bold;">Irradiance W/m²</p>
        
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Panel Temp:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--amber);">${panelTemp}°C</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">MPPT Voltage:</span>
            <span style="font-family: monospace; font-weight: bold;">${dcVolt}V</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(234, 179, 8, 0.08); padding: 6px; border-radius: 6px; border: 1px solid rgba(234, 179, 8, 0.12);">
            <span style="font-weight: bold; color: var(--yellow);">AC Output Power:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--yellow);">${acPower} kW</span>
          </div>
        </div>
      `;
    } else if (asset === 'wind') {
      const windSpeed = parseFloat(vals.wind_speed || 0).toFixed(1);
      const turbineRPM = parseFloat(vals.turbine_rpm || 0).toFixed(0);
      const bladeAngle = parseFloat(vals.blade_angle || 0).toFixed(1);
      const generatedPower = parseFloat(vals.generated_power || 0).toFixed(2);
      
      card.innerHTML = `
        <div class="asset-card-header">
          <div class="asset-card-title text-purple" style="color: var(--purple);">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.8 19.6A2 2 0 1 0 14 16H2"></path><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2"></path><path d="M9.8 4.4A2 2 0 1 1 11 8H2"></path></svg>
            <span>Wind Turbine</span>
          </div>
          <span style="font-size: 0.65rem; font-family: monospace; color: var(--emerald);">STREAMING</span>
        </div>
        
        <div class="spinning-dial-outer">
          <div class="spinning-dial-ring wind-theme"></div>
          <span class="spinning-dial-val">${windSpeed}</span>
        </div>
        <p style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); text-align: center; margin-top: -6px; font-weight: bold;">Wind Speed m/s</p>
        
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Rotor Speed:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--purple);">${turbineRPM} RPM</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Blade Angle:</span>
            <span style="font-family: monospace; font-weight: bold;">${bladeAngle}°</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(168, 85, 247, 0.08); padding: 6px; border-radius: 6px; border: 1px solid rgba(168, 85, 247, 0.12);">
            <span style="font-weight: bold; color: var(--purple);">Generated Power:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--purple);">${generatedPower} kW</span>
          </div>
        </div>
      `;
    } else if (asset === 'battery') {
      const soc = parseFloat(vals.soc || 0).toFixed(0);
      const voltage = parseFloat(vals.voltage || 0).toFixed(1);
      const temp = parseFloat(vals.temperature || 0).toFixed(1);
      const current = parseFloat(vals.current || 0).toFixed(1);
      
      card.innerHTML = `
        <div class="asset-card-header">
          <div class="asset-card-title text-emerald" style="color: var(--emerald);">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="16" height="10" rx="2" ry="2"></rect><line x1="22" y1="11" x2="22" y2="13"></line></svg>
            <span>Battery BESS</span>
          </div>
          <span style="font-size: 0.65rem; font-family: monospace; color: var(--emerald);">STREAMING</span>
        </div>
        
        <div class="spinning-dial-outer">
          <div class="spinning-dial-ring battery-theme"></div>
          <span class="spinning-dial-val">${soc}%</span>
        </div>
        <p style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); text-align: center; margin-top: -6px; font-weight: bold;">State of Charge</p>
        
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Pack Voltage:</span>
            <span style="font-family: monospace; font-weight: bold;">${voltage}V</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Pack Temp:</span>
            <span style="font-family: monospace; font-weight: bold;">${temp}°C</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(16, 185, 129, 0.08); padding: 6px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.12);">
            <span style="font-weight: bold; color: var(--emerald);">Pack Current:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--emerald);">${current} A</span>
          </div>
        </div>
      `;
    } else if (asset === 'grid') {
      const freq = parseFloat(vals.frequency || 0).toFixed(2);
      const voltage = parseFloat(vals.voltage || 0).toFixed(0);
      const current = parseFloat(vals.current || 0).toFixed(1);
      const imp = parseFloat(vals.import_power || 0);
      const exp = parseFloat(vals.export_power || 0);
      
      const flowVal = imp > 0 ? `Imp: ${imp.toFixed(1)}kW` : `Exp: ${exp.toFixed(1)}kW`;
      
      card.innerHTML = `
        <div class="asset-card-header">
          <div class="asset-card-title text-blue" style="color: var(--blue);">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            <span>Grid Tie</span>
          </div>
          <span style="font-size: 0.65rem; font-family: monospace; color: var(--emerald);">STREAMING</span>
        </div>
        
        <div class="spinning-dial-outer">
          <div class="spinning-dial-ring grid-theme"></div>
          <span class="spinning-dial-val">${freq}Hz</span>
        </div>
        <p style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); text-align: center; margin-top: -6px; font-weight: bold;">Line Frequency</p>
        
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Line Voltage:</span>
            <span style="font-family: monospace; font-weight: bold;">${voltage}V</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Line Current:</span>
            <span style="font-family: monospace; font-weight: bold;">${current}A</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(59, 130, 246, 0.08); padding: 6px; border-radius: 6px; border: 1px solid rgba(59, 130, 246, 0.12);">
            <span style="font-weight: bold; color: var(--blue);">Import/Export:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--blue);">${flowVal}</span>
          </div>
        </div>
      `;
    } else if (asset === 'load') {
      const act = parseFloat(vals.active_power || 0).toFixed(0);
      const voltage = parseFloat(vals.load_voltage || 0).toFixed(0);
      const energy = parseFloat(vals.energy_consumption || 0).toFixed(2);
      const react = parseFloat(vals.reactive_power || 0).toFixed(1);
      
      card.innerHTML = `
        <div class="asset-card-header">
          <div class="asset-card-title text-rose" style="color: var(--rose);">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>
            <span>Load Feeder</span>
          </div>
          <span style="font-size: 0.65rem; font-family: monospace; color: var(--emerald);">STREAMING</span>
        </div>
        
        <div class="spinning-dial-outer">
          <div class="spinning-dial-ring load-theme"></div>
          <span class="spinning-dial-val">${act}kW</span>
        </div>
        <p style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); text-align: center; margin-top: -6px; font-weight: bold;">Active Demand</p>
        
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Feeder Voltage:</span>
            <span style="font-family: monospace; font-weight: bold;">${voltage}V</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
            <span style="color: var(--text-secondary);">Total Consumption:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--rose);">${energy} kWh</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(244, 63, 94, 0.08); padding: 6px; border-radius: 6px; border: 1px solid rgba(244, 63, 94, 0.12);">
            <span style="font-weight: bold; color: var(--rose);">Reactive Power:</span>
            <span style="font-family: monospace; font-weight: bold; color: var(--rose);">${react} kVAR</span>
          </div>
        </div>
      `;
    }
  });
}

