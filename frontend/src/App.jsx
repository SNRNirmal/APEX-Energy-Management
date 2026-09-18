import React, { useState, useEffect, useRef } from 'react';
import { 
  Sun, 
  Wind, 
  Battery, 
  Cpu, 
  Activity, 
  AlertTriangle, 
  Settings, 
  Sliders, 
  Terminal, 
  TrendingUp, 
  Zap, 
  RefreshCw, 
  Wifi, 
  WifiOff, 
  Database,
  ArrowRight,
  ArrowLeft,
  Info,
  UserCheck,
  ShieldAlert,
  Play,
  RotateCcw,
  Volume2,
  VolumeX,
  Lock,
  Unlock,
  Leaf,
  Clock,
  Sparkles,
  Flame,
  AlertCircle,
  Moon,
  Download
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend,
  LineChart,
  Line,
  BarChart,
  Bar,
  ReferenceLine
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import ApexDashboard from './components/ApexDashboard';

// Play Web Audio Synth warning beep for critical alarms (reusing a single AudioContext to prevent lag/memory leaks)
let globalAudioCtx = null;
const playAlarmSound = () => {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    if (!globalAudioCtx) {
      globalAudioCtx = new AudioContextClass();
    }
    // Resume context if browser suspended it (autoplay policy)
    if (globalAudioCtx.state === 'suspended') {
      globalAudioCtx.resume();
    }
    const ctx = globalAudioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(660, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(880, ctx.currentTime + 0.15);
    osc.frequency.linearRampToValueAtTime(550, ctx.currentTime + 0.3);
    
    gain.gain.setValueAtTime(0.06, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.start();
    osc.stop(ctx.currentTime + 0.5);
  } catch (err) {
    console.warn("Audio context blocked by browser autoplay policy:", err);
  }
};

// Dynamic SVG Dial Gauge component matching industrial dashboard specs
const DialGauge = ({ min, max, value, title, unit }) => {
  const center = 75;
  const radius = 50;
  
  // Normalize value between 0 and 1
  const t = Math.min(1, Math.max(0, (value - min) / (max - min || 1)));
  // Sweep from 135 to 405 degrees (270 degree sweep)
  const angle_deg = 135 + t * 270;
  const angle_rad = (angle_deg * Math.PI) / 180;
  
  const needleX = center + (radius - 12) * Math.cos(angle_rad);
  const needleY = center + (radius - 12) * Math.sin(angle_rad);
  
  // SVG path arc helper
  const polarToCartesian = (centerX, centerY, radius, angleInDegrees) => {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: centerX + radius * Math.cos(angleInRadians),
      y: centerY + radius * Math.sin(angleInRadians)
    };
  };

  const drawArc = (centerX, centerY, radius, startAngle, endAngle) => {
    const start = polarToCartesian(centerX, centerY, radius, endAngle);
    const end = polarToCartesian(centerX, centerY, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    return [
      "M", start.x, start.y, 
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y
    ].join(" ");
  };

  // Color segments
  const greenArc = drawArc(center, center, radius, 135, 135 + 270 * 0.7);
  const yellowArc = drawArc(center, center, radius, 135 + 270 * 0.7, 135 + 270 * 0.9);
  const redArc = drawArc(center, center, radius, 135 + 270 * 0.9, 405);

  return (
    <div className="flex flex-col items-center p-2.5 bg-slate-900/60 dark:bg-slate-50 border border-slate-800/80 dark:border-slate-300 rounded-xl w-[105px] md:w-[115px] shadow-lg">
      <span className="text-[8px] md:text-[9px] uppercase font-bold text-slate-400 dark:text-slate-550 mb-1 text-center font-sans tracking-wide truncate w-full">{title}</span>
      <svg className="w-20 h-20 md:w-22 md:h-22" viewBox="0 0 150 150">
        {/* Background track */}
        <path d={drawArc(center, center, radius, 135, 405)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round" />
        
        {/* Color Zones */}
        <path d={greenArc} fill="none" stroke="#10b981" strokeWidth="8" />
        <path d={yellowArc} fill="none" stroke="#f59e0b" strokeWidth="8" />
        <path d={redArc} fill="none" stroke="#ef4444" strokeWidth="8" />
        
        {/* Ticks */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((tick, idx) => {
          const a = 135 + tick * 270;
          const r_a = (a * Math.PI) / 180;
          const x1 = center + (radius - 5) * Math.cos(r_a);
          const y1 = center + (radius - 5) * Math.sin(r_a);
          const x2 = center + (radius + 2) * Math.cos(r_a);
          const y2 = center + (radius + 2) * Math.sin(r_a);
          return <line key={idx} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#64748b" strokeWidth="2" />;
        })}

        {/* Needle Pin and line */}
        <circle cx={center} cy={center} r="6" fill="#ef4444" />
        <line x1={center} y1={center} x2={needleX} y2={needleY} stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
        <circle cx={center} cy={center} r="2" fill="#ffffff" />
      </svg>
      <div className="text-center mt-1 font-mono">
        <span className="text-xs md:text-sm font-extrabold text-white dark:text-slate-900">{value.toFixed(1)}</span>
        <span className="text-[9px] text-slate-400 dark:text-slate-500 ml-0.5 font-bold">{unit}</span>
      </div>
    </div>
  );
};

// Physical-style electricity meter digital odometer
const Odometer = ({ value }) => {
  const valStr = Math.round(value * 100).toString().padStart(8, '0');
  const digits = valStr.split('');
  
  return (
    <div className="flex items-center gap-0.5 bg-slate-950 p-1 rounded border border-slate-900 justify-center shadow-lg w-full max-w-[160px] mx-auto">
      {digits.map((char, idx) => {
        const isDecimal = idx >= digits.length - 2;
        return (
          <React.Fragment key={idx}>
            {idx === digits.length - 2 && (
              <span className="text-emerald-500 font-extrabold px-0.5 text-xs animate-pulse">.</span>
            )}
            <span 
              className={`font-mono text-[11px] font-extrabold px-1 py-0.5 rounded shadow ${
                isDecimal 
                  ? 'bg-rose-950 text-rose-350 border border-rose-900' // highlights decimal parts in red
                  : 'bg-slate-900 text-slate-100 border border-slate-850'
              }`}
            >
              {char}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};

// Optimized sub-component for rendering a single alarm row to prevent main-thread layout re-calculation lag
const AlarmRow = React.memo(({ alarm, userRole, ackAlarm, clearAlarm, repairAlarm }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const isCritical = alarm.severity === 'CRITICAL';
  const isAcked = alarm.status === 'ACKNOWLEDGED';
  
  return (
    <div
      className={`rounded-xl border transition-all ${
        isAcked    ? 'bg-slate-900/30 border-slate-700/40 text-slate-400 dark:bg-slate-100 dark:border-slate-300 dark:text-slate-500'
        : isCritical ? 'bg-rose-950/40 border-rose-500/40 text-rose-200 alarm-breathe'
        : 'bg-amber-950/35 border-amber-500/35 text-amber-200'
      }`}
    >
      {/* ── Alarm Header Row ── */}
      <div
        className="p-3 flex items-start justify-between gap-3 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase font-mono ${
              isAcked ? 'bg-slate-700 text-slate-400' : isCritical ? 'bg-rose-600 text-white' : 'bg-amber-500 text-slate-950'
            }`}>{isAcked ? 'ACKNOWLEDGED' : alarm.severity}</span>
            {alarm.fault_code && (
              <span className="px-2 py-0.5 rounded text-[8px] font-mono font-bold bg-slate-800 dark:bg-slate-200 text-slate-400 dark:text-slate-600 border border-slate-700 dark:border-slate-300">
                {alarm.fault_code}
              </span>
            )}
            <span className="text-[9px] font-bold text-slate-500 uppercase">SRC: {alarm.source}</span>
            <span className="text-[9px] text-slate-600">{new Date(alarm.timestamp * 1000).toLocaleTimeString()}</span>
          </div>
          <p className="font-semibold text-[11px] leading-snug">{alarm.message}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {userRole !== 'viewer' && alarm.status === 'ACTIVE' && (
            <button
              onClick={(e) => { e.stopPropagation(); ackAlarm(alarm.id); }}
              className="bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-slate-400 dark:text-slate-600 hover:text-white px-2.5 py-1 rounded-lg text-[9px] font-bold border border-slate-800 dark:border-slate-300 whitespace-nowrap"
            >ACK</button>
          )}
          {userRole !== 'viewer' && (
            <button
              onClick={(e) => { e.stopPropagation(); clearAlarm(alarm.id); }}
              className="bg-slate-900 hover:bg-rose-900/50 dark:bg-slate-100 text-slate-600 hover:text-rose-400 px-2.5 py-1 rounded-lg text-[9px] font-bold border border-slate-800 dark:border-slate-300 whitespace-nowrap"
            >CLEAR</button>
          )}
          <span className={`text-[11px] transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>▾</span>
        </div>
      </div>

      {/* ── Fault Advisor Expanded Panel ── */}
      {isExpanded && alarm.fault_code && (
        <div className={`mx-3 mb-3 rounded-xl border p-3.5 space-y-3 ${
          isCritical
            ? 'bg-rose-950/60 border-rose-700/50'
            : 'bg-amber-950/40 border-amber-700/40'
        }`}>
          {/* Header */}
          <div className="flex items-center gap-2 border-b border-slate-800/60 pb-2">
            <span className="text-[9px] uppercase font-extrabold tracking-widest text-slate-400">⚡ AI Fault Advisor</span>
            <span className={`ml-auto px-2 py-0.5 rounded text-[8px] font-mono font-extrabold ${
              isCritical ? 'bg-rose-800 text-rose-200' : 'bg-amber-800 text-amber-200'
            }`}>{alarm.fault_code}</span>
          </div>

          {/* Root Cause */}
          <div>
            <p className="text-[8px] uppercase font-extrabold text-slate-500 tracking-wider mb-1">🔍 Root Cause Analysis</p>
            <p className="text-[11px] text-slate-300 dark:text-slate-600 leading-relaxed">{alarm.root_cause}</p>
          </div>

          {/* Repair Actions */}
          {alarm.repair_actions && (
            <div>
              <p className="text-[8px] uppercase font-extrabold text-slate-500 tracking-wider mb-1.5">🔧 Repair Actions</p>
              <div className="space-y-1.5">
                {alarm.repair_actions.map((action, idx) => (
                  <div key={idx} className={`flex items-start gap-2 p-2 rounded-lg text-[10px] leading-snug ${
                    isCritical ? 'bg-rose-950/50 text-rose-100' : 'bg-amber-950/40 text-amber-100'
                  }`}>
                    <span className="shrink-0 text-[8px] font-extrabold text-slate-500 mt-0.5">{idx + 1}.</span>
                    <span>{action.replace(/^\d+\.\s*/, '')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer Row: time + safety */}
          <div className="flex flex-col md:flex-row gap-2 pt-1 border-t border-slate-800/50">
            {alarm.estimated_time && (
              <div className="flex items-center gap-1.5 bg-slate-900/60 dark:bg-slate-100 rounded-lg px-2.5 py-1.5 flex-1">
                <span className="text-[8px] text-slate-500 uppercase font-bold tracking-wide">⏱ Est. Repair:</span>
                <span className="text-[10px] font-extrabold text-emerald-400 font-mono">{alarm.estimated_time}</span>
              </div>
            )}
            {alarm.safety_warning && (
              <div className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 flex-1 ${
                isCritical ? 'bg-rose-900/60 border border-rose-700/30' : 'bg-amber-900/40 border border-amber-700/30'
              }`}>
                <span className="text-[9px] leading-snug font-semibold">{alarm.safety_warning}</span>
              </div>
            )}
          </div>

          {/* Mark Resolved */}
          {userRole !== 'viewer' && (
            <div className="flex gap-2">
              <button
                onClick={() => { clearAlarm(alarm.id); setIsExpanded(false); }}
                className="flex-1 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 dark:bg-slate-200 dark:hover:bg-slate-300 border border-slate-750 dark:border-slate-300 text-slate-300 dark:text-slate-700 text-[9px] font-extrabold uppercase tracking-wider transition-all"
              >
                Clear Log Only
              </button>
              <button
                onClick={() => { repairAlarm(alarm.id); setIsExpanded(false); }}
                className="flex-[2] py-1.5 rounded-lg bg-emerald-800/50 hover:bg-emerald-700/60 border border-emerald-750 text-emerald-300 text-[9px] font-extrabold uppercase tracking-wider transition-all"
              >
                🔧 Self-Repair / Resolve Fault
              </button>
            </div>
          )}
        </div>
      )}

      {/* No advisor data fallback */}
      {isExpanded && !alarm.fault_code && (
        <div className="mx-3 mb-3 p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-[10px] text-slate-500 italic">
          No fault advisor data available for this alarm. Contact engineering team.
        </div>
      )}
    </div>
  );
});

export default function App() {
  // Connection states
  const [isConnected, setIsConnected] = useState(false);
  const [telemetry, setTelemetry] = useState({
    Solar_Power: 0, Solar_Voltage: 0, Solar_Current: 0, Solar_Temperature: 0,
    Wind_Power: 0, Wind_Speed: 0, Wind_RPM: 0,
    Battery_SOC: 50, Battery_SOH: 100, Battery_Voltage: 0, Battery_Current: 0, Battery_Temperature: 25,
    Grid_Status: 1, Grid_Voltage: 0, Grid_Frequency: 50, Grid_Power: 0,
    Load_Demand: 0, Load_Current: 0, Load_Voltage: 0,
    Inverter_Status: "RUNNING", Inverter_Efficiency: 98.5, Inverter_Output_Power: 0,
    ems_action: "STANDBY", electricity_cost: 0,
    timestamp: Date.now() / 1000, hour: 12,
    ambient_temp: 25, cloud_cover: 0.2,
    load_shedding_level: 0, original_load: 0,
    active_failures: []
  });
  
  const [activeAlarms, setActiveAlarms] = useState([]);
  const [alarmFilter, setAlarmFilter] = useState('ALL'); // ALL | CRITICAL | WARNING | ACKNOWLEDGED
  const alarmFingerprint = useRef(''); // prevents re-render when alarms haven't changed
  const [historicalData, setHistoricalData] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [forecastExtended, setForecastExtended] = useState([]);
  const [protocolData, setProtocolData] = useState(null);
  
  // Settings Form States
  const [settings, setSettings] = useState({
    battery_min_soc: "20.0",
    battery_max_soc: "100.0",
    tariff_peak_start: "14:00",
    tariff_peak_end: "20:00",
    tariff_peak_rate: "7.50",
    tariff_offpeak_rate: "4.50",
    export_enabled: "true",
    optimization_mode: "NORMAL"
  });

  // Simulator Control Overrides
  const [simulationMode, setSimulationMode] = useState("NORMAL");
  const [solarOverride, setSolarOverride] = useState("");
  const [windOverride, setWindOverride] = useState("");
  const [loadOverride, setLoadOverride] = useState("");
  
  // Live Telemetry Ingestion States
  const [liveSolar, setLiveSolar] = useState("0");
  const [liveWind, setLiveWind] = useState("0");
  const [liveBatteryTemp, setLiveBatteryTemp] = useState("25");
  const [liveBatteryCurrent, setLiveBatteryCurrent] = useState("0");
  const [liveLoadDemand, setLiveLoadDemand] = useState("15");
  const [liveGridPower, setLiveGridPower] = useState("0");
  const [liveGridStatus, setLiveGridStatus] = useState("1");
  const [liveBatterySOC, setLiveBatterySOC] = useState("");
  const [liveBatteryVoltage, setLiveBatteryVoltage] = useState("");
  
  // Manual Component Enabled Switches
  const [solarEnabled, setSolarEnabled] = useState(true);
  const [windEnabled, setWindEnabled] = useState(true);
  const [batteryEnabled, setBatteryEnabled] = useState(true);
  const [gridEnabled, setGridEnabled] = useState(true);
  const [fanOverride, setFanOverride] = useState(null); // null (Auto), "ON", "OFF"
  
  // Replay Scenario states
  const [replayActive, setReplayActive] = useState(false);
  const [sectionSizes, setSectionSizes] = useState({ solar: 0, wind: 0, battery: 0, inverter: 0, load: 0, grid: 0 });
  const [sectionIndices, setSectionIndices] = useState({ solar: 0, wind: 0, battery: 0, inverter: 0, load: 0, grid: 0 });
  const [uploadMsgs, setUploadMsgs] = useState({ solar: "", wind: "", battery: "", inverter: "", load: "", grid: "" });
  const [uploadingSections, setUploadingSections] = useState({ solar: false, wind: false, battery: false, inverter: false, load: false, grid: false });
  
  // UI Tabs / View states
  const [chartTab, setChartTab] = useState("live"); // live, historical, forecast, forecast_extended
  const [protocolTab, setProtocolTab] = useState("can"); // can, modbus, opcua, iec
  const [activeFaceplate, setActiveFaceplate] = useState(null);
  const [modalTab, setModalTab] = useState("live"); // live, stats, settings
  const [activeTab, setActiveTab] = useState("apex"); // apex, dashboard, ems, battery, renewable, grid, ai, alarms, reports, settings
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Real-time Asset connection status and simulation variables
  const [assetsState, setAssetsState] = useState({
    solar: { status: "DISCONNECTED", protocol: "MQTT", collecting: false, last_updated: 0.0, sensor_values: {} },
    wind: { status: "DISCONNECTED", protocol: "MQTT", collecting: false, last_updated: 0.0, sensor_values: {} },
    battery: { status: "DISCONNECTED", protocol: "REST API", collecting: false, last_updated: 0.0, sensor_values: {} },
    grid: { status: "DISCONNECTED", protocol: "Modbus TCP", collecting: false, last_updated: 0.0, sensor_values: {} },
    load: { status: "DISCONNECTED", protocol: "Modbus TCP", collecting: false, last_updated: 0.0, sensor_values: {} }
  });

  const [assetProtocolInputs, setAssetProtocolInputs] = useState({
    solar: "MQTT",
    wind: "MQTT",
    battery: "Direct BMS",
    grid: "Modbus TCP",
    load: "Modbus TCP"
  });

  // Reset modal tab back to live dashboard when faceplate changes
  useEffect(() => {
    setModalTab("live");
  }, [activeFaceplate]);

  const [isChartReady, setIsChartReady] = useState(false);
  useEffect(() => {
    if (activeFaceplate) {
      setIsChartReady(false);
      const timer = setTimeout(() => {
        setIsChartReady(true);
      }, 350);
      return () => clearTimeout(timer);
    } else {
      setIsChartReady(false);
    }
  }, [activeFaceplate]);

  const chartContainerRef = useRef(null);
  const [chartWidth, setChartWidth] = useState(600);

  useEffect(() => {
    if (!activeFaceplate || !chartContainerRef.current) return;
    
    // Set initial width
    const initialWidth = chartContainerRef.current.getBoundingClientRect().width;
    if (initialWidth > 0) {
      setChartWidth(initialWidth);
    }
    
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        if (entry.contentRect.width > 0) {
          setChartWidth(entry.contentRect.width);
        }
      }
    });
    resizeObserver.observe(chartContainerRef.current);
    return () => resizeObserver.disconnect();
  }, [activeFaceplate, isChartReady]);
  
  // Role & Authentication States
  const [userRole, setUserRole] = useState(() => localStorage.getItem('role') || 'viewer');
  const [userToken, setUserToken] = useState(() => localStorage.getItem('token') || '');
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Carbon Analytics State
  const [carbonMetrics, setCarbonMetrics] = useState({
    co2_saved_kg: 12450.0,
    renewable_share_pct: 100.0,
    grid_import_kwh: 0.0,
    grid_export_kwh: 0.0,
    carbon_offset_rate: 0.45
  });

  // Audio Warning Mute State
  const [isAudioMuted, setIsAudioMuted] = useState(true);
  
  // Light/Dark Theme State
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  // Refs for WebSockets
  const ws = useRef(null);

  // API Domain Resolver
  const API_BASE = window.location.hostname === "localhost" ? "http://localhost:8000" : `http://${window.location.hostname}:8000`;

  // Apply CSS Theme class to root
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'cyberpunk', 'green', 'blue', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Connect WebSockets & fetch static components
  useEffect(() => {
    connectWS();
    fetchSettings();
    fetchForecast();
    fetchForecastExtended();
    fetchHistorical();
    fetchCarbonAnalytics();
    
    // Polling fallback interval if WebSocket is closed
    const fallbackInterval = setInterval(() => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        fetchTelemetryREST();
      }
    }, 2000);

    return () => {
      if (ws.current) ws.current.close();
      clearInterval(fallbackInterval);
    };
  }, []);

  // Play audio chime if critical alarms exist and audio is unmuted
  useEffect(() => {
    if (isAudioMuted) return;
    const activeCritical = activeAlarms.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE');
    if (activeCritical.length === 0) return;

    const interval = setInterval(playAlarmSound, 3000);
    playAlarmSound(); // initial play
    return () => clearInterval(interval);
  }, [activeAlarms, isAudioMuted]);

  // Local browser-based simulation backup (runs only if websocket is disconnected)
  useEffect(() => {
    if (isConnected) return;
    
    const simInterval = setInterval(() => {
      setTelemetry(prev => {
        const hour = (prev.hour + 0.05) % 24;
        const ambient = 25.0 + 5.0 * Math.sin(2 * Math.PI * (hour - 8.0) / 24);
        
        let solar = 0.0;
        if (solarOverride !== "" && solarEnabled) {
          solar = parseFloat(solarOverride);
        } else if (6.0 <= hour && hour <= 18.0 && solarEnabled) {
          solar = 85.0 * Math.sin(Math.PI * (hour - 6.0) / 12.0) * (1.0 - prev.cloud_cover);
          solar = Math.max(0.0, solar);
        }
        
        const windSpeed = 7.0 + 3.0 * Math.sin(2 * Math.PI * (hour - 4) / 24) + (Math.random() - 0.5);
        let wind = 0.0;
        if (windOverride !== "" && windEnabled) {
          wind = parseFloat(windOverride);
        } else if (windSpeed >= 3.0 && windEnabled) {
          wind = 35.0 * Math.pow((windSpeed - 3.0)/9.0, 3);
          wind = Math.min(45.0, Math.max(0.0, wind));
        }

        const t1 = Math.exp(-Math.pow((hour - 8.0) / 2.0, 2));
        const t2 = Math.exp(-Math.pow((hour - 19.0) / 3.0, 2));
        const loadBase = 25.0 + 20.0 * t1 + 35.0 * t2;
        const load = loadOverride !== "" ? parseFloat(loadOverride) : loadBase + (Math.random() * 2.0 - 1.0);
        
        // Settings bounds
        const minSoc = parseFloat(settings.battery_min_soc);
        let soc = prev.Battery_SOC;
        let battPower = 0.0;
        let gridPower = 0.0;
        let emsAction = "STANDBY";
        let gridStatus = gridEnabled ? 1 : 0;
        let finalLoad = load;
        let loadSheddingLevel = 0;
        
        // Failure scenarios in simulator
        const isFanFailed = prev.active_failures?.includes("FAN_FAILURE");
        const isRunaway = prev.active_failures?.includes("BATTERY_RUNAWAY");
        const isInvFault = prev.active_failures?.includes("INVERTER_FAULT");
        
        const surplus = (solar + wind) - load;
        
        // Temperature based safety limits
        const prevTemp = prev.Battery_Temperature;
        let maxChargeRate = 50.0;
        let maxDischargeRate = 60.0;
        
        if (!batteryEnabled) {
          maxChargeRate = 0.0;
          maxDischargeRate = 0.0;
        } else if (prevTemp >= 55.0 || prevTemp <= -10.0) {
          maxChargeRate = 0.0;
          maxDischargeRate = 0.0;
        } else if (prevTemp >= 50.0) {
          maxChargeRate = 10.0;
          maxDischargeRate = 15.0;
        } else if (prevTemp >= 45.0) {
          maxChargeRate = 25.0;
          maxDischargeRate = 30.0;
        } else if (prevTemp <= 0.0) {
          maxChargeRate = 0.0;
          maxDischargeRate = 30.0;
        }

        if (isInvFault) {
          emsAction = "FAULTED";
          battPower = 0.0;
          // Renewables still supply load directly even during inverter fault (via grid tie)
          const renewableAvail = Math.min(solar + wind, load);
          gridPower = gridEnabled ? Math.max(0, load - renewableAvail) : 0.0;
        } else if (!gridEnabled) {
          // Islanding Outage Mode
          if (surplus >= 0) {
            if (soc < 95.0 && maxChargeRate > 0) {
              battPower = Math.min(surplus, maxChargeRate);
              emsAction = "ISLAND_CHARGE";
            } else {
              battPower = 0.0;
              emsAction = "ISLAND_BALANCED";
            }
          } else {
            // Deficit in islanded mode
            const deficit = Math.abs(surplus);
            // Shed load if battery is disabled or near empty
            if (soc <= 15.0 || !batteryEnabled) {
              loadSheddingLevel = 3;
              finalLoad = load * 0.15;
            } else if (soc <= 20.0) {
              loadSheddingLevel = 2;
              finalLoad = load * 0.40;
            } else if (soc <= 25.0) {
              loadSheddingLevel = 1;
              finalLoad = load * 0.70;
            }
            
            const islandSurplus = (solar + wind) - finalLoad;
            if (islandSurplus >= 0) {
              battPower = 0.0;
              emsAction = "ISLAND_BALANCED";
            } else {
              const islandDeficit = Math.abs(islandSurplus);
              if (soc > minSoc && maxDischargeRate > 0) {
                battPower = -Math.min(islandDeficit, maxDischargeRate);
                emsAction = "ISLAND_DISCHARGE";
              } else {
                battPower = 0.0;
                emsAction = "ISLAND_LOAD_SHED";
              }
            }
          }
        } else {
          // ════════════════════════════════════════════
          // GRID-CONNECTED EMS — STRICT PRIORITY ORDER
          // 1. Solar + Wind → Load (always first)
          // 2. Excess renewable → Charge Battery
          // 3. No renewable → Discharge Battery
          // 4. Battery low/unavailable → Use Grid
          // ════════════════════════════════════════════
          if (surplus >= 0) {
            // ── CASE 1 & 2: Renewables cover load, store excess in battery ──
            if (soc < 95.0 && maxChargeRate > 0) {
              battPower = Math.min(surplus, maxChargeRate);         // charge battery with surplus
              gridPower = -(surplus - battPower);          // export any remaining excess
              emsAction = "RENEWABLE_CHARGE";
            } else {
              // Battery full → export all surplus to grid
              battPower = 0.0;
              gridPower = -surplus;
              emsAction = "GRID_EXPORT";
            }
          } else {
            // ── CASE 3: Renewable deficit — use battery FIRST ──
            const deficit = Math.abs(surplus);
            if (soc > minSoc && maxDischargeRate > 0) {
              // Battery has charge → discharge to cover deficit
              const discharge = Math.min(deficit, maxDischargeRate);
              battPower = -discharge;
              gridPower = Math.max(0, deficit - discharge); // grid only covers what battery can't
              emsAction = gridPower > 0 ? "BATTERY_GRID_SUPPORT" : "BATTERY_DISCHARGE";
            } else {
              // ── CASE 4: Battery unavailable or depleted → Grid fallback ──
              battPower = 0.0;
              gridPower = deficit;
              emsAction = "GRID_FALLBACK";
            }
          }
        }

        
        // Update SOC
        const dt = 0.05;
        if (batteryEnabled) {
          if (battPower > 0) {
            soc += (battPower * 0.95 * dt) / 200.0 * 100.0;
          } else {
            soc += (battPower * (1.0/0.95) * dt) / 200.0 * 100.0;
          }
          soc = Math.max(0.0, Math.min(soc, 100.0));
        }
        
        // Heat calculations
        let temp = prev.Battery_Temperature;
        if (isRunaway) {
          temp += 1.5;
        } else if (isFanFailed) {
          temp += 0.3;
        } else {
          const dissipation = 0.05 * (temp - ambient);
          const heat = 0.001 * Math.pow(battPower, 2);
          temp += (heat - dissipation);
        }
        temp = Math.max(10.0, Math.min(temp, 65.0));

        // Sync local telemetry
        const mockTel = {
          ...prev,
          hour,
          timestamp: Date.now() / 1000,
          Solar_Power: parseFloat(solar.toFixed(2)),
          Solar_Voltage: parseFloat((solar > 0 ? 385.0 + Math.random()*10.0 : 0.0).toFixed(1)),
          Solar_Current: parseFloat((solar > 0 ? (solar * 1000)/390.0 : 0.0).toFixed(2)),
          Solar_Temperature: parseFloat((ambient + 12).toFixed(1)),
          Wind_Power: parseFloat(wind.toFixed(2)),
          Wind_Speed: parseFloat(windSpeed.toFixed(1)),
          Wind_RPM: parseFloat((wind > 0 ? 120 + wind * 9 : 0.0).toFixed(1)),
          Battery_SOC: parseFloat(soc.toFixed(2)),
          Battery_Voltage: parseFloat((320.0 + 80.0 * (soc/100.0)).toFixed(1)),
          Battery_Current: parseFloat(((battPower * 1000)/400.0).toFixed(1)),
          Battery_Temperature: parseFloat(temp.toFixed(1)),
          Battery_Fan_Status: isFanFailed ? "FAULTED" : (temp >= 35.0 ? "ON" : "OFF"),
          Load_Demand: parseFloat(finalLoad.toFixed(2)),
          Load_Voltage: parseFloat((230.2 + (Math.random() - 0.5) * 1.5).toFixed(1)),
          Load_Current: parseFloat(((finalLoad * 1000.0)/230.0).toFixed(1)),
          Grid_Power: parseFloat(gridPower.toFixed(2)),
          Grid_Voltage: parseFloat((gridEnabled ? 400.0 + (Math.random() - 0.5) * 3.0 : 0.0).toFixed(1)),
          Grid_Frequency: parseFloat((gridEnabled ? 50.0 + (Math.random() - 0.5) * 0.01 : 0.0).toFixed(3)),
          Grid_Status: gridStatus,
          Inverter_Status: isInvFault ? "FAULTED" : (battPower === 0 && solar + wind === 0 ? "STANDBY" : "RUNNING"),
          Inverter_Efficiency: parseFloat((98.2 + (Math.random() - 0.5) * 0.2).toFixed(2)),
          Inverter_Output_Power: parseFloat((finalLoad + (battPower > 0 ? battPower : 0.0)).toFixed(2)),
          ems_action: emsAction,
          electricity_cost: Math.max(0, gridPower) * (14.0 <= hour && hour <= 20.0 ? 7.50 : 4.50) / 3600.0,
          ambient_temp: parseFloat(ambient.toFixed(1))
        };

        // Local Alarms Generator
        let localAlarms = [];
        if (soc <= 15.0) {
          localAlarms.push({ id: 801, timestamp: Date.now()/1000, severity: "CRITICAL", source: "BMS",
            message: `Battery emergency low SOC: ${soc.toFixed(1)}%! Load shedding active.`, status: "ACTIVE",
            fault_code: "BMS-SOC-001",
            root_cause: "Battery State of Charge critically low (≤15%). Load shedding is now active to protect the cell stack from deep discharge damage.",
            repair_actions: ["1. Enable utility grid import if available.","2. Immediately reduce non-critical load by 30–50%.","3. Check solar and wind generation are online and producing.","4. Verify charge controller is not in fault state.","5. Do NOT disconnect battery until SOC reaches ≥25%."],
            estimated_time: "10–30 minutes", safety_warning: "⚠️ Deep discharge below 10% SOC permanently damages lithium cells. Act immediately."
          });
        } else if (soc <= 20.0) {
          localAlarms.push({ id: 802, timestamp: Date.now()/1000, severity: "WARNING", source: "BMS",
            message: `Battery low SOC: ${soc.toFixed(1)}%.`, status: "ACTIVE",
            fault_code: "BMS-SOC-002",
            root_cause: "Battery SOC approaching minimum protection threshold (≤20%). Risk of load shedding in next cycle.",
            repair_actions: ["1. Enable grid import or increase renewable generation.","2. Reduce load demand if possible.","3. Monitor SOC trend — if declining, escalate to CRITICAL response.","4. Check BMS charge parameters in settings."],
            estimated_time: "5–20 minutes", safety_warning: "⚠️ Monitor closely. SOC may drop further and trigger emergency load shedding."
          });
        }
        if (temp >= 55.0) {
          localAlarms.push({ id: 803, timestamp: Date.now()/1000, severity: "CRITICAL", source: "BMS",
            message: `CRITICAL: BESS Thermal Runaway detected! Temp: ${temp.toFixed(1)}°C!`, status: "ACTIVE",
            fault_code: "BMS-THERM-001",
            root_cause: "BESS thermal runaway threshold exceeded (≥55°C). Battery disconnected for safety.",
            repair_actions: ["1. 🚨 EMERGENCY: Evacuate battery room immediately.","2. Activate fire suppression system if smoke/fire visible.","3. Call qualified battery engineer — do NOT attempt DIY repair.","4. Keep battery isolated and disconnected until engineer arrives.","5. Check and replace cooling fans and HVAC.","6. Inspect battery cells for swelling, leakage, or discolouration.","7. Run full BMS diagnostics before reconnecting."],
            estimated_time: "2–8 hours (engineer required)", safety_warning: "🚨 CRITICAL SAFETY HAZARD. Lithium thermal runaway can cause fire."
          });
        } else if (temp >= 45.0) {
          localAlarms.push({ id: 804, timestamp: Date.now()/1000, severity: "WARNING", source: "BMS",
            message: `Battery high temperature warning: ${temp.toFixed(1)}°C.`, status: "ACTIVE",
            fault_code: "BMS-THERM-002",
            root_cause: "Battery temperature elevated (≥45°C). Charge/discharge rates have been derated.",
            repair_actions: ["1. Check battery enclosure ventilation — clear any blockages.","2. Verify cooling fans are spinning at correct RPM.","3. Reduce charge current setpoint in EMS settings temporarily.","4. Check ambient room temperature — should be ≤35°C.","5. Monitor temperature trend — if rising, prepare for BMS-THERM-001 response."],
            estimated_time: "15–60 minutes", safety_warning: "⚠️ Sustained high temperature reduces battery lifespan."
          });
        }
        if (isInvFault) {
          localAlarms.push({ id: 805, timestamp: Date.now()/1000, severity: "CRITICAL", source: "Inverter",
            message: "Inverter system fault: Overcurrent trip.", status: "ACTIVE",
            fault_code: "INV-FAULT-001",
            root_cause: "Inverter overcurrent protection tripped. DC or AC bus current exceeded safe operating limits.",
            repair_actions: ["1. Disconnect AC and DC sides of inverter using isolation breakers.","2. Wait 5 minutes for capacitors to discharge fully.","3. Inspect AC output terminals for short circuits or loose wiring.","4. Check DC bus fuses — replace if blown.","5. Verify load demand has not spiked beyond inverter rating.","6. Reset inverter via front panel or SCADA reset command.","7. Reconnect and monitor output current for 10 minutes."],
            estimated_time: "20–45 minutes", safety_warning: "⚠️ Always isolate both AC and DC sides before inspection. Inverter capacitors retain lethal voltage."
          });
        }
        // Fingerprint-guarded alarm update — only triggers re-render if alarms actually changed
        const newFingerprint = localAlarms.map(a => `${a.id}:${a.severity}`).join('|');
        if (newFingerprint !== alarmFingerprint.current) {
          alarmFingerprint.current = newFingerprint;
          setActiveAlarms(localAlarms);
        }


        // Update local mock protocols
        setProtocolData({
          can: `ID: 0x18F009A1 | DLC: 8 | DATA: ${Math.round(soc).toString(16).toUpperCase().padStart(2, '0')} 0E A1 C3 84 ${Math.round(temp + 40).toString(16).toUpperCase().padStart(2, '0')} FF FE`,
          modbus: {
            40001: Math.round(solar * 10),
            40002: Math.round(wind * 10),
            40003: Math.round(soc * 100),
            40004: Math.round(mockTel.Inverter_Output_Power * 10) + 32768,
            40005: settings.export_enabled === "true" ? 1 : 0,
            40006: Math.round(minSoc),
            40007: Math.round((temp + 50.0) * 10),
            40008: mockTel.load_shedding_level,
            40009: localAlarms.length,
            40010: Math.round(mockTel.Inverter_Efficiency * 100)
          },
          opc: {
            "ns=2;s=Microgrid.Solar.Voltage": mockTel.Solar_Voltage,
            "ns=2;s=Microgrid.Solar.Current": mockTel.Solar_Current,
            "ns=2;s=Microgrid.Wind.Speed": mockTel.Wind_Speed,
            "ns=2;s=Microgrid.BESS.SOH": Math.round(mockTel.Battery_SOH),
            "ns=2;s=Microgrid.Load.Demand": mockTel.Load_Demand,
            "ns=2;s=Microgrid.Grid.Frequency": mockTel.Grid_Frequency,
            "ns=2;s=Microgrid.BESS.Temperature": mockTel.Battery_Temperature,
            "ns=2;s=Microgrid.Inverter.Efficiency": mockTel.Inverter_Efficiency,
            "ns=2;s=Microgrid.EMS.LoadSheddingLevel": mockTel.load_shedding_level,
            "ns=2;s=Microgrid.EMS.AlarmCount": localAlarms.length
          },
          iec61850: {
            "Grid_XCBR1.Pos.stVal": mockTel.Grid_Status === 1 ? 1 : 2,
            "Grid_XCBR1.Pos.q": "Good",
            "Inverter_MMXU1.TotW.mag.f": mockTel.Inverter_Output_Power,
            "Inverter_MMXU1.TotV.mag.f": mockTel.Grid_Voltage,
            "Inverter_MMXU1.TotHz.mag.f": mockTel.Grid_Frequency
          }
        });
        
        return mockTel;
      });
    }, 1000);

    return () => clearInterval(simInterval);
  }, [isConnected, settings, solarEnabled, windEnabled, batteryEnabled, gridEnabled, solarOverride, windOverride, loadOverride]);

  // Poll assets status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/assets/status`);
        const data = await res.json();
        if (data) setAssetsState(data);
      } catch (e) {
        console.error("Error fetching assets status", e);
      }
    };

    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
    }, 2000);

    return () => clearInterval(interval);
  }, [API_BASE]);

  const handleConnectAsset = async (asset, protocol) => {
    try {
      await fetch(`${API_BASE}/api/assets/${asset}/protocol`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`
        },
        body: JSON.stringify({ protocol })
      });

      const res = await fetch(`${API_BASE}/api/assets/${asset}/connect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });
      const data = await res.json();
      if (data.state) {
        setAssetsState(prev => ({ ...prev, [asset]: data.state }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDisconnectAsset = async (asset) => {
    try {
      const res = await fetch(`${API_BASE}/api/assets/${asset}/disconnect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });
      const data = await res.json();
      if (data.state) {
        setAssetsState(prev => ({ ...prev, [asset]: data.state }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartCollection = async (asset) => {
    try {
      const res = await fetch(`${API_BASE}/api/assets/${asset}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });
      const data = await res.json();
      if (data.state) {
        setAssetsState(prev => ({ ...prev, [asset]: data.state }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStopCollection = async (asset) => {
    try {
      const res = await fetch(`${API_BASE}/api/assets/${asset}/stop`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });
      const data = await res.json();
      if (data.state) {
        setAssetsState(prev => ({ ...prev, [asset]: data.state }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const connectWS = () => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : `${window.location.hostname}:8000`;
    
    ws.current = new WebSocket(`${protocol}//${host}/ws`);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connection established");
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.telemetry) setTelemetry(data.telemetry);
        if (data.alarms) setActiveAlarms(data.alarms);
        if (data.protocols) setProtocolData(data.protocols);
        if (data.assets_state) setAssetsState(data.assets_state);
      } catch (err) {
        console.error("Error parsing socket frame:", err);
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected. Retrying in 3s...");
      setTimeout(connectWS, 3000);
    };
  };

  const fetchTelemetryREST = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tags`);
      const data = await res.json();
      if (data && data.Solar_Power !== undefined) {
        setTelemetry(data);
        setIsConnected(true);
      }
      
      const alarmRes = await fetch(`${API_BASE}/api/alarms`);
      const alarmData = await alarmRes.json();
      if (alarmData.active) setActiveAlarms(alarmData.active);

      const protoRes = await fetch(`${API_BASE}/api/protocols`);
      const protoData = await protoRes.json();
      setProtocolData({
        modbus: protoData.modbus_registers,
        opc: protoData.opc_nodes,
        can: protoData.can_bus_bms,
        iec61850: protoData.iec61850_nodes
      });
    } catch (e) {
      setIsConnected(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (e) {
      console.warn("Rest API offline. Operating in fallback simulator mode.");
    }
  };

  const fetchForecast = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/forecast`);
      if (res.ok) {
        const data = await res.json();
        setForecastData(data);
      }
    } catch (e) {
      // Offline fallback: generate mock forecasts
      const hour = telemetry.hour;
      const forecasts = [];
      for (let i = 0; i < 24; i++) {
        const fHour = (hour + i) % 24;
        let sol = 0;
        if (6 <= fHour && fHour <= 18) {
          sol = 80 * Math.sin(Math.PI * (fHour - 6)/12);
        }
        const wnd = 15.0 + 5.0 * Math.sin(2 * Math.PI * (fHour - 2)/24);
        const t1 = Math.exp(-Math.pow((fHour - 8) / 2, 2));
        const t2 = Math.exp(-Math.pow((fHour - 19) / 3, 2));
        const ld = 25 + 20 * t1 + 35 * t2;
        forecasts.push({
          time: fHour,
          solar: parseFloat(sol.toFixed(1)),
          wind: parseFloat(wnd.toFixed(1)),
          load: parseFloat(ld.toFixed(1)),
          tariff: 14.0 <= fHour && fHour <= 20.0 ? 7.50 : 4.50
        });
      }
      setForecastData(forecasts);
    }
  };

  const fetchForecastExtended = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/forecast-extended`);
      if (res.ok) {
        const data = await res.json();
        setForecastExtended(data);
      }
    } catch (e) {
      // offline fallback
      const forecasts = [];
      let soc = telemetry.Battery_SOC;
      for (let i = 0; i < 24; i++) {
        const fHour = (telemetry.hour + i) % 24;
        let sol = 0;
        if (6 <= fHour && fHour <= 18) {
          sol = 80 * Math.sin(Math.PI * (fHour - 6)/12);
        }
        const wnd = 20;
        const ld = 35;
        const surplus = sol + wnd - ld;
        let bPow = 0;
        if (surplus > 0) {
          bPow = Math.min(surplus, 30);
          soc = Math.min(95, soc + bPow * 0.15);
        } else {
          bPow = Math.max(surplus, -40);
          soc = Math.max(20, soc + bPow * 0.15);
        }
        forecasts.push({
          hour_index: i,
          hour: Math.round(fHour),
          solar: parseFloat(sol.toFixed(1)),
          wind: wnd,
          load: ld,
          battery_soc: parseFloat(soc.toFixed(1)),
          battery_power: parseFloat(bPow.toFixed(1)),
          grid_power: parseFloat((-(surplus - bPow)).toFixed(1))
        });
      }
      setForecastExtended(forecasts);
    }
  };

  const fetchHistorical = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/historical?limit=30`);
      if (res.ok) {
        const data = await res.json();
        setHistoricalData(data);
      }
    } catch (e) {
      console.warn("Could not retrieve historical database logs.");
    }
  };

  const fetchCarbonAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/carbon-analytics`);
      if (res.ok) {
        const data = await res.json();
        setCarbonMetrics(data);
      }
    } catch (e) {
      // calculate offline estimate
      const renewableTotal = telemetry.Solar_Power + telemetry.Wind_Power;
      setCarbonMetrics(prev => {
        const added = renewableTotal * (1.0 / 3600.0) * 0.45;
        return {
          co2_saved_kg: prev.co2_saved_kg + added,
          renewable_share_pct: telemetry.Load_Demand > 0 ? Math.min(100.0, ((telemetry.Solar_Power + telemetry.Wind_Power)/telemetry.Load_Demand)*100.0) : 100.0,
          grid_import_kwh: prev.grid_import_kwh + Math.max(0, telemetry.Grid_Power) / 3600.0,
          carbon_offset_rate: 0.45
        };
      });
    }
  };

  // Poll status indices & status check
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/status`);
        if (res.ok) {
          const data = await res.json();
          setSimulationMode(data.simulation_mode);
          setReplayActive(data.replay_active);
          if (data.section_dataset_sizes) setSectionSizes(data.section_dataset_sizes);
          if (data.section_indices) setSectionIndices(data.section_indices);
          if (data.solar_enabled !== undefined) setSolarEnabled(data.solar_enabled);
          if (data.wind_enabled !== undefined) setWindEnabled(data.wind_enabled);
          if (data.battery_enabled !== undefined) setBatteryEnabled(data.battery_enabled);
          if (data.grid_enabled !== undefined) setGridEnabled(data.grid_enabled);
          if (data.fan_override !== undefined) setFanOverride(data.fan_override);
        }
      } catch (e) {
        // local polling
      }
    };
    pollStatus();
    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  // Update carbon analytics periodically
  useEffect(() => {
    const interval = setInterval(fetchCarbonAnalytics, 10000);
    return () => clearInterval(interval);
  }, [telemetry]);

  // Handle settings config save (locked to Admins)
  const saveSetting = async (key, val) => {
    if (userRole !== 'admin') {
      alert("UNAUTHORIZED: Only users with 'admin' credentials can edit EMS parameters!");
      return;
    }
    
    // Save locally
    setSettings(prev => ({ ...prev, [key]: val }));

    try {
      await fetch(`${API_BASE}/api/settings`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({ key, value: val })
      });
      fetchSettings();
    } catch (e) {
      console.warn("Settings saved locally. Server endpoint unreachable.");
    }
  };

  // Handle toggles immediately
  const handleComponentToggle = async (component, enabledValue) => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only operators with 'engineer' or 'admin' credentials can toggle grid components!");
      return;
    }

    let nextSolar = solarEnabled;
    let nextWind = windEnabled;
    let nextBattery = batteryEnabled;
    let nextGrid = gridEnabled;

    if (component === 'solar') { setSolarEnabled(enabledValue); nextSolar = enabledValue; }
    if (component === 'wind') { setWindEnabled(enabledValue); nextWind = enabledValue; }
    if (component === 'battery') { setBatteryEnabled(enabledValue); nextBattery = enabledValue; }
    if (component === 'grid') { setGridEnabled(enabledValue); nextGrid = enabledValue; }

    const payload = {
      simulation_mode: simulationMode,
      solar_override: solarOverride !== "" ? parseFloat(solarOverride) : null,
      wind_override: windOverride !== "" ? parseFloat(windOverride) : null,
      load_override: loadOverride !== "" ? parseFloat(loadOverride) : null,
      solar_enabled: nextSolar,
      wind_enabled: nextWind,
      battery_enabled: nextBattery,
      grid_enabled: nextGrid,
      fan_override: fanOverride
    };

    try {
      const res = await fetch(`${API_BASE}/api/control`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        alert(`Feeder control failed: ${errorData.detail || 'Access Denied'}`);
        // Revert local UI state
        if (component === 'solar') setSolarEnabled(!enabledValue);
        if (component === 'wind') setWindEnabled(!enabledValue);
        if (component === 'battery') setBatteryEnabled(!enabledValue);
        if (component === 'grid') setGridEnabled(!enabledValue);
      }
    } catch (e) {
      console.warn("Component toggled locally. Server unreachable.");
    }
  };

  const handleFanOverrideToggle = async (overrideValue) => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only operators with 'engineer' or 'admin' credentials can override cooling fan settings!");
      return;
    }

    const previousOverride = fanOverride;
    setFanOverride(overrideValue);

    const payload = {
      simulation_mode: simulationMode,
      solar_override: solarOverride !== "" ? parseFloat(solarOverride) : null,
      wind_override: windOverride !== "" ? parseFloat(windOverride) : null,
      load_override: loadOverride !== "" ? parseFloat(loadOverride) : null,
      solar_enabled: solarEnabled,
      wind_enabled: windEnabled,
      battery_enabled: batteryEnabled,
      grid_enabled: gridEnabled,
      fan_override: overrideValue
    };

    try {
      const res = await fetch(`${API_BASE}/api/control`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        alert(`Fan control failed: ${errorData.detail || 'Access Denied'}`);
        setFanOverride(previousOverride);
      }
    } catch (e) {
      console.warn("Fan override toggled locally. Server unreachable.");
    }
  };

  // Handle overrides (Engineer or Admin)
  const applyOverrides = async () => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only users with 'engineer' or 'admin' credentials can force overrides!");
      return;
    }

    const payload = {
      simulation_mode: simulationMode,
      solar_override: solarOverride !== "" ? parseFloat(solarOverride) : null,
      wind_override: windOverride !== "" ? parseFloat(windOverride) : null,
      load_override: loadOverride !== "" ? parseFloat(loadOverride) : null,
      solar_enabled: solarEnabled,
      wind_enabled: windEnabled,
      battery_enabled: batteryEnabled,
      grid_enabled: gridEnabled
    };

    try {
      const res = await fetch(`${API_BASE}/api/control`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errorText = await res.json();
        alert(`Server Error: ${errorText.detail}`);
      }
    } catch (e) {
      // offline simulation mode switch
      setTelemetry(prev => ({
        ...prev,
        active_failures: simulationMode === "FAULT" ? ["INVERTER_FAULT"] : []
      }));
      alert(`Simulation Mode applied locally: ${simulationMode}`);
    }
  };

  const resetOverrides = async () => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only users with 'engineer' or 'admin' credentials can clear overrides!");
      return;
    }
    setSolarOverride("");
    setWindOverride("");
    setLoadOverride("");
    setSimulationMode("NORMAL");
    try {
      await fetch(`${API_BASE}/api/control`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({
          simulation_mode: "NORMAL",
          solar_override: null,
          wind_override: null,
          load_override: null,
          solar_enabled: true,
          wind_enabled: true,
          battery_enabled: true,
          grid_enabled: true
        })
      });
    } catch (e) {
      console.warn("Overrides reset locally. Server unreachable.");
    }
  };

  const ingestLiveData = async () => {
    if (userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator') {
      alert("UNAUTHORIZED: Only users with 'operator', 'engineer' or 'admin' credentials can ingest live data!");
      return;
    }

    const payload = {
      solar_power: parseFloat(liveSolar) || 0.0,
      wind_power: parseFloat(liveWind) || 0.0,
      battery_temp: parseFloat(liveBatteryTemp) || 25.0,
      battery_current: parseFloat(liveBatteryCurrent) || 0.0,
      load_demand: parseFloat(liveLoadDemand) || 0.0,
      grid_power: parseFloat(liveGridPower) || 0.0,
      grid_status: parseInt(liveGridStatus) === 0 ? 0 : 1,
      battery_soc: liveBatterySOC !== "" ? parseFloat(liveBatterySOC) : null,
      battery_voltage: liveBatteryVoltage !== "" ? parseFloat(liveBatteryVoltage) : null
    };

    try {
      const res = await fetch(`${API_BASE}/api/live-data`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const respData = await res.json();
        setTelemetry(respData.telemetry);
        setSimulationMode("LIVE");
      } else {
        const errorText = await res.json();
        alert(`Server Ingestion Error: ${errorText.detail}`);
      }
    } catch (e) {
      setTelemetry(prev => {
        const temp = parseFloat(liveBatteryTemp) || 25.0;
        const volt = liveBatteryVoltage !== "" ? parseFloat(liveBatteryVoltage) : (320.0 + 80.0 * ((liveBatterySOC !== "" ? parseFloat(liveBatterySOC) : prev.Battery_SOC)/100.0));
        const soc = liveBatterySOC !== "" ? parseFloat(liveBatterySOC) : prev.Battery_SOC;
        const solar = parseFloat(liveSolar) || 0.0;
        const wind = parseFloat(liveWind) || 0.0;
        const load = parseFloat(liveLoadDemand) || 0.0;
        const grid = parseFloat(liveGridPower) || 0.0;
        const curr = parseFloat(liveBatteryCurrent) || 0.0;
        const isGrid = parseInt(liveGridStatus) === 0 ? 0 : 1;
        
        return {
          ...prev,
          hour: (new Date().getHours() + new Date().getMinutes()/60.0),
          timestamp: Date.now() / 1000,
          Solar_Power: solar,
          Solar_Voltage: solar > 0 ? 385.0 : 0.0,
          Solar_Current: solar > 0 ? (solar * 1000)/385.0 : 0.0,
          Wind_Power: wind,
          Wind_RPM: wind > 0 ? 300.0 : 0.0,
          Battery_SOC: soc,
          Battery_Voltage: volt,
          Battery_Current: curr,
          Battery_Temperature: temp,
          Load_Demand: load,
          Grid_Power: grid,
          Grid_Status: isGrid,
          Inverter_Output_Power: Math.max(0.0, load - grid),
          ems_action: "LIVE_EXTERNAL_PUSH"
        };
      });
      setSimulationMode("LIVE");
      alert("Ingested live data locally in Offline Mode.");
    }
  };

  // Acknowledge Alarms (Operator, Engineer, Admin)
  const ackAlarm = async (id) => {
    if (userRole === 'viewer') {
      alert("UNAUTHORIZED: Viewer role cannot acknowledge alarms!");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/alarms/acknowledge`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({ alarm_id: id })
      });
      if (res.ok) {
        fetchTelemetryREST();
      }
    } catch (e) {
      // offline ack
      setActiveAlarms(prev => prev.map(a => a.id === id ? { ...a, status: 'ACKNOWLEDGED' } : a));
    }
  };

  const clearAlarm = async (id) => {
    if (userRole === 'viewer') {
      alert("UNAUTHORIZED: Viewer role cannot clear alarms!");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/alarms/clear`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({ alarm_id: id })
      });
      if (res.ok) {
        fetchTelemetryREST();
      }
    } catch (e) {
      // offline clear
      setActiveAlarms(prev => prev.filter(a => a.id !== id));
    }
  };

  const repairAlarm = async (id) => {
    if (userRole === 'viewer') {
      alert("UNAUTHORIZED: Viewer role cannot repair/resolve alarms!");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/alarms/repair`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({ alarm_id: id })
      });
      if (res.ok) {
        fetchTelemetryREST();
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(`Self-repair failed: ${errorData.detail || 'Access Denied'}`);
      }
    } catch (e) {
      // offline repair fallback
      setActiveAlarms(prev => prev.filter(a => a.id !== id));
    }
  };

  // Trigger Digital Twin Simulated Failures (Engineer or Admin)
  const handleSimulateFailure = async (type, active) => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only 'engineer' or 'admin' roles can inject digital twin hardware failures!");
      return;
    }
    
    // Apply locally
    setTelemetry(prev => {
      const failures = prev.active_failures ? [...prev.active_failures] : [];
      if (active) {
        if (!failures.includes(type)) failures.push(type);
      } else {
        const idx = failures.indexOf(type);
        if (idx !== -1) failures.splice(idx, 1);
      }
      return { ...prev, active_failures: failures };
    });

    try {
      await fetch(`${API_BASE}/api/twin/simulate-failure`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${userToken}`
        },
        body: JSON.stringify({ failure_type: type, active })
      });
    } catch (e) {
      console.warn("Digital twin failure injected locally.");
    }
  };

  // User login/role selector processing
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: usernameInput, password: passwordInput })
      });
      const data = await res.json();
      if (res.ok) {
        setUserRole(data.role);
        setUserToken(data.token);
        localStorage.setItem('role', data.role);
        localStorage.setItem('token', data.token);
        setShowLoginModal(false);
        setUsernameInput('');
        setPasswordInput('');
      } else {
        setLoginError(data.detail || "Authentication failed");
      }
    } catch (err) {
      // offline login fallback
      const valid = ["admin", "operator", "engineer", "viewer"];
      const user = usernameInput.toLowerCase();
      if (valid.includes(user) && passwordInput === user) {
        setUserRole(user);
        setUserToken(`mock-jwt-token-${user}-${Date.now()}`);
        localStorage.setItem('role', user);
        localStorage.setItem('token', `mock-jwt-token-${user}-${Date.now()}`);
        setShowLoginModal(false);
        setLoginError('');
        setUsernameInput('');
        setPasswordInput('');
      } else {
        setLoginError("Invalid offline credentials. Hint: use 'admin' as both username & password.");
      }
    }
  };

  const handleLogout = () => {
    setUserRole('viewer');
    setUserToken('');
    localStorage.removeItem('role');
    localStorage.removeItem('token');
  };

  // Handle file dataset uploads (Engineer, Admin)
  const uploadSectionDataset = async (section, file) => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only 'engineer' or 'admin' roles can upload Replay datasets!");
      return;
    }
    if (!file) return;
    
    setUploadingSections(prev => ({ ...prev, [section]: true }));
    setUploadMsgs(prev => ({ ...prev, [section]: "" }));
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await fetch(`${API_BASE}/api/upload-dataset/${section}`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        if (section === "master") {
          ["solar", "wind", "battery", "inverter", "load", "grid", "master"].forEach(sec => {
            setUploadMsgs(prev => ({ ...prev, [sec]: `Parsed ${data.replay_dataset_size} rows.` }));
            setSectionSizes(prev => ({ ...prev, [sec]: data.replay_dataset_size }));
          });
        } else {
          setUploadMsgs(prev => ({ ...prev, [section]: `Parsed ${data.replay_dataset_size} rows.` }));
          setSectionSizes(prev => ({ ...prev, [section]: data.replay_dataset_size }));
        }
        setReplayActive(true);
        setSimulationMode("REPLAY");
      } else {
        setUploadMsgs(prev => ({ ...prev, [section]: `Error: ${data.detail}` }));
      }
    } catch (err) {
      setUploadMsgs(prev => ({ ...prev, [section]: `Err: ${err.message}` }));
    } finally {
      setUploadingSections(prev => ({ ...prev, [section]: false }));
    }
  };

  const toggleReplayState = async () => {
    if (userRole !== 'admin' && userRole !== 'engineer') {
      alert("UNAUTHORIZED: Only 'engineer' or 'admin' roles can toggle Replay states!");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/toggle-replay`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        setReplayActive(data.replay_active);
        setSimulationMode(data.replay_active ? "REPLAY" : "NORMAL");
      } else {
        alert(data.detail);
      }
    } catch (err) {
      setReplayActive(!replayActive);
    }
  };

  const [showLegends, setShowLegends] = useState(true);
  const [showFlowArrows, setShowFlowArrows] = useState(true);
  const [cumulativeEnergy, setCumulativeEnergy] = useState(() => {
    try {
      const saved = localStorage.getItem('scada_cumulative_energy');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return {
      solar: 80519.40,
      wind: 124503.20,
      battery: 45210.85,
      inverter: 215430.60,
      grid: 98124.50,
      grid_export: 34125.20,
      load: 310540.15
    };
  });

  useEffect(() => {
    try {
      localStorage.setItem('scada_cumulative_energy', JSON.stringify(cumulativeEnergy));
    } catch (e) {}
  }, [cumulativeEnergy]);

  // Live Chart data collection
  const [liveChartData, setLiveChartData] = useState([]);
  useEffect(() => {
    if (telemetry.timestamp) {
      setLiveChartData(prev => {
        const timeStr = new Date(telemetry.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const updated = [
          ...prev,
          {
            time: timeStr,
            solar: telemetry.Solar_Power,
            wind: telemetry.Wind_Power,
            load: telemetry.Load_Demand,
            battery: telemetry.Battery_SOC,
            grid: telemetry.Grid_Power
          }
        ];
        if (updated.length > 30) {
          updated.shift();
        }
        return updated;
      });

      // Update historicalData dynamically so the faceplate charts also update in real-time!
      setHistoricalData(prev => {
        // Prevent duplicate timestamps
        if (prev.length > 0 && prev[prev.length - 1].timestamp === telemetry.timestamp) {
          return prev;
        }
        const updated = [
          ...prev,
          {
            timestamp: telemetry.timestamp,
            solar_power: telemetry.Solar_Power,
            solar_voltage: telemetry.Solar_Voltage,
            solar_current: telemetry.Solar_Current,
            solar_temperature: telemetry.Solar_Temperature,
            wind_power: telemetry.Wind_Power,
            wind_speed: telemetry.Wind_Speed,
            wind_rpm: telemetry.Wind_RPM,
            battery_soc: telemetry.Battery_SOC,
            battery_voltage: telemetry.Battery_Voltage,
            battery_current: telemetry.Battery_Current,
            battery_temperature: telemetry.Battery_Temperature,
            inverter_output_power: telemetry.Inverter_Output_Power,
            grid_power: telemetry.Grid_Power,
            grid_voltage: telemetry.Grid_Voltage,
            grid_frequency: telemetry.Grid_Frequency,
            load_demand: telemetry.Load_Demand,
            load_voltage: telemetry.Load_Voltage,
            load_current: telemetry.Load_Current
          }
        ];
        // Keep the last 50 points for rich historical view
        if (updated.length > 50) {
          updated.shift();
        }
        return updated;
      });

      // Accumulate cumulative energy dynamically (in kWh, scaled assuming 1 telemetry event = ~1 second)
      setCumulativeEnergy(prev => ({
        solar: prev.solar + (telemetry.Solar_Power > 0 ? (telemetry.Solar_Power * 1 / 3600.0) : 0),
        wind: prev.wind + (telemetry.Wind_Power > 0 ? (telemetry.Wind_Power * 1 / 3600.0) : 0),
        battery: prev.battery + (Math.abs(telemetry.Battery_Voltage * telemetry.Battery_Current / 1000) * 1 / 3600.0),
        inverter: prev.inverter + (Math.abs(telemetry.Inverter_Output_Power) * 1 / 3600.0),
        grid: prev.grid + (Math.abs(telemetry.Grid_Power) * 1 / 3600.0),
        grid_export: (prev.grid_export || 0) + (telemetry.Grid_Power < 0 ? (Math.abs(telemetry.Grid_Power) * 1 / 3600.0) : 0),
        load: prev.load + (telemetry.Load_Demand * 1 / 3600.0)
      }));
    }
  }, [telemetry]);

  // Pre-seed chart with 20 initial simulated points so it's never blank on load
  useEffect(() => {
    const now = Date.now() / 1000;
    const seed = [];
    for (let i = 20; i >= 0; i--) {
      const h = ((new Date().getHours()) + (new Date().getMinutes() / 60) - i * (30 / 3600)) % 24;
      const hPos = ((h % 24) + 24) % 24;
      const sol = hPos >= 6 && hPos <= 18 ? Math.max(0, 85 * Math.sin(Math.PI * (hPos - 6) / 12) * 0.85) : 0;
      const wnd = Math.max(0, 12 + 8 * Math.sin(2 * Math.PI * hPos / 24));
      const ld = 25 + 20 * Math.exp(-Math.pow((hPos - 8) / 2, 2)) + 35 * Math.exp(-Math.pow((hPos - 19) / 3, 2));
      const grd = ld - sol - wnd;
      const t = new Date((now - i * 3) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      seed.push({ time: t, solar: parseFloat(sol.toFixed(2)), wind: parseFloat(wnd.toFixed(2)), load: parseFloat(ld.toFixed(2)), battery: 65, grid: parseFloat(grd.toFixed(2)) });
    }
    setLiveChartData(seed);
  }, []);

  // Calculate where the load gets its power
  const calculateLoadSourceBreakdown = () => {
    const load = telemetry.Load_Demand || 0.001; // Avoid division by zero
    const solar = telemetry.Solar_Power || 0;
    const wind = telemetry.Wind_Power || 0;
    const gridImport = telemetry.Grid_Power > 0 ? telemetry.Grid_Power : 0;
    const batteryDischarge = (telemetry.Battery_Current && telemetry.Battery_Current < 0) 
      ? -((telemetry.Battery_Voltage * telemetry.Battery_Current) / 1000.0) 
      : 0;

    const totalAvailable = solar + wind + gridImport + batteryDischarge;
    
    if (totalAvailable <= 0) {
      return {
        solarPct: 0,
        windPct: 0,
        batteryPct: 0,
        gridPct: gridEnabled ? 100 : 0,
        solarKw: 0,
        windKw: 0,
        batteryKw: 0,
        gridKw: gridEnabled ? load : 0
      };
    }

    // Calculate fractions based on generation mix
    const solarShare = solar / totalAvailable;
    const windShare = wind / totalAvailable;
    const batteryShare = batteryDischarge / totalAvailable;
    const gridShare = gridImport / totalAvailable;

    // Distribute the actual load demand according to these shares
    const solarKw = Math.min(solar, load * solarShare);
    const windKw = Math.min(wind, load * windShare);
    const batteryKw = Math.min(batteryDischarge, load * batteryShare);
    const gridKw = Math.max(0, load - solarKw - windKw - batteryKw); // Grid balances the rest

    const solarPct = (solarKw / load) * 100;
    const windPct = (windKw / load) * 100;
    const batteryPct = (batteryKw / load) * 100;
    const gridPct = (gridKw / load) * 100;

    return {
      solarPct: Math.round(solarPct),
      windPct: Math.round(windPct),
      batteryPct: Math.round(batteryPct),
      gridPct: Math.round(gridPct),
      solarKw: parseFloat(solarKw.toFixed(2)),
      windKw: parseFloat(windKw.toFixed(2)),
      batteryKw: parseFloat(batteryKw.toFixed(2)),
      gridKw: parseFloat(gridKw.toFixed(2))
    };
  };

  // Load Feeder Power Status — determines if load is fully/partially/un-supplied
  const getLoadPowerStatus = () => {
    const demand = telemetry.Load_Demand || 0;
    if (demand <= 0) return 'powered'; // No demand = no issue
    const solar = telemetry.Solar_Power || 0;
    const wind = telemetry.Wind_Power || 0;
    const gridImport = telemetry.Grid_Power > 0 ? telemetry.Grid_Power : 0;
    const batteryDischarge = (telemetry.Battery_Current && telemetry.Battery_Current < 0)
      ? -((telemetry.Battery_Voltage * telemetry.Battery_Current) / 1000.0)
      : 0;
    const totalSupply = solar + wind + gridImport + batteryDischarge;
    const ratio = totalSupply / demand;
    if (ratio >= 0.95) return 'powered';   // ≥95% supplied → green
    if (ratio >= 0.5)  return 'partial';   // 50–95% supplied → amber
    return 'unsupplied';                   // <50% supplied → red
  };
  const loadPowerStatus = getLoadPowerStatus();

  // Faceplate Modal descriptors
  const getFaceplateDetails = () => {
    if (!activeFaceplate) return null;
    
    switch (activeFaceplate) {
      case 'solar':
        const solarGenerating = telemetry.Solar_Power > 0;
        return {
          title: "Solar PV Array Details",
          icon: <Sun className="w-6 h-6 text-yellow-400" />,
          statusText: solarGenerating ? "STATUS: GENERATING" : "STATUS: STANDBY (NIGHT)",
          statusClass: solarGenerating ? "green" : "warning",
          metrics: [
            { label: "Array Output Power", value: telemetry.Solar_Power.toFixed(2), unit: "kW" },
            { label: "MPPT DC Voltage", value: telemetry.Solar_Voltage.toFixed(1), unit: "V" },
            { label: "Solar DC Current", value: telemetry.Solar_Current.toFixed(2), unit: "A" },
            { label: "Module Temperature", value: telemetry.Solar_Temperature.toFixed(1), unit: "°C" },
            { label: "Solar Irradiance", value: (telemetry.Solar_Power * 12.5).toFixed(0), unit: "W/m²" },
            { label: "PV Cell Health (SOH)", value: "94.2", unit: "%" },
          ],
          extraMetric: { label: "MPPT Converter Efficiency", value: "99.1", unit: "%", className: "text-emerald-400 font-bold" },
          assets: [
            { name: "Manufacturer", val: "Apex Solar Tech" },
            { name: "Model", val: "APX-Mono-540W-Bifacial" },
            { name: "Installed Capacity", val: "80.0 kWp" },
            { name: "Cell Technology", val: "Monocrystalline PERC" },
            { name: "Degradation Index", val: "0.55% / Year" },
            { name: "Installation Date", val: "2024-04-12" },
          ]
        };
      case 'wind':
        const windGenerating = telemetry.Wind_Power > 0;
        return {
          title: "Wind Turbine Details",
          icon: <Wind className="w-6 h-6 text-purple-400" />,
          statusText: windGenerating ? "STATUS: GENERATING" : "STATUS: STANDBY (CALM)",
          statusClass: windGenerating ? "green" : "warning",
          metrics: [
            { label: "Turbine Power Output", value: telemetry.Wind_Power.toFixed(2), unit: "kW" },
            { label: "Rotor Speed", value: telemetry.Wind_RPM, unit: "RPM" },
            { label: "Wind Speed", value: telemetry.Wind_Speed.toFixed(1), unit: "m/s" },
            { label: "Cp (Power Coefficient)", value: "0.42", unit: "" },
            { label: "Generator Temp", value: (38.5 + telemetry.Wind_Power * 0.12).toFixed(1), unit: "°C" },
            { label: "Mechanical SOH", value: "96.8", unit: "%" },
          ],
          extraMetric: { label: "Converter Efficiency", value: "94.5", unit: "%", className: "text-emerald-400 font-bold" },
          assets: [
            { name: "Manufacturer", val: "AeroWind Systems" },
            { name: "Model", val: "DMSG-1.5MW-VarPitch" },
            { name: "Blade Diameter", val: "22.5 meters" },
            { name: "Generator Type", val: "Direct Drive PM Sync" },
            { name: "Cut-in Wind Speed", val: "2.5 m/s" },
            { name: "Pitch Mechanism", val: "Hydraulic Active Pitch" },
          ]
        };
      case 'battery':
        const batPower = (telemetry.Battery_Voltage * telemetry.Battery_Current / 1000).toFixed(2);
        const batMode = telemetry.Battery_Current > 0 ? "charging" : telemetry.Battery_Current < 0 ? "discharging" : "standby";
        let batStatusText = "STATUS: STANDBY";
        let batStatusClass = "warning";
        if (batMode === "charging") {
          batStatusText = "STATUS: CHARGING";
          batStatusClass = "green";
        } else if (batMode === "discharging") {
          batStatusText = "STATUS: DISCHARGING";
          batStatusClass = "green";
        }
        return {
          title: "Battery BESS Details",
          icon: <Battery className="w-6 h-6 text-emerald-400" />,
          statusText: batStatusText,
          statusClass: batStatusClass,
          metrics: [
            { label: "Active Power (DC)", value: batPower, unit: "kW" },
            { label: "State of Charge (SOC)", value: telemetry.Battery_SOC.toFixed(1), unit: "%" },
            { label: "Pack DC Voltage", value: telemetry.Battery_Voltage.toFixed(1), unit: "V" },
            { label: "Pack DC Current", value: telemetry.Battery_Current.toFixed(1), unit: "A" },
            { label: "BESS Temperature", value: telemetry.Battery_Temperature.toFixed(1), unit: "°C" },
            { label: "State of Health (SOH)", value: Math.round(telemetry.Battery_SOH).toString(), unit: "%" },
            { label: "Battery Cycle Count", value: "142", unit: "cycles" },
            { label: "Internal Resistance", value: "12.4", unit: "mΩ" },
          ],
          extraMetric: { label: "Round-Trip Efficiency", value: "95.0", unit: "%", className: "text-emerald-400 font-bold" },
          assets: [
            { name: "Chemistry", val: "Lithium Iron Phosphate (LFP)" },
            { name: "Nominal Capacity", val: "200 kWh" },
            { name: "Power Rating", val: "100 kW Continuous" },
            { name: "Cell Config", val: "120S 4P Rack System" },
            { name: "BMS Controller", val: "BMS-SAE-J1939 v2.4" },
            { name: "Cooling Fan Status", val: telemetry.Battery_Fan_Status === "FAULTED" ? "FAULTED (Locked Rotor)" : telemetry.Battery_Fan_Status === "ON" ? "ON (Active Cooling)" : "OFF (Standby)" },
            { name: "Thermal Management", val: "Forced Air Cooling (Dual Fan)" },
          ]
        };
      case 'inverter':
        const invFaulted = telemetry.Inverter_Status === "FAULTED";
        return {
          title: "Hybrid PCS Inverter Details",
          icon: <Cpu className="w-6 h-6 text-slate-400" />,
          statusText: "STATUS: " + telemetry.Inverter_Status,
          statusClass: invFaulted ? "critical" : telemetry.Inverter_Status === "RUNNING" ? "green" : "warning",
          metrics: [
            { label: "Inverter Output (AC)", value: telemetry.Inverter_Output_Power.toFixed(2), unit: "kW" },
            { label: "Conversion Efficiency", value: telemetry.Inverter_Efficiency.toFixed(1), unit: "%" },
            { label: "Heatsink Temperature", value: (35.0 + Math.abs(telemetry.Inverter_Output_Power) * 0.22).toFixed(1), unit: "°C" },
            { label: "DC Link Bus Voltage", value: "680.0", unit: "V" },
            { label: "AC Frequency", value: telemetry.Grid_Frequency.toFixed(3), unit: "Hz" },
            { label: "Thermal SOH (Health)", value: "98.2", unit: "%" },
            { label: "PWM Switching Freq", value: "8.0", unit: "kHz" },
            { label: "Output Voltage THD", value: "1.2", unit: "%" },
          ],
          extraMetric: null,
          assets: [
            { name: "Manufacturer", val: "Apex Power Conversion" },
            { name: "Model", val: "APX-PCS-120kVA-GF" },
            { name: "Inverter Topology", val: "3-Level T-Type NPC" },
            { name: "Grid Compliance", val: "IEEE 1547 / UL 1741 SB" },
            { name: "Cooling Mode", val: "Forced Air Cooling (Dual Fan)" },
            { name: "Firmware Version", val: "v4.92.1-DSP" },
          ]
        };
      case 'grid':
        const gridConnected = telemetry.Grid_Status === 1;
        const pfPower = telemetry.Grid_Power;
        const currentHour = telemetry.hour;
        const tariff = 14.0 <= currentHour && currentHour <= 20.0 ? 7.50 : 4.50;
        return {
          title: "Utility Grid Interconnection",
          icon: <Zap className="w-6 h-6 text-blue-400" />,
          statusText: gridConnected ? "STATUS: CONNECTED" : "STATUS: ISLANDED (OUTAGE)",
          statusClass: gridConnected ? "green" : "critical",
          metrics: [
            { label: "Tie-Line Active Power", value: pfPower > 0 ? "Import: " + pfPower.toFixed(2) : pfPower < 0 ? "Export: " + Math.abs(pfPower).toFixed(2) : "0.00", unit: "kW" },
            { label: "Line Voltage (Ph-Ph)", value: telemetry.Grid_Voltage, unit: "V" },
            { label: "Grid Frequency", value: telemetry.Grid_Frequency.toFixed(3), unit: "Hz" },
            { label: "Active Power Factor", value: "0.98", unit: "" },
            { label: "Billing Tariff Rate", value: `₹${tariff.toFixed(2)}`, unit: "/kWh" },
            { label: "Power Quality Index", value: "99.9", unit: "%" },
          ],
          extraMetric: null,
          assets: [
            { name: "Interconnection Node", val: "Substation Feeder #4B" },
            { name: "Utility Operator", val: "Metro Grid Power Co." },
            { name: "Total Energy Exported", val: (cumulativeEnergy.grid_export || 0).toFixed(2) + " kWh" },
            { name: "Protective Relay", val: "SEL-751 Feeder Relay" },
            { name: "Logical Node Path", val: "Grid_XCBR1.Pos" },
            { name: "Max Import Limit", val: "150.0 kW" },
            { name: "Line Impedance", val: "0.15 + j0.08 Ω" },
          ]
        };
      case 'load':
        return {
          title: "Load Feeder Details",
          icon: <Activity className="w-6 h-6 text-rose-400" />,
          statusText: telemetry.load_shedding_level > 0
            ? `STATUS: LOAD SHED LEVEL ${telemetry.load_shedding_level}`
            : loadPowerStatus === 'powered'
              ? "STATUS: FULLY POWERED ✓"
              : loadPowerStatus === 'partial'
                ? "STATUS: PARTIAL SUPPLY ◑"
                : "STATUS: UNSUPPLIED ✗",
          statusClass: telemetry.load_shedding_level > 0
            ? "warning"
            : loadPowerStatus === 'powered'
              ? "green"
              : loadPowerStatus === 'partial'
                ? "warning"
                : "error",
          metrics: [
            { label: "Active Power Demand", value: telemetry.Load_Demand.toFixed(2), unit: "kW" },
            { label: "Feeder AC Voltage", value: telemetry.Load_Voltage, unit: "V" },
            { label: "Feeder AC Current", value: telemetry.Load_Current.toFixed(1), unit: "A" },
            { label: "Average Power Factor", value: "0.92", unit: "lag" },
            { label: "Reactive Power (VAR)", value: (telemetry.Load_Demand * 0.42).toFixed(2), unit: "kVAR" },
            { label: "Current THDi (Distortion)", value: "2.5", unit: "%" },
          ],
          extraMetric: { label: "Original Base Load", value: telemetry.original_load.toFixed(2), unit: "kW", className: "text-slate-400 font-mono" },
          assets: [
            { name: "Feeder Designation", val: "Feeder #A (Factory Load)" },
            { name: "Main Breaker Type", val: "Air Circuit Breaker (ACB)" },
            { name: "Protective Setting", val: "Overcurrent / Earth Fault" },
            { name: "Smart Meter Protocol", val: "OPC UA Client (Nodes ns=2)" },
            { name: "Connected Phase", val: "3-Phase 3-Wire Delta" },
          ]
        };
      default:
        return null;
    }
  };

  const formatHour = (hourDecimal) => {
    const h = Math.floor(hourDecimal);
    const m = Math.floor((hourDecimal - h) * 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  };

  // 10x10 Cell Thermal Heatmap Grid for Battery digital twin
  const renderBatteryHeatmap = () => {
    const cells = [];
    const baseTemp = telemetry.Battery_Temperature;
    const isRunaway = telemetry.active_failures?.includes("BATTERY_RUNAWAY");
    const currentI = telemetry.Battery_Current;
    const timestamp = telemetry.timestamp || Date.now() / 1000;
    
    for (let r = 0; r < 10; r++) {
      for (let c = 0; c < 10; c++) {
        // Calculate distance from center cell grouping (4.5, 4.5)
        const dx = r - 4.5;
        const dy = c - 4.5;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        // Heat distribution model: core cells are warmer, outer are cooler.
        // Current load adds load-based heat. Runaway spikes core aggressively.
        let cellTemp = baseTemp + (4.8 - dist) * 0.75 + Math.abs(currentI) * 0.04;
        if (isRunaway) {
          cellTemp += (6.5 - dist) * 6.5; // Core runaway spikes temperatures
        }
        
        // Minor dynamic variance
        cellTemp += Math.sin(timestamp * 0.5 + r * 1.5 + c * 2.0) * 0.15;
        cellTemp = Math.max(12.0, Math.min(cellTemp, 85.0));
        
        // Assign color categories
        let cellColorClass = "bg-emerald-500/80";
        if (cellTemp > 50) {
          cellColorClass = "bg-rose-600 animate-pulse shadow-md shadow-rose-600/50";
        } else if (cellTemp > 42) {
          cellColorClass = "bg-red-500 shadow-sm shadow-red-500/40";
        } else if (cellTemp > 34) {
          cellColorClass = "bg-orange-500";
        } else if (cellTemp > 26) {
          cellColorClass = "bg-amber-400 text-slate-900";
        }
        
        cells.push(
          <div 
            key={`${r}-${c}`}
            title={`Cell Group [Row ${r+1}, Col ${c+1}]: ${cellTemp.toFixed(1)}°C`}
            className={`w-3.5 h-3.5 md:w-5 md:h-5 rounded transition-all duration-300 border border-slate-950/20 cursor-crosshair ${cellColorClass}`}
          />
        );
      }
    }
    
    return (
      <div className="flex flex-col items-center">
        <div className="flex justify-between w-full items-center mb-3">
          <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider">BESS Battery Module Stack (100 Cell Matrix)</span>
          <span className="text-[9px] font-mono font-bold text-slate-500">Core Temp Status: {isRunaway ? "DANGER RUNAWAY" : "NOMINAL"}</span>
        </div>
        <div className="grid grid-cols-10 gap-1 bg-slate-950/90 p-3 rounded-xl border border-slate-900 shadow-inner">
          {cells}
        </div>
        <div className="flex flex-wrap justify-between w-full mt-3.5 text-[8.5px] font-bold text-slate-500 uppercase gap-2">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-emerald-500/80 rounded" /> Cool (&lt;26°C)</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-amber-400 rounded" /> Mid (26-34°C)</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-orange-500 rounded" /> Warm (34-42°C)</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-rose-600 rounded" /> Hot (&gt;42°C)</span>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen flex text-slate-100 dark:text-slate-900 font-sans transition-colors duration-300 bg-gradient-to-br from-slate-950 to-slate-900 theme-container select-none">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className={`glass-panel rounded-none border-y-0 border-l-0 border-r border-slate-800 dark:border-slate-300 transition-all duration-300 flex flex-col ${sidebarOpen ? 'w-64' : 'w-20'} shrink-0 z-40 hidden md:flex`}>
        {/* Sidebar Header */}
        <div className="p-4 flex items-center gap-3 border-b border-slate-800 dark:border-slate-200">
          <div className="bg-slate-950 dark:bg-slate-200 p-2 rounded-xl border border-emerald-500/30 flex items-center justify-center shrink-0">
            <Activity className="w-6 h-6 text-emerald-400 animate-pulse" />
          </div>
          {sidebarOpen && (
            <div className="flex flex-col">
              <span className="font-extrabold text-sm uppercase tracking-wider text-slate-100 dark:text-slate-850">SEnergy OS</span>
              <span className="text-[9px] font-bold text-slate-500">v3.0.0-Hybrid</span>
            </div>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {[
            { id: 'apex', label: 'APEX Platform', icon: <Sparkles className="w-4 h-4 text-emerald-400 animate-pulse" /> },
            { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> },
            { id: 'data_sources', label: 'Data Sources', icon: <Database className="w-4 h-4 text-cyan-400" /> },
            { id: 'live_display', label: 'Live Display', icon: <Sliders className="w-4 h-4 text-emerald-400" /> },
            { id: 'ems', label: 'EMS Control', icon: <Sliders className="w-4 h-4" /> },
            { id: 'battery', label: 'Battery BESS', icon: <Battery className="w-4 h-4" /> },
            { id: 'renewable', label: 'Renewable', icon: <Sun className="w-4 h-4" /> },
            { id: 'grid', label: 'Grid Tie', icon: <Zap className="w-4 h-4" /> },
            { id: 'ai', label: 'AI Analytics', icon: <Sparkles className="w-4 h-4" /> },
            { id: 'alarms', label: 'Alarms', icon: <AlertTriangle className="w-4 h-4" />, badge: activeAlarms.length > 0 ? activeAlarms.length : null },
            { id: 'reports', label: 'Reports', icon: <TrendingUp className="w-4 h-4" /> },
            { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all relative ${
                activeTab === item.id
                  ? 'bg-emerald-500 text-slate-950 shadow-lg'
                  : 'text-slate-400 hover:text-slate-200 dark:text-slate-600 dark:hover:text-slate-900 hover:bg-slate-900/40 dark:hover:bg-slate-200/50'
              }`}
            >
              {item.icon}
              {sidebarOpen && <span className="truncate">{item.label}</span>}
              {item.badge && (
                <span className={`absolute right-2 px-1.5 py-0.5 text-[8px] font-extrabold rounded-full ${
                  activeTab === item.id ? 'bg-slate-950 text-emerald-400' : 'bg-rose-600 text-white animate-pulse'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-slate-800 dark:border-slate-200 flex flex-col gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center p-2 rounded-lg bg-slate-950/40 dark:bg-slate-100 hover:bg-slate-900/60 dark:hover:bg-slate-200 text-slate-400 hover:text-white dark:hover:text-slate-800 transition-colors"
          >
            {sidebarOpen ? <ArrowLeft className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT WRAPPER */}
      <div className="flex-1 flex flex-col min-w-0 grid-bg overflow-y-auto p-4 md:p-6">
        
        {/* FLOATING TOP STATUS BAR */}
        <header className="glass-panel p-4 mb-5 flex flex-col xl:flex-row justify-between items-center gap-4 border border-slate-800 dark:border-slate-300">
          <div className="flex items-center gap-3">
            {/* Mobile Nav Toggle */}
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)} 
              className="md:hidden p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
            >
              <Activity className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-base font-extrabold tracking-tight text-white dark:text-slate-900 flex items-center gap-2">
                APEX Smart-Grid OS <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">v3.0 Hybrid</span>
              </h1>
              <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Supervisory Control and Data Acquisition HMI</p>
            </div>
          </div>

          {/* Real-time Status Marquee Indicators */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Sustainability Index Badge */}
            <div className="bg-slate-950/40 dark:bg-slate-100 border border-slate-900 dark:border-slate-300 px-2.5 py-1 rounded-lg text-[9px] font-bold flex items-center gap-1.5">
              <Leaf className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400 dark:text-slate-500 uppercase">Sustain Index:</span>
              <span className="font-mono text-emerald-400 dark:text-emerald-600">
                {Math.min(100, Math.round(((telemetry.Solar_Power + telemetry.Wind_Power) / (telemetry.Load_Demand || 1)) * 100))}%
              </span>
            </div>

            {/* Microgrid System Efficiency Badge */}
            <div className="bg-slate-950/40 dark:bg-slate-100 border border-slate-900 dark:border-slate-300 px-2.5 py-1 rounded-lg text-[9px] font-bold flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-slate-400 dark:text-slate-500 uppercase">Grid Eff:</span>
              <span className="font-mono text-blue-400 dark:text-blue-600">{telemetry.Inverter_Efficiency.toFixed(1)}%</span>
            </div>

            {/* Audio Warning Controls */}
            <button 
              onClick={() => setIsAudioMuted(!isAudioMuted)} 
              title={isAudioMuted ? "Unmute alarm warnings" : "Mute alarm warnings"}
              className={`p-1.5 rounded-lg border text-[9px] font-bold flex items-center gap-1 ${isAudioMuted ? 'bg-slate-900/80 text-slate-500 border-slate-800' : 'bg-rose-600 text-white border-rose-500 shadow shadow-rose-600/35'}`}
            >
              {isAudioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5 animate-bounce" />}
              <span className="font-extrabold">{isAudioMuted ? "MUTED" : "ALARM SOUND"}</span>
            </button>

            {/* Theme Dropdown */}
            <div className="relative">
              <select 
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="bg-slate-950/80 dark:bg-white border border-slate-900 dark:border-slate-300 rounded-lg px-2.5 py-1.5 text-[9px] font-bold text-slate-300 dark:text-slate-700 outline-none cursor-pointer focus:border-emerald-500"
              >
                <option value="dark">Dark Theme</option>
                <option value="light">Light Theme</option>
                <option value="cyberpunk">Cyberpunk Neon</option>
                <option value="green">Energy Green</option>
                <option value="blue">Industrial Blue</option>
              </select>
            </div>

            {/* User Role Security Control Banner */}
            <div className="flex items-center bg-slate-950/70 dark:bg-slate-200 border border-slate-900 px-2.5 py-1 rounded-lg text-[9px] font-bold gap-2">
              <span className="text-slate-400 dark:text-slate-500 flex items-center gap-1">
                {userRole === 'viewer' ? <Lock className="w-3 h-3 text-slate-500" /> : <Unlock className="w-3 h-3 text-emerald-400" />}
                Role:
              </span>
              <span className="font-mono text-emerald-400 dark:text-emerald-600 font-extrabold uppercase tracking-wider">{userRole}</span>
              {userRole !== 'viewer' ? (
                <button 
                  onClick={handleLogout}
                  className="ml-1 bg-slate-800 hover:bg-slate-700 text-white text-[8px] font-extrabold px-1.5 py-0.5 rounded border border-slate-700"
                >
                  Lock
                </button>
              ) : (
                <button 
                  onClick={() => setShowLoginModal(true)}
                  className="ml-1 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 border border-emerald-500/30 text-[8px] font-extrabold px-1.5 py-0.5 rounded"
                >
                  Authorize
                </button>
              )}
            </div>

            {/* Live Tariff display */}
            <div className="bg-slate-950/40 dark:bg-slate-100 border border-slate-900 dark:border-slate-300 px-2.5 py-1 rounded-lg text-[9px] font-bold flex items-center gap-1.5">
              <span className="text-slate-400 dark:text-slate-500">Tariff Rate:</span>
              <span className="font-mono text-emerald-400 dark:text-emerald-600 font-extrabold">₹{(telemetry.electricity_cost * 3600.0).toFixed(2)}/kWh</span>
            </div>

            {/* Connectivity Badge */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[9px] font-extrabold ${isConnected ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'}`}>
              {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              {isConnected ? 'STREAMING LIVE' : 'OFFLINE SIM'}
            </div>
          </div>
        </header>

        {/* ── LIVE EMS POWER DISPATCH BANNER ── */}
        {(() => {
          const solar = telemetry.Solar_Power || 0;
          const wind  = telemetry.Wind_Power  || 0;
          const load  = telemetry.Load_Demand || 0;
          const soc   = telemetry.Battery_SOC || 0;
          const gridP = telemetry.Grid_Power  || 0;
          const battI = telemetry.Battery_Current || 0;
          const battV = telemetry.Battery_Voltage || 0;
          const battKw = (battV * battI) / 1000.0;
          const isCharging  = battI > 0;
          const isDischarging = battI < 0;
          const gridImporting = gridP > 0.5;
          const gridExporting = gridP < -0.5;
          const renewable = solar + wind;
          const ems = telemetry.ems_action || 'STANDBY';

          // Banner color: red=grid importing, amber=battery discharging, green=renewable only
          const bannerCls = gridImporting
            ? 'border-blue-500/30 bg-blue-950/30 text-blue-300'
            : isDischarging
            ? 'border-amber-500/30 bg-amber-950/20 text-amber-300'
            : 'border-emerald-500/25 bg-emerald-950/20 text-emerald-300';

          return (
            <div className={`mx-4 mt-2 mb-0 px-4 py-2 rounded-xl border flex flex-wrap items-center gap-x-5 gap-y-1 text-[9px] font-extrabold uppercase tracking-wider ${bannerCls}`}>
              <span className="text-slate-400">⚡ EMS Live Dispatch:</span>

              {/* Source breakdown */}
              <span className={solar > 0.5 ? 'text-yellow-400' : 'text-slate-600'}>
                ☀ Solar {solar.toFixed(1)} kW
              </span>
              <span className={wind > 0.5 ? 'text-purple-400' : 'text-slate-600'}>
                🌬 Wind {wind.toFixed(1)} kW
              </span>
              <span className={isDischarging ? 'text-amber-400' : isCharging ? 'text-emerald-400' : 'text-slate-500'}>
                🔋 Batt {isDischarging ? `↓ ${Math.abs(battKw).toFixed(1)} kW DISCHARGING` : isCharging ? `↑ ${Math.abs(battKw).toFixed(1)} kW CHARGING` : 'IDLE'} · SOC {soc.toFixed(0)}%
              </span>
              <span className={gridImporting ? 'text-blue-400' : gridExporting ? 'text-cyan-400' : 'text-slate-500'}>
                🔌 Grid {gridImporting ? `IMPORT ${gridP.toFixed(1)} kW` : gridExporting ? `EXPORT ${Math.abs(gridP).toFixed(1)} kW` : 'IDLE'}
              </span>
              <span className="text-slate-400">→ Load {load.toFixed(1)} kW</span>
              <span className={`ml-auto px-2 py-0.5 rounded font-mono text-[8px] ${
                gridImporting ? 'bg-blue-900/60 text-blue-300 border border-blue-700/40'
                : isDischarging ? 'bg-amber-900/60 text-amber-300 border border-amber-700/40'
                : 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/30'
              }`}>{ems}</span>
            </div>
          );
        })()}



        {/* ACTIVE SIMULATION FAILURE WARNING BANNER */}
        {telemetry.active_failures && telemetry.active_failures.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-rose-950/80 border border-rose-500/40 text-rose-200 px-4 py-2.5 rounded-xl mb-5 flex items-center justify-between text-xs font-semibold shadow-lg shadow-rose-950/20 alarm-breathe"
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 animate-bounce" />
              <span className="tracking-wide text-[10px] uppercase font-bold">Digital Twin Simulation Fault Injected: </span>
              <div className="flex gap-1.5">
                {telemetry.active_failures.map(f => (
                  <span key={f} className="bg-rose-800/40 border border-rose-500/40 px-2 py-0.5 rounded text-[9px] font-mono font-bold tracking-wider">{f}</span>
                ))}
              </div>
            </div>
            <button 
              onClick={() => handleSimulateFailure(telemetry.active_failures[0], false)}
              className="bg-rose-700 hover:bg-rose-600 text-white px-2.5 py-1 rounded text-[9px] font-bold"
            >
              Reset Faults
            </button>
          </motion.div>
        )}

        {/* TAB CONTENTS */}
        <main className="flex-1 space-y-5">
          
          {/* TAB 0: APEX ENERGY ORCHESTRATION PLATFORM (PHASES 1-6) */}
          {activeTab === 'apex' && (
            <ApexDashboard telemetry={telemetry} isConnected={isConnected} API_BASE={API_BASE} />
          )}

          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-5">
              {/* KPI Cards Grid — 6 key system metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                {[
                  { label: 'Solar Power', value: telemetry.Solar_Power.toFixed(2), unit: 'kW', color: 'text-yellow-400', bg: 'bg-yellow-500/8', icon: <Sun className="w-4 h-4 text-yellow-400" />, sub: `${telemetry.Solar_Voltage.toFixed(0)}V / ${telemetry.Solar_Current.toFixed(1)}A` },
                  { label: 'Wind Power', value: telemetry.Wind_Power.toFixed(2), unit: 'kW', color: 'text-purple-400', bg: 'bg-purple-500/8', icon: <Wind className="w-4 h-4 text-purple-400" />, sub: `${telemetry.Wind_Speed.toFixed(1)} m/s · ${telemetry.Wind_RPM.toFixed(0)} RPM` },
                  { label: 'Battery SOC', value: telemetry.Battery_SOC.toFixed(1), unit: '%', color: 'text-emerald-400', bg: 'bg-emerald-500/8', icon: <Battery className="w-4 h-4 text-emerald-400" />, sub: `${telemetry.Battery_Temperature.toFixed(1)}°C · ${Math.round(telemetry.Battery_SOH)}% SOH` },
                  { label: 'Load Demand', value: telemetry.Load_Demand.toFixed(2), unit: 'kW', color: 'text-rose-400', bg: 'bg-rose-500/8', icon: <Activity className="w-4 h-4 text-rose-400" />, sub: `${telemetry.Load_Current.toFixed(1)}A / ${telemetry.Load_Voltage.toFixed(0)}V` },
                  { label: 'Grid Power', value: Math.abs(telemetry.Grid_Power).toFixed(2), unit: 'kW', color: telemetry.Grid_Power > 0 ? 'text-blue-400' : 'text-emerald-400', bg: 'bg-blue-500/8', icon: <Zap className="w-4 h-4 text-blue-400" />, sub: telemetry.Grid_Power < 0 ? `Exporting · Total: ${(cumulativeEnergy.grid_export || 0).toFixed(1)} kWh` : (telemetry.Grid_Power > 0 ? 'Importing from Grid' : `Grid Idle · Total Exported: ${(cumulativeEnergy.grid_export || 0).toFixed(1)} kWh`) },
                  { label: 'Inverter Eff.', value: telemetry.Inverter_Efficiency.toFixed(1), unit: '%', color: 'text-slate-300', bg: 'bg-slate-500/8', icon: <Cpu className="w-4 h-4 text-slate-300" />, sub: telemetry.Inverter_Status },
                ].map((kpi, i) => (
                  <div key={i} className={`glass-panel p-3 ${kpi.bg} float-up`} style={{ animationDelay: `${i * 0.05}s` }}>
                    <div className="flex items-center justify-between mb-1.5">
                      {kpi.icon}
                      <span className="text-[8px] font-bold uppercase text-slate-500 tracking-wider text-right">{kpi.label}</span>
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className={`text-xl font-extrabold font-mono ${kpi.color}`}>{kpi.value}</span>
                      <span className="text-[9px] text-slate-500 font-bold">{kpi.unit}</span>
                    </div>
                    <div className="text-[8px] text-slate-500 font-mono mt-1 truncate">{kpi.sub}</div>
                  </div>
                ))}
              </div>

              {/* Dynamic Power Flow schematic panel */}
              <div className="glass-panel p-5 relative overflow-hidden flex flex-col items-center">
                <div className="w-full flex justify-between items-center mb-3">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">Microgrid HMI Single Line Diagram</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Toggle Flow Arrows Option */}
                    <button 
                      onClick={() => setShowFlowArrows(!showFlowArrows)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold border transition-all ${
                        showFlowArrows 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.15)]' 
                          : 'bg-slate-800/50 text-slate-400 border-slate-700/50 hover:bg-slate-800'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${showFlowArrows ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'}`}></span>
                      {showFlowArrows ? 'Flow Arrows On' : 'Flow Arrows Off'}
                    </button>
                    <span className="text-[9px] bg-slate-900 text-emerald-400 dark:bg-slate-200 dark:text-emerald-700 font-mono font-bold px-2 py-0.5 rounded-md border border-slate-800/50">
                      Live System Flows
                    </span>
                  </div>
                </div>

                {/* SVG HMI Canvas */}
                <div className="w-full overflow-x-auto py-2.5 flex justify-center">
                  <svg width="850" height="260" viewBox="0 0 850 260" className="w-full max-w-4xl">
                    <defs>
                      <linearGradient id="solarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#eab308" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#ca8a04" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="windGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#a855f7" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#7e22ce" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="battGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#047857" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="invGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.9" />
                        <stop offset="100%" stopColor="#475569" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="gridGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="loadGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#be123c" stopOpacity="0.95" />
                      </linearGradient>
                      <linearGradient id="isolatedGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#475569" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#334155" stopOpacity="0.9" />
                      </linearGradient>
                    </defs>

                    {/* BUSBAR LINES */}
                    {/* Solar to Inverter */}
                    <path d="M 130 65 L 365 130" stroke="#f59e0b" strokeWidth="2.5" fill="none" opacity="0.6" />
                    <path d="M 130 65 L 365 130" stroke="#f59e0b" strokeWidth="2.5" fill="none" 
                          style={{ "--glow-color": "rgba(245,158,11,0.6)" }}
                          className={`flow-line ${solarEnabled && telemetry.Solar_Power > 0 ? '' : 'inactive'}`} />

                    {/* Wind to Inverter */}
                    <path d="M 130 185 L 365 130" stroke="#a855f7" strokeWidth="2.5" fill="none" opacity="0.6" />
                    <path d="M 130 185 L 365 130" stroke="#a855f7" strokeWidth="2.5" fill="none" 
                          style={{ "--glow-color": "rgba(168,85,247,0.6)" }}
                          className={`flow-line ${windEnabled && telemetry.Wind_Power > 0 ? '' : 'inactive'}`} />

                    {/* Battery to Inverter */}
                    <path d="M 425 205 L 425 170" stroke="#10b981" strokeWidth="2.5" fill="none" opacity="0.6" />
                    <path d="M 425 205 L 425 170" stroke="#10b981" strokeWidth="2.5" fill="none" 
                          style={{ "--glow-color": "rgba(16,185,129,0.6)" }}
                          className={`flow-line ${batteryEnabled && telemetry.Battery_Current < 0 ? '' : batteryEnabled && telemetry.Battery_Current > 0 ? 'reverse' : 'inactive'}`} />

                    {/* Inverter to Grid Tie */}
                    <path d="M 485 130 L 680 65" stroke="#3b82f6" strokeWidth="2.5" fill="none" opacity="0.6" />
                    <path d="M 485 130 L 680 65" stroke="#3b82f6" strokeWidth="2.5" fill="none" 
                          style={{ "--glow-color": "rgba(59,130,246,0.6)" }}
                          className={`flow-line ${gridEnabled && telemetry.Grid_Power < 0 ? '' : gridEnabled && telemetry.Grid_Power > 0 ? 'reverse' : 'inactive'}`} />

                    {/* Inverter to Load */}
                    <path d="M 485 130 L 680 185" stroke="#f43f5e" strokeWidth="2.5" fill="none" opacity="0.6" />
                    <path d="M 485 130 L 680 185" stroke="#f43f5e" strokeWidth="2.5" fill="none" 
                          style={{ "--glow-color": "rgba(239,68,68,0.6)" }}
                          className={`flow-line ${telemetry.Load_Demand > 0 ? '' : 'inactive'}`} />

                    {/* STATIC POWER FLOW DIRECTION ARROWHEADS */}
                    {showFlowArrows && (
                      <g style={{ pointerEvents: 'none' }}>
                        {/* Solar PV to Inverter Arrow */}
                        {solarEnabled && telemetry.Solar_Power > 0 && (
                          <g transform="translate(188.75, 81.25) rotate(15.46)">
                            <polygon points="-6,-4 6,0 -6,4" fill="#f59e0b" className="glow-yellow" />
                          </g>
                        )}
                        {/* Wind to Inverter Arrow */}
                        {windEnabled && telemetry.Wind_Power > 0 && (
                          <g transform="translate(188.75, 171.25) rotate(-13.15)">
                            <polygon points="-6,-4 6,0 -6,4" fill="#a855f7" className="glow-purple" />
                          </g>
                        )}
                        {/* Battery discharging (Up) or charging (Down) Arrow */}
                        {/* Arrow above breaker (between breaker@187.5 and inverter bottom@170) */}
                        {batteryEnabled && telemetry.Battery_Current && Math.abs(telemetry.Battery_Current) > 0.1 && (
                          <g transform={`translate(425, 178) rotate(${telemetry.Battery_Current < 0 ? -90 : 90})`}>
                            <polygon points="-7,-5 7,0 -7,5" fill="#10b981" className="glow-green" />
                          </g>
                        )}
                        {/* Arrow below breaker (between breaker@187.5 and BESS top@205) */}
                        {batteryEnabled && telemetry.Battery_Current && Math.abs(telemetry.Battery_Current) > 0.1 && (
                          <g transform={`translate(425, 197) rotate(${telemetry.Battery_Current < 0 ? -90 : 90})`}>
                            <polygon points="-7,-5 7,0 -7,5" fill="#10b981" className="glow-green" />
                          </g>
                        )}
                        {/* Grid Export (Right) or Import (Left) Arrow */}
                        {gridEnabled && telemetry.Grid_Power !== 0 && (
                          <g transform={`translate(533.75, 113.75) rotate(${telemetry.Grid_Power < 0 ? -18.43 : 161.57})`}>
                            <polygon points="-6,-4 6,0 -6,4" fill="#3b82f6" className="glow-blue" />
                          </g>
                        )}
                        {/* Inverter to Load Arrow */}
                        {telemetry.Load_Demand > 0 && (
                          <g transform="translate(582.5, 157.5) rotate(15.75)">
                            <polygon points="-6,-4 6,0 -6,4" fill="#f43f5e" className="glow-red" />
                          </g>
                        )}
                      </g>
                    )}

                    {/* BREAKER SWITCHES (DISCONNECTORS) */}
                    {/* Solar PV Breaker */}
                    <g transform="translate(247.5, 97.5)" className="cursor-pointer" onClick={(e) => { e.stopPropagation(); handleComponentToggle('solar', !solarEnabled); }} title={userRole !== 'admin' && userRole !== 'engineer' ? "Breaker: Requires Operator credentials" : `Toggle Solar Breaker`}>
                      <circle r="9" fill="#0f172a" stroke={solarEnabled ? "#10b981" : "#f43f5e"} strokeWidth="2" />
                      {solarEnabled ? (
                        <line x1="-5" y1="0" x2="5" y2="0" stroke="#10b981" strokeWidth="2.5" />
                      ) : (
                        <line x1="-5" y1="0" x2="3.5" y2="-4.5" stroke="#f43f5e" strokeWidth="2.5" />
                      )}
                    </g>

                    {/* Wind Breaker */}
                    <g transform="translate(247.5, 157.5)" className="cursor-pointer" onClick={(e) => { e.stopPropagation(); handleComponentToggle('wind', !windEnabled); }} title={userRole !== 'admin' && userRole !== 'engineer' ? "Breaker: Requires Operator credentials" : `Toggle Wind Breaker`}>
                      <circle r="9" fill="#0f172a" stroke={windEnabled ? "#10b981" : "#f43f5e"} strokeWidth="2" />
                      {windEnabled ? (
                        <line x1="-5" y1="0" x2="5" y2="0" stroke="#10b981" strokeWidth="2.5" />
                      ) : (
                        <line x1="-5" y1="0" x2="3.5" y2="-4.5" stroke="#f43f5e" strokeWidth="2.5" />
                      )}
                    </g>

                    {/* Battery Breaker */}
                    <g transform="translate(425, 187.5)" className="cursor-pointer" onClick={(e) => { e.stopPropagation(); handleComponentToggle('battery', !batteryEnabled); }} title={userRole !== 'admin' && userRole !== 'engineer' ? "Breaker: Requires Operator credentials" : `Toggle BESS Breaker`}>
                      <circle r="9" fill="#0f172a" stroke={batteryEnabled ? "#10b981" : "#f43f5e"} strokeWidth="2" />
                      {batteryEnabled ? (
                        <line x1="0" y1="-5" x2="0" y2="5" stroke="#10b981" strokeWidth="2.5" />
                      ) : (
                        <line x1="0" y1="-5" x2="4.5" y2="3.5" stroke="#f43f5e" strokeWidth="2.5" />
                      )}
                    </g>

                    {/* Utility Grid Breaker */}
                    <g transform="translate(582.5, 97.5)" className="cursor-pointer" onClick={(e) => { e.stopPropagation(); handleComponentToggle('grid', !gridEnabled); }} title={userRole !== 'admin' && userRole !== 'engineer' ? "Breaker: Requires Operator credentials" : `Toggle Grid Breaker`}>
                      <circle r="9" fill="#0f172a" stroke={gridEnabled ? "#10b981" : "#f43f5e"} strokeWidth="2" />
                      {gridEnabled ? (
                        <line x1="-5" y1="0" x2="5" y2="0" stroke="#10b981" strokeWidth="2.5" />
                      ) : (
                        <line x1="-5" y1="0" x2="3.5" y2="-4.5" stroke="#f43f5e" strokeWidth="2.5" />
                      )}
                    </g>

                    {/* NODES */}
                    
                    {/* Solar PV Node */}
                    <g onClick={() => setActiveFaceplate('solar')} className="cursor-pointer hover:opacity-85 transition-all animate-none" transform="translate(40, 30)">
                      <rect width="90" height="70" rx="8" fill={solarEnabled ? "url(#solarGrad)" : "url(#isolatedGrad)"} className={solarEnabled ? "glow-yellow" : "opacity-80"} />
                      {solarEnabled ? (
                        <motion.g
                          animate={{ opacity: telemetry.Solar_Power > 0 ? [0.75, 1, 0.75] : 1 }}
                          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                        >
                          <Sun className="w-5 h-5 text-yellow-100" x="8" y="8" />
                        </motion.g>
                      ) : (
                        <Sun className="w-5 h-5 text-slate-400" x="8" y="8" />
                      )}
                      <text x="35" y="24" fill={solarEnabled ? "#fff" : "#cbd5e1"} fontSize="11" fontWeight="bold">SOLAR PV</text>
                      {solarEnabled ? (
                        <>
                          <text x="12" y="46" fill="#fff" fontSize="13" fontWeight="bold" className="font-mono">{telemetry.Solar_Power.toFixed(2)} kW</text>
                          <text x="12" y="58" fill="#fef08a" fontSize="9" className="font-mono">{telemetry.Solar_Voltage.toFixed(0)}V / {telemetry.Solar_Current.toFixed(1)}A</text>
                        </>
                      ) : (
                        <text x="12" y="48" fill="#cbd5e1" fontSize="11" fontWeight="extrabold" className="font-mono">ISOLATED</text>
                      )}
                    </g>

                    {/* Wind Turbine Node */}
                    <g onClick={() => setActiveFaceplate('wind')} className="cursor-pointer hover:opacity-85 transition-all" transform="translate(40, 150)">
                      <rect width="90" height="70" rx="8" fill={windEnabled ? "url(#windGrad)" : "url(#isolatedGrad)"} className={windEnabled ? "glow-purple" : "opacity-80"} />
                      <motion.g
                        animate={{ rotate: (windEnabled && telemetry.Wind_Power > 0) ? 360 : 0 }}
                        transition={(windEnabled && telemetry.Wind_Power > 0) ? { repeat: Infinity, duration: 4, ease: "linear" } : {}}
                        style={{ originX: '18px', originY: '18px' }}
                      >
                        <Wind className={`w-5 h-5 ${windEnabled ? 'text-purple-100' : 'text-slate-400'}`} x="8" y="8" />
                      </motion.g>
                      <text x="35" y="24" fill={windEnabled ? "#fff" : "#cbd5e1"} fontSize="11" fontWeight="bold">WIND</text>
                      {windEnabled ? (
                        <>
                          <text x="12" y="46" fill="#fff" fontSize="13" fontWeight="bold" className="font-mono">{telemetry.Wind_Power.toFixed(2)} kW</text>
                          <text x="12" y="58" fill="#e9d5ff" fontSize="9" className="font-mono">{telemetry.Wind_Speed.toFixed(1)} m/s</text>
                        </>
                      ) : (
                        <text x="12" y="48" fill="#cbd5e1" fontSize="11" fontWeight="extrabold" className="font-mono">ISOLATED</text>
                      )}
                    </g>

                    {/* Hybrid Inverter Node (Center PCS Gateway) */}
                    <g onClick={() => setActiveFaceplate('inverter')} className="cursor-pointer hover:opacity-85 transition-all" transform="translate(365, 95)">
                      <rect width="120" height="75" rx="10" fill="url(#invGrad)" className="stroke-slate-700 stroke-2" />
                      <Cpu className="w-5 h-5 text-slate-800" x="8" y="8" />
                      <text x="32" y="22" fill="#0f172a" fontSize="11" fontWeight="bold">HYBRID PCS</text>
                      <text x="12" y="44" fill="#0f172a" fontSize="12" fontWeight="bold" className="font-mono">{telemetry.Inverter_Output_Power.toFixed(2)} kW</text>
                      <text x="12" y="56" fill="#475569" fontSize="9" className="font-mono">Efficiency: {telemetry.Inverter_Efficiency.toFixed(1)}%</text>
                      <text x="12" y="66" fill={telemetry.Inverter_Status === 'FAULTED' ? '#ef4444' : '#059669'} fontSize="9" fontWeight="bold" className="font-mono">{telemetry.Inverter_Status}</text>
                    </g>

                    {/* BESS Battery Storage Node */}
                    <g onClick={() => setActiveFaceplate('battery')} className="cursor-pointer hover:opacity-85 transition-all" transform="translate(370, 205)">
                      <rect width="110" height="50" rx="8" fill={batteryEnabled ? "url(#battGrad)" : "url(#isolatedGrad)"} className={batteryEnabled ? "glow-green" : "opacity-80"} />
                      <Battery className={`w-5 h-5 ${batteryEnabled ? 'text-emerald-100' : 'text-slate-400'}`} x="8" y="6" />
                      <text x="35" y="20" fill={batteryEnabled ? "#fff" : "#cbd5e1"} fontSize="11" fontWeight="bold">BESS</text>
                      {batteryEnabled ? (
                        <text x="12" y="40" fill="#fff" fontSize="13" fontWeight="bold" className="font-mono">{telemetry.Battery_SOC.toFixed(1)}% SOC</text>
                      ) : (
                        <text x="12" y="40" fill="#cbd5e1" fontSize="11" fontWeight="extrabold" className="font-mono">ISOLATED</text>
                      )}
                    </g>

                    {/* Utility Grid Tie Node */}
                    <g onClick={() => setActiveFaceplate('grid')} className="cursor-pointer hover:opacity-85 transition-all" transform="translate(680, 30)">
                      <rect width="110" height="70" rx="8" fill={gridEnabled ? "url(#gridGrad)" : "url(#isolatedGrad)"} className={gridEnabled ? "glow-blue" : "opacity-80"} />
                      <Zap className={`w-5 h-5 ${gridEnabled ? 'text-blue-100' : 'text-slate-400'}`} x="8" y="8" />
                      <text x="35" y="24" fill={gridEnabled ? "#fff" : "#cbd5e1"} fontSize="11" fontWeight="bold">UTILITY GRID</text>
                      {gridEnabled ? (
                        <>
                          <text x="12" y="46" fill="#fff" fontSize="13" fontWeight="bold" className="font-mono">
                            {telemetry.Grid_Power > 0 ? `Import: ${telemetry.Grid_Power.toFixed(1)}` : telemetry.Grid_Power < 0 ? `Export: ${Math.abs(telemetry.Grid_Power).toFixed(1)}` : 'Idle'}
                          </text>
                          <text x="12" y="58" fill="#93c5fd" fontSize="9" className="font-mono">{telemetry.Grid_Voltage.toFixed(0)}V / {telemetry.Grid_Frequency.toFixed(2)}Hz</text>
                        </>
                      ) : (
                        <text x="12" y="48" fill="#cbd5e1" fontSize="11" fontWeight="extrabold" className="font-mono">ISOLATED</text>
                      )}
                    </g>

                    {/* Load Feeder Node */}
                    <g onClick={() => setActiveFaceplate('load')} className="cursor-pointer hover:opacity-85 transition-all" transform="translate(660, 140)">
                      <rect width="130" height="90" rx="8" fill="url(#loadGrad)" className="glow-red" />
                      <Activity className="w-5 h-5 text-rose-100" x="8" y="8" />
                      <text x="35" y="24" fill="#fff" fontSize="11" fontWeight="bold">LOAD FEEDER</text>
                      <text x="12" y="46" fill="#fff" fontSize="13" fontWeight="bold" className="font-mono">{telemetry.Load_Demand.toFixed(2)} kW</text>
                      <text x="12" y="58" fill="#fca5a5" fontSize="9" className="font-mono">{telemetry.Load_Current.toFixed(1)}A / {telemetry.Load_Voltage.toFixed(0)}V</text>

                      {/* ── Power Status Indicator Light ── */}
                      {/* Outer ring glow */}
                      <circle
                        cx="108" cy="14"
                        r="10"
                        fill={loadPowerStatus === 'powered' ? 'rgba(34,197,94,0.18)' : loadPowerStatus === 'partial' ? 'rgba(251,191,36,0.18)' : 'rgba(239,68,68,0.18)'}
                        className={loadPowerStatus === 'powered' ? 'load-status-glow-green' : loadPowerStatus === 'partial' ? 'load-status-glow-amber' : 'load-status-glow-red'}
                      />
                      {/* Inner filled dot */}
                      <circle
                        cx="108" cy="14"
                        r="6"
                        fill={loadPowerStatus === 'powered' ? '#22c55e' : loadPowerStatus === 'partial' ? '#fbbf24' : '#ef4444'}
                        stroke={loadPowerStatus === 'powered' ? '#16a34a' : loadPowerStatus === 'partial' ? '#d97706' : '#b91c1c'}
                        strokeWidth="1.5"
                        className={loadPowerStatus === 'powered' ? 'load-status-glow-green' : loadPowerStatus === 'partial' ? 'load-status-glow-amber' : 'load-status-glow-red'}
                      />
                      {/* Status label under the dot */}
                      <text
                        x="108" y="80"
                        textAnchor="middle"
                        fill={loadPowerStatus === 'powered' ? '#4ade80' : loadPowerStatus === 'partial' ? '#fcd34d' : '#f87171'}
                        fontSize="7"
                        fontWeight="bold"
                        className="font-mono"
                      >
                        {loadPowerStatus === 'powered' ? '● POWERED' : loadPowerStatus === 'partial' ? '◑ PARTIAL' : '○ UNSUPPLIED'}
                      </text>
                    </g>
                  </svg>
                </div>

                {/* Load Supply Source Breakdown */}
                <div className="w-full mt-4 border-t border-slate-800/50 dark:border-slate-300/50 pt-4 flex flex-col md:flex-row justify-between items-center gap-4">
                  <div className="text-left shrink-0">
                    <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-650 tracking-wider block">Load Demand Supply Mix</span>
                    <span className="text-[8px] text-slate-500 mt-0.5 block">Breakdown of where the current load gets its power</span>
                  </div>
                  <div className="w-full grid grid-cols-2 md:grid-cols-4 gap-3 flex-1">
                    {(() => {
                      const breakdown = calculateLoadSourceBreakdown();
                      return [
                        { name: 'Solar PV', value: breakdown.solarKw, pct: breakdown.solarPct, color: 'text-yellow-450 dark:text-yellow-600', bg: 'bg-yellow-500/8 border-yellow-500/15', barColor: 'bg-yellow-450 dark:bg-yellow-500' },
                        { name: 'Wind Turbine', value: breakdown.windKw, pct: breakdown.windPct, color: 'text-purple-450 dark:text-purple-600', bg: 'bg-purple-500/8 border-purple-500/15', barColor: 'bg-purple-450 dark:bg-purple-500' },
                        { name: 'Battery (BESS)', value: breakdown.batteryKw, pct: breakdown.batteryPct, color: 'text-emerald-450 dark:text-emerald-600', bg: 'bg-emerald-500/8 border-emerald-500/15', barColor: 'bg-emerald-450 dark:bg-emerald-500' },
                        { name: 'Utility Grid', value: breakdown.gridKw, pct: breakdown.gridPct, color: 'text-blue-450 dark:text-blue-600', bg: 'bg-blue-500/8 border-blue-500/15', barColor: 'bg-blue-450 dark:bg-blue-500' },
                      ].map((source, idx) => (
                        <div key={idx} className={`p-2.5 rounded-xl border ${source.bg}`}>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[9px] font-bold text-slate-400 dark:text-slate-600">{source.name}</span>
                            <span className={`text-[10px] font-extrabold ${source.color}`}>{source.pct}%</span>
                          </div>
                          <div className="flex items-baseline gap-0.5 mb-1.5">
                            <span className="text-sm font-extrabold font-mono text-white dark:text-slate-900">{source.value.toFixed(1)}</span>
                            <span className="text-[8px] text-slate-500 font-bold">kW</span>
                          </div>
                          <div className="w-full bg-slate-900/50 dark:bg-slate-350/50 h-1 rounded-full overflow-hidden">
                            <div className={`h-full ${source.barColor}`} style={{ width: `${source.pct}%` }}></div>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                {/* Quick Manual Isolation Switches */}
                <div className="w-full mt-4 border-t border-slate-800/50 dark:border-slate-300/50 pt-4">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div className="text-left shrink-0">
                      <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-650 tracking-wider block">Quick Feeder Isolation Controls</span>
                      <span className="text-[8.5px] text-slate-500 mt-0.5 block">Isolate or reconnect component loops in real time</span>
                    </div>
                    <div className="w-full grid grid-cols-2 md:grid-cols-4 gap-3 flex-1">
                      {[
                        { id: 'solar', label: 'Solar PV Array', enabled: solarEnabled, text: 'Solar PV' },
                        { id: 'wind', label: 'Wind Turbine', enabled: windEnabled, text: 'Wind Turbine' },
                        { id: 'battery', label: 'BESS Battery', enabled: batteryEnabled, text: 'BESS Battery' },
                        { id: 'grid', label: 'Utility Grid Tie', enabled: gridEnabled, text: 'Utility Grid' }
                      ].map((comp) => (
                        <div key={comp.id} className="bg-slate-950/45 dark:bg-slate-100 p-2 rounded-xl border border-slate-900 dark:border-slate-300 flex items-center justify-between gap-2.5">
                          <span className="text-[9px] font-bold text-slate-400 dark:text-slate-600 truncate">{comp.text}</span>
                          <button
                            onClick={() => handleComponentToggle(comp.id, !comp.enabled)}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className={`px-2.5 py-1 rounded-lg text-[9px] font-extrabold border transition-all shrink-0 disabled:opacity-40 disabled:cursor-not-allowed ${
                              comp.enabled
                                ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/35 hover:bg-emerald-600/25'
                                : 'bg-rose-600/15 text-rose-400 border-rose-500/35 hover:bg-rose-600/25'
                            }`}
                            title={userRole !== 'admin' && userRole !== 'engineer' ? "Requires Engineer or Admin credentials" : `Toggle ${comp.text}`}
                          >
                            {comp.enabled ? "ONLINE" : "ISOLATED"}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Dashboard Cooling Fan Override */}
                <div className="w-full mt-4 border-t border-slate-800/50 dark:border-slate-300/50 pt-4">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div className="text-left shrink-0">
                      <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-650 tracking-wider block">BESS Cooling Fan Override</span>
                      <span className="text-[8.5px] text-slate-500 mt-0.5 block">Manually turn BESS cabinet ventilation ON, OFF or set to AUTO</span>
                    </div>
                    <div className="flex gap-2 flex-1 justify-end">
                      {[
                        { value: null, label: 'AUTO (TEMP)' },
                        { value: 'ON', label: 'MANUAL ON' },
                        { value: 'OFF', label: 'MANUAL OFF' }
                      ].map((opt) => (
                        <button
                          key={opt.label}
                          onClick={() => handleFanOverrideToggle(opt.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className={`px-3 py-1.5 rounded-lg text-[9px] font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                            fanOverride === opt.value
                              ? 'bg-blue-600/20 text-blue-400 border-blue-500/50 hover:bg-blue-600/30'
                              : 'bg-slate-900/40 text-slate-400 border-slate-800 hover:bg-slate-900 dark:bg-white dark:border-slate-350 dark:hover:bg-slate-200'
                          }`}
                          title={userRole !== 'admin' && userRole !== 'engineer' ? "Requires Engineer or Admin credentials" : `Set Fan to ${opt.label}`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Grid of weather + carbon savings cards */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Weather widget (5 columns) */}
                <div className="lg:col-span-5 glass-panel p-4 flex flex-col justify-between">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider">Irradiance & Weather Twin</span>
                    <span className="text-[9px] bg-slate-900 text-amber-400 dark:bg-slate-200 px-2 py-0.5 rounded font-bold">Forecast Sync</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/25">
                        <Sun className="w-8 h-8 text-yellow-500 animate-pulse" />
                      </div>
                      <div>
                        <span className="text-2xl font-extrabold font-mono text-white dark:text-slate-900">{telemetry.ambient_temp.toFixed(1)}°C</span>
                        <span className="block text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Ambient Temperature</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="block text-[9px] text-slate-400 dark:text-slate-550 uppercase font-bold tracking-wide">Solar Irradiance</span>
                      <span className="font-mono text-sm font-extrabold text-amber-400 dark:text-amber-600">{(telemetry.Solar_Power * 12.5).toFixed(0)} W/m²</span>
                      <span className="block text-[8px] text-slate-550 mt-0.5">Cloud Cover: {(telemetry.cloud_cover * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {/* Carbon & sustainability Analytics (7 columns) */}
                <div className="lg:col-span-7 glass-panel p-4 grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="bg-slate-950/45 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-350">
                    <span className="block text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">CO₂ Footprint Offset</span>
                    <div className="flex items-baseline gap-1 mt-2">
                      <span className="text-lg font-extrabold font-mono text-emerald-400 dark:text-emerald-600">{carbonMetrics.co2_saved_kg.toFixed(1)}</span>
                      <span className="text-[9px] font-bold text-slate-500">kg</span>
                    </div>
                    <span className="text-[8px] text-slate-500 mt-1 block">0.45 kg/kWh Saved</span>
                  </div>

                  <div className="bg-slate-950/45 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-355">
                    <span className="block text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Renewable Penetration</span>
                    <div className="flex items-baseline gap-1 mt-2">
                      <span className="text-lg font-extrabold font-mono text-purple-400 dark:text-purple-600">{carbonMetrics.renewable_share_pct.toFixed(1)}</span>
                      <span className="text-[9px] font-bold text-slate-500">%</span>
                    </div>
                    <span className="text-[8px] text-slate-500 mt-1 block">Green Load Offset</span>
                  </div>

                  <div className="bg-slate-950/45 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-355 col-span-2 md:col-span-1">
                    <span className="block text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Tariff Savings Rate</span>
                    <div className="flex items-baseline gap-1 mt-2">
                      <span className="text-lg font-extrabold font-mono text-emerald-400 dark:text-emerald-600">{(telemetry.electricity_cost * 3600).toFixed(2)}</span>
                      <span className="text-[9px] font-bold text-slate-500">₹/hr</span>
                    </div>
                    <span className="text-[8px] text-slate-500 mt-1 block">Arbitrage Efficiency</span>
                  </div>
                </div>
              </div>

              {/* Real-time mini alarms ticker */}
              <div className="glass-panel p-3.5 flex items-center justify-between gap-4">
                <span className="text-[9px] font-extrabold uppercase text-slate-400 dark:text-slate-600 tracking-wider shrink-0 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-500 animate-pulse" /> Live Alarm Feed:
                </span>
                <div className="flex-1 overflow-hidden h-5 relative">
                  {activeAlarms.length > 0 ? (
                    <div className="absolute animate-marquee text-[10px] font-mono text-rose-400 font-bold uppercase truncate">
                      {activeAlarms.map(a => `[${a.severity}]: ${a.message}`).join("  |  ")}
                    </div>
                  ) : (
                    <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">ALL CORE FEEDERS ONLINE. NO ALARMS DETECTED.</span>
                  )}
                </div>
              </div>

              {/* Dynamic Faults & Solutions Dashboard Panel */}
              {activeAlarms.filter(a => a.status === 'ACTIVE').length > 0 && (
                <div className="glass-panel p-4 border border-rose-500/25 bg-rose-950/10 space-y-3.5">
                  <div className="flex items-center gap-2 border-b border-rose-500/20 pb-2">
                    <AlertTriangle className="w-4 h-4 text-rose-500 animate-pulse" />
                    <h4 className="text-xs uppercase font-extrabold tracking-wider text-rose-400 dark:text-rose-600">
                      Active System Faults &amp; Repair Solutions
                    </h4>
                    <span className="ml-auto text-[8px] bg-rose-500/20 text-rose-350 px-2 py-0.5 rounded font-mono font-bold">
                      {activeAlarms.filter(a => a.status === 'ACTIVE').length} FAULTS DETECTED
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {activeAlarms.filter(a => a.status === 'ACTIVE').map((alarm) => (
                      <div key={alarm.id} className="p-3 bg-slate-950/40 dark:bg-slate-100/80 border border-slate-900 dark:border-slate-250 rounded-xl space-y-2 text-xs">
                        <div className="flex justify-between items-center">
                          <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase font-mono ${
                            alarm.severity === 'CRITICAL' ? 'bg-rose-600 text-white animate-pulse' : 'bg-amber-500 text-slate-950'
                          }`}>{alarm.severity}</span>
                          {alarm.fault_code && (
                            <span className="px-2 py-0.5 rounded text-[8px] font-mono font-bold bg-slate-800 dark:bg-slate-200 border border-slate-700 dark:border-slate-350 text-slate-400 dark:text-slate-600">
                              {alarm.fault_code}
                            </span>
                          )}
                        </div>
                        <p className="font-extrabold text-slate-200 dark:text-slate-800 text-[11px] leading-snug">{alarm.message}</p>
                        
                        {alarm.root_cause && (
                          <div className="mt-1">
                            <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wide block">Root Cause Analysis</span>
                            <p className="text-[10px] text-slate-400 dark:text-slate-600 leading-snug">{alarm.root_cause}</p>
                          </div>
                        )}

                        {alarm.repair_actions && (
                          <div className="mt-1.5">
                            <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wide block mb-1">Recommended Repair Actions</span>
                            <div className="space-y-1">
                              {alarm.repair_actions.map((act, idx) => (
                                <div key={idx} className="flex gap-1.5 text-[9px] text-slate-300 dark:text-slate-600 leading-tight">
                                  <span className="text-[8px] font-bold text-slate-500">{idx+1}.</span>
                                  <span>{act.replace(/^\d+\.\s*/, '')}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {alarm.safety_warning && (
                          <p className="text-[9px] text-amber-500 leading-tight font-semibold mt-1 bg-amber-500/5 p-1 px-1.5 rounded border border-amber-500/10">
                            {alarm.safety_warning}
                          </p>
                        )}

                        <div className="flex gap-2 pt-2 border-t border-slate-850 dark:border-slate-200 mt-2">
                          <button
                            onClick={() => ackAlarm(alarm.id)}
                            className="flex-1 py-1 rounded bg-slate-900 hover:bg-slate-800 dark:bg-slate-200 dark:hover:bg-slate-300 text-[9px] font-bold text-slate-400 dark:text-slate-650 border border-slate-800 dark:border-slate-300"
                          >
                            Acknowledge
                          </button>
                          <button
                            onClick={() => repairAlarm(alarm.id)}
                            className="flex-1 py-1 rounded bg-emerald-800/30 hover:bg-emerald-800/50 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/20 text-[9px] font-bold text-emerald-400 dark:text-emerald-600 border border-emerald-700/30 dark:border-emerald-500/30"
                          >
                            🔧 Self-Repair
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: EMS CONTROL */}
          {activeTab === 'ems' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Digital Twin control panels */}
                <div className="lg:col-span-7 glass-panel p-4 space-y-4">
                  <div className="flex justify-between items-center border-b border-slate-800 dark:border-slate-200 pb-2 mb-2">
                    <div className="flex items-center gap-1.5">
                      <Sliders className="w-4 h-4 text-emerald-400" />
                      <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">Digital Twin Failure Simulators</h3>
                    </div>
                    <span className="text-[9px] bg-slate-900 text-rose-400 dark:bg-slate-200 px-2 py-0.5 rounded font-bold">HMI Control Overrides</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="bg-slate-950/45 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-350">
                      <span className="block text-[9px] font-extrabold uppercase text-slate-400 dark:text-slate-655 mb-2">Battery Runaway</span>
                      <button 
                        onClick={() => handleSimulateFailure("BATTERY_RUNAWAY", !telemetry.active_failures?.includes("BATTERY_RUNAWAY"))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className={`w-full py-2.5 rounded-lg text-[10px] font-extrabold border transition-all ${
                          telemetry.active_failures?.includes("BATTERY_RUNAWAY")
                            ? 'bg-rose-600 text-white border-rose-500 animate-pulse'
                            : 'bg-slate-900 hover:bg-slate-850 text-slate-400 dark:bg-slate-200 dark:text-slate-700 border-slate-850'
                        }`}
                      >
                        {telemetry.active_failures?.includes("BATTERY_RUNAWAY") ? "TRIGGERED" : "INJECT FAULT"}
                      </button>
                    </div>

                    <div className="bg-slate-950/45 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-350">
                      <span className="block text-[9px] font-extrabold uppercase text-slate-400 dark:text-slate-655 mb-2">Fan Lock Overtemp</span>
                      <button 
                        onClick={() => handleSimulateFailure("FAN_FAILURE", !telemetry.active_failures?.includes("FAN_FAILURE"))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className={`w-full py-2.5 rounded-lg text-[10px] font-extrabold border transition-all ${
                          telemetry.active_failures?.includes("FAN_FAILURE")
                            ? 'bg-rose-600 text-white border-rose-500 animate-pulse'
                            : 'bg-slate-900 hover:bg-slate-850 text-slate-400 dark:bg-slate-200 dark:text-slate-700 border-slate-850'
                        }`}
                      >
                        {telemetry.active_failures?.includes("FAN_FAILURE") ? "TRIGGERED" : "INJECT FAULT"}
                      </button>
                    </div>

                    <div className="bg-slate-950/45 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-350">
                      <span className="block text-[9px] font-extrabold uppercase text-slate-400 dark:text-slate-655 mb-2">Inverter Trip Fault</span>
                      <button 
                        onClick={() => handleSimulateFailure("INVERTER_FAULT", !telemetry.active_failures?.includes("INVERTER_FAULT"))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className={`w-full py-2.5 rounded-lg text-[10px] font-extrabold border transition-all ${
                          telemetry.active_failures?.includes("INVERTER_FAULT")
                            ? 'bg-rose-600 text-white border-rose-500 animate-pulse'
                            : 'bg-slate-900 hover:bg-slate-850 text-slate-400 dark:bg-slate-200 dark:text-slate-700 border-slate-850'
                        }`}
                      >
                        {telemetry.active_failures?.includes("INVERTER_FAULT") ? "TRIGGERED" : "INJECT FAULT"}
                      </button>
                    </div>
                  </div>

                  {/* Simulation mode override bar */}
                  <div className="border-t border-slate-800 dark:border-slate-200 pt-3 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[9px] font-extrabold uppercase text-slate-400 tracking-wider">Simulation Override Control</span>
                      <div className="flex gap-2">
                        <button
                          onClick={applyOverrides}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-slate-950 font-extrabold px-3 py-1 rounded-lg text-[9px] flex items-center gap-1"
                        >
                          <Play className="w-3 h-3" /> Apply
                        </button>
                        <button
                          onClick={resetOverrides}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 font-extrabold px-3 py-1 rounded-lg text-[9px] flex items-center gap-1"
                        >
                          <RotateCcw className="w-3 h-3" /> Reset
                        </button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Sim Mode</label>
                        <select
                          value={simulationMode}
                          onChange={(e) => setSimulationMode(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="w-full text-[9px] font-bold"
                        >
                          <option value="NORMAL">Normal</option>
                          <option value="FAULT">Fault</option>
                          <option value="STRESS">Stress</option>
                          <option value="NIGHT">Night</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Solar Override (kW)</label>
                        <input
                          type="number" placeholder="Auto"
                          value={solarOverride}
                          onChange={(e) => setSolarOverride(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="w-full text-[9px] font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Wind Override (kW)</label>
                        <input
                          type="number" placeholder="Auto"
                          value={windOverride}
                          onChange={(e) => setWindOverride(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="w-full text-[9px] font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Load Override (kW)</label>
                        <input
                          type="number" placeholder="Auto"
                          value={loadOverride}
                          onChange={(e) => setLoadOverride(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="w-full text-[9px] font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Live Real-Time Data Ingestion Control Card */}
                  <div className="border-t border-slate-800 dark:border-slate-200 pt-3 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[9px] font-extrabold uppercase text-slate-400 tracking-wider">Live Real-Time Data Ingestion</span>
                      <button
                        onClick={ingestLiveData}
                        disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-slate-950 font-extrabold px-3 py-1 rounded-lg text-[9px] flex items-center gap-1 transition-all"
                      >
                        <Zap className="w-3 h-3 animate-pulse" /> Ingest Live Telemetry
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Solar Gen (kW)</label>
                        <input
                          type="number" step="0.1" min="0"
                          value={liveSolar}
                          onChange={(e) => setLiveSolar(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>
                      
                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Wind Gen (kW)</label>
                        <input
                          type="number" step="0.1" min="0"
                          value={liveWind}
                          onChange={(e) => setLiveWind(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Load Demand (kW)</label>
                        <input
                          type="number" step="0.1" min="0"
                          value={liveLoadDemand}
                          onChange={(e) => setLiveLoadDemand(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Grid Power (kW)</label>
                        <input
                          type="number" step="0.1"
                          value={liveGridPower}
                          placeholder="+ Import / - Export"
                          onChange={(e) => setLiveGridPower(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">BESS Temp (°C)</label>
                        <input
                          type="number" step="0.5"
                          value={liveBatteryTemp}
                          onChange={(e) => setLiveBatteryTemp(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">BESS Current (A)</label>
                        <input
                          type="number" step="0.1"
                          value={liveBatteryCurrent}
                          placeholder="+ Chg / - Dischg"
                          onChange={(e) => setLiveBatteryCurrent(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">Grid Status</label>
                        <select
                          value={liveGridStatus}
                          onChange={(e) => setLiveGridStatus(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-bold bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        >
                          <option value="1">CONNECTED</option>
                          <option value="0">OUTAGE</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[8px] uppercase font-bold text-slate-500 block mb-1">BESS SOC (%)</label>
                        <input
                          type="number" min="0" max="100" placeholder="Auto"
                          value={liveBatterySOC}
                          onChange={(e) => setLiveBatterySOC(e.target.value)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer' && userRole !== 'operator'}
                          className="w-full text-[9px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Grid Component Manual Switches */}
                  <div className="border-t border-slate-800 dark:border-slate-200 pt-3 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[9px] font-extrabold uppercase text-slate-400 tracking-wider">Manual Component Isolation Switches</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {[
                        { id: 'solar', label: 'Solar PV Array', enabled: solarEnabled },
                        { id: 'wind', label: 'Wind Turbine', enabled: windEnabled },
                        { id: 'battery', label: 'BESS Battery', enabled: batteryEnabled },
                        { id: 'grid', label: 'Utility Grid Tie', enabled: gridEnabled },
                      ].map((comp) => (
                        <div key={comp.id} className="bg-slate-950/45 dark:bg-slate-100 p-2.5 rounded-xl border border-slate-900 dark:border-slate-350 flex flex-col justify-between">
                          <span className="text-[8px] uppercase font-bold text-slate-500 block mb-2">{comp.label}</span>
                          <button
                            onClick={() => handleComponentToggle(comp.id, !comp.enabled)}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className={`w-full py-1.5 rounded-lg text-[9px] font-extrabold border transition-all ${
                              comp.enabled
                                ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                                : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                            }`}
                          >
                            {comp.enabled ? "ONLINE (ON)" : "OFF (ISOLATED)"}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* AI Optimization recommendations */}
                <div className="lg:col-span-5 space-y-4">
                  <div className="glass-panel p-4 flex flex-col justify-between">
                    <div className="flex justify-between items-center border-b border-slate-800 dark:border-slate-200 pb-2 mb-2">
                      <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider">AI Optimizer Recommendations</span>
                      <span className="text-[9px] bg-slate-900 text-emerald-400 dark:bg-slate-200 px-2 py-0.5 rounded font-bold">Q-Learning Dispatch</span>
                    </div>
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-300 font-mono text-[9px] text-slate-300 dark:text-slate-700 space-y-2">
                      <div className="flex justify-between border-b border-slate-900/10 pb-1">
                        <span>Optimization Policy:</span>
                        <span className="text-white dark:text-slate-900 font-extrabold">{settings.optimization_mode}</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-900/10 pb-1">
                        <span>Dispatch Policy Status:</span>
                        <span className="text-emerald-400 dark:text-emerald-600 font-extrabold">{telemetry.ems_action}</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-900/10 pb-1">
                        <span>EMS Action Timestamp:</span>
                        <span className="text-slate-450 dark:text-slate-600 font-bold">{new Date(telemetry.timestamp * 1000).toLocaleTimeString()}</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-900/10 pb-1">
                        <span>Calculated Action Recommendation:</span>
                        <span className="text-amber-400 dark:text-amber-605 font-bold">
                          {telemetry.ems_action === "BATTERY_SUPPORT" ? "Discharge BESS to shave peak load costs." :
                           telemetry.ems_action === "PEAK_SHAVING_DISCHARGE" ? "Peak shaving active: discharge BESS to avoid high demand charges." :
                           telemetry.ems_action === "RENEWABLE_CHARGE" ? "Charge BESS with surplus green power." :
                           telemetry.ems_action === "GRID_EXPORT" ? "Export surplus energy to utility grid." :
                           telemetry.ems_action === "GRID_CHARGING_OFFPEAK" ? "Off-peak grid charging active." :
                           telemetry.ems_action === "GRID_FALLBACK" ? "Renewable deficit: fallback importing power from utility grid." :
                           telemetry.ems_action === "BESS_DISCONNECTED" ? "BESS Battery isolated. Supplying load directly with renewables and grid fallback." :
                           telemetry.ems_action === "BESS_DISCONNECTED_EXPORT" ? "BESS isolated. Supplying load directly from renewables; surplus exported to grid." :
                           telemetry.ems_action === "BESS_DISCONNECTED_LIMIT" ? "BESS isolated. Supplying load directly from renewables; surplus power curtailed." :
                           telemetry.ems_action === "BESS_DISCONNECTED_FALLBACK" ? "BESS isolated. Supplying load directly from renewables; deficit met by grid." :
                           telemetry.ems_action === "BESS_DISCONNECTED_ISLAND_BALANCED" ? "BESS isolated. Island mode: load fully supplied directly by solar/wind." :
                           telemetry.ems_action === "BESS_DISCONNECTED_ISLAND_LOAD_SHED" ? "BESS isolated. Island mode: load shed to match solar/wind capacity." :
                           telemetry.ems_action === "ISLANDED_BLACKOUT" ? "CRITICAL: Grid and BESS offline! System in blackout, critical load only." :
                           telemetry.ems_action === "ISLAND_CHARGE" ? "Island mode: charging BESS with surplus renewables." :
                           telemetry.ems_action === "ISLAND_DISCHARGE" ? "Island mode: discharging BESS to meet load demand." :
                           telemetry.ems_action === "ISLAND_BALANCED" ? "Island mode: balanced load supply with local generation." :
                           telemetry.ems_action === "ISLAND_LOAD_SHED" ? "Island mode warning: low SOC, critical load shedding active." :
                           "Hold standby configuration."}
                        </span>
                      </div>
                      <div className="flex flex-col pt-1">
                        <span className="text-slate-400 dark:text-slate-500 font-bold">Load Supply Breakdown:</span>
                        <span className="text-slate-200 dark:text-slate-850 mt-1 font-bold">
                          {(() => {
                            const breakdown = calculateLoadSourceBreakdown();
                            const supplies = [];
                            if (breakdown.solarKw > 0) supplies.push(`Solar: ${breakdown.solarKw} kW (${breakdown.solarPct}%)`);
                            if (breakdown.windKw > 0) supplies.push(`Wind: ${breakdown.windKw} kW (${breakdown.windPct}%)`);
                            if (breakdown.batteryKw > 0) supplies.push(`BESS: ${breakdown.batteryKw} kW (${breakdown.batteryPct}%)`);
                            if (breakdown.gridKw > 0) supplies.push(`Grid: ${breakdown.gridKw} kW (${breakdown.gridPct}%)`);
                            return supplies.length > 0 ? supplies.join(" | ") : "0 kW supplied";
                          })()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Live Protocol Terminal */}
                  <div className="glass-panel p-4">
                    <div className="flex justify-between items-center border-b border-slate-800 pb-2 mb-3">
                      <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">Live Protocol Monitor</span>
                      <div className="flex gap-1">
                        {['can', 'modbus', 'opcua', 'iec'].map(tab => (
                          <button key={tab} onClick={() => setProtocolTab(tab)}
                            className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase transition-all ${
                              protocolTab === tab ? 'bg-emerald-500 text-slate-950' : 'bg-slate-900 text-slate-500 hover:text-white'
                            }`}
                          >{tab}</button>
                        ))}
                      </div>
                    </div>
                    <div className="bg-slate-950 rounded-xl border border-slate-900 p-3 font-mono text-[9px] min-h-[90px] max-h-[130px] overflow-y-auto">
                      {protocolTab === 'can' && (
                        <div className="space-y-1">
                          <div className="text-emerald-400 data-blink">► CAN BUS LIVE DATA FRAME</div>
                          <div className="text-slate-400">{protocolData?.can || 'Connecting to CAN bus...'}</div>
                          <div className="text-slate-500 text-[8px] mt-1">Baud: 500kbps | Protocol: SAE J1939</div>
                        </div>
                      )}
                      {protocolTab === 'modbus' && (
                        <div className="space-y-0.5">
                          <div className="text-blue-400 mb-1">► MODBUS TCP REGISTER MAP</div>
                          {protocolData?.modbus ? Object.entries(protocolData.modbus).map(([reg, val]) => (
                            <div key={reg} className="flex justify-between">
                              <span className="text-slate-500">REG {reg}:</span>
                              <span className="text-slate-300">{String(val)}</span>
                            </div>
                          )) : <div className="text-slate-500">Polling Modbus registers...</div>}
                        </div>
                      )}
                      {protocolTab === 'opcua' && (
                        <div className="space-y-0.5">
                          <div className="text-amber-400 mb-1">► OPC UA NODE DATA</div>
                          {protocolData?.opc ? Object.entries(protocolData.opc).slice(0, 8).map(([node, val]) => (
                            <div key={node} className="flex justify-between gap-2">
                              <span className="text-slate-500 truncate">{node.split('.').pop()}:</span>
                              <span className="text-slate-300 shrink-0">{Number(val).toFixed(2)}</span>
                            </div>
                          )) : <div className="text-slate-500">Connecting to OPC UA server...</div>}
                        </div>
                      )}
                      {protocolTab === 'iec' && (
                        <div className="space-y-0.5">
                          <div className="text-purple-400 mb-1">► IEC 61850 GOOSE/MMS NODES</div>
                          {protocolData?.iec61850 ? Object.entries(protocolData.iec61850).map(([node, val]) => (
                            <div key={node} className="flex justify-between gap-2">
                              <span className="text-slate-500 truncate">{node}:</span>
                              <span className="text-slate-300 shrink-0">{String(val)}</span>
                            </div>
                          )) : <div className="text-slate-500">IEC 61850 MMS server offline.</div>}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* EMS live chart */}
              <div className="glass-panel p-4">
                <div className="flex items-center gap-1.5 mb-3 border-b border-slate-800 pb-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-[10px] font-bold text-slate-300 uppercase tracking-wide">Real-Time Power Flow Trends</h4>
                </div>
                <div className="h-[200px] w-full" style={{minHeight:'200px'}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={liveChartData}>
                      <defs>
                        <linearGradient id="emsS" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="emsW" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="emsL" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={8} />
                      <YAxis stroke="#64748b" fontSize={8} unit=" kW" />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '9px' }} />
                      <Legend wrapperStyle={{ fontSize: '9px' }} />
                      <Area type="monotone" dataKey="solar" stroke="#eab308" strokeWidth={1.5} fillOpacity={1} fill="url(#emsS)" name="Solar (kW)" />
                      <Area type="monotone" dataKey="wind" stroke="#a855f7" strokeWidth={1.5} fillOpacity={1} fill="url(#emsW)" name="Wind (kW)" />
                      <Area type="monotone" dataKey="load" stroke="#f43f5e" strokeWidth={2} fillOpacity={1} fill="url(#emsL)" name="Load (kW)" />
                      <Line type="monotone" dataKey="grid" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Grid (kW)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: BATTERY */}
          {activeTab === 'battery' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* 10x10 thermal heatmap grid (7 columns) */}
                <div className="lg:col-span-7 glass-panel p-4">
                  {renderBatteryHeatmap()}
                </div>

                {/* Circular SOC and health indicators (5 columns) */}
                <div className="lg:col-span-5 glass-panel p-4 flex flex-col justify-between">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider">BESS Vitals Monitor</span>
                    <span className="text-[9px] bg-slate-900 text-emerald-400 dark:bg-slate-200 px-2 py-0.5 rounded font-bold">Pack Health</span>
                  </div>

                  <div className="flex flex-col items-center py-2.5">
                    {/* SOC Gauge */}
                    <div className="relative w-28 h-28 flex items-center justify-center">
                      <svg className="absolute w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                        <circle cx="50" cy="50" r="42" fill="none" stroke="#10b981" strokeWidth="6"
                                strokeDasharray={263.89}
                                strokeDashoffset={263.89 - (263.89 * telemetry.Battery_SOC) / 100}
                                className="transition-all duration-500 ease-out" />
                      </svg>
                      <div className="text-center font-mono z-10">
                        <span className="text-2xl font-extrabold text-white dark:text-slate-900">{telemetry.Battery_SOC.toFixed(1)}%</span>
                        <span className="block text-[8px] text-slate-500 font-bold uppercase mt-0.5">Charge Level</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-3.5">
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-2 border border-slate-900 dark:border-slate-350 rounded-xl text-[9.5px]">
                      <span className="text-slate-450 dark:text-slate-550 block font-bold">SOH:</span>
                      <span className="font-mono text-xs font-extrabold text-white dark:text-slate-900">{Math.round(telemetry.Battery_SOH)}%</span>
                    </div>
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-2 border border-slate-900 dark:border-slate-350 rounded-xl text-[9.5px]">
                      <span className="text-slate-450 dark:text-slate-550 block font-bold">Temperature:</span>
                      <span className="font-mono text-xs font-extrabold text-white dark:text-slate-900">{telemetry.Battery_Temperature.toFixed(1)}°C</span>
                    </div>
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-2 border border-slate-900 dark:border-slate-350 rounded-xl text-[9.5px]">
                      <span className="text-slate-450 dark:text-slate-550 block font-bold">Cooling Fan:</span>
                      <span className={`font-mono text-xs font-extrabold block ${
                        telemetry.Battery_Fan_Status === "FAULTED" ? "text-rose-500 animate-pulse" :
                        telemetry.Battery_Fan_Status === "ON" ? "text-emerald-400" :
                        "text-slate-400"
                      }`}>{telemetry.Battery_Fan_Status || "OFF"}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: RENEWABLE */}
          {activeTab === 'renewable' && (
            <div className="space-y-5">
              {/* Renewable KPI stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Solar Generation', value: telemetry.Solar_Power.toFixed(2), unit: 'kW', pct: Math.min(100, (telemetry.Solar_Power / 80) * 100), color: '#eab308', bg: 'rgba(234,179,8,0.1)' },
                  { label: 'Wind Generation', value: telemetry.Wind_Power.toFixed(2), unit: 'kW', pct: Math.min(100, (telemetry.Wind_Power / 45) * 100), color: '#a855f7', bg: 'rgba(168,85,247,0.1)' },
                  { label: 'Combined Output', value: (telemetry.Solar_Power + telemetry.Wind_Power).toFixed(2), unit: 'kW', pct: Math.min(100, ((telemetry.Solar_Power + telemetry.Wind_Power) / 125) * 100), color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
                  { label: 'Renewable Share', value: Math.min(100, Math.round(((telemetry.Solar_Power + telemetry.Wind_Power) / (telemetry.Load_Demand || 1)) * 100)).toString(), unit: '%', pct: Math.min(100, ((telemetry.Solar_Power + telemetry.Wind_Power) / (telemetry.Load_Demand || 1)) * 100), color: '#06b6d4', bg: 'rgba(6,182,212,0.1)' },
                ].map((item, i) => (
                  <div key={i} className="glass-panel p-3">
                    <span className="text-[8px] font-bold uppercase text-slate-500 tracking-wider block">{item.label}</span>
                    <div className="flex items-baseline gap-1 my-1.5">
                      <span className="text-xl font-extrabold font-mono" style={{ color: item.color }}>{item.value}</span>
                      <span className="text-[9px] text-slate-500">{item.unit}</span>
                    </div>
                    <div className="w-full bg-slate-900/60 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full progress-bar transition-all duration-700" style={{ width: `${item.pct.toFixed(0)}%`, backgroundColor: item.color }}></div>
                    </div>
                    <span className="text-[8px] text-slate-600 font-mono mt-0.5 block">{item.pct.toFixed(0)}% of rated capacity</span>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Generation specs cards */}
                <div className="lg:col-span-4 glass-panel p-4 space-y-4">
                  <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider mb-2.5 block border-b border-slate-800 pb-1">Renewable Sources Vitals</span>
                  
                  {/* Solar detail block */}
                  <div className="bg-slate-950/40 dark:bg-slate-100 p-3 rounded-xl border border-yellow-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <Sun className="w-4 h-4 text-yellow-400 pulse-glow" />
                      <span className="text-[9px] font-extrabold uppercase text-yellow-400">Solar PV Generation</span>
                      <span className="status-led online ml-auto"></span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 text-[9px] font-mono">
                      {[
                        ['Output Power', `${telemetry.Solar_Power.toFixed(2)} kW`],
                        ['DC Voltage', `${telemetry.Solar_Voltage.toFixed(0)} V`],
                        ['DC Current', `${telemetry.Solar_Current.toFixed(1)} A`],
                        ['Module Temp', `${telemetry.Solar_Temperature.toFixed(1)} °C`],
                        ['Irradiance', `${(telemetry.Solar_Power * 12.5).toFixed(0)} W/m²`],
                        ['MPPT Eff.', '99.1 %'],
                      ].map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-slate-500">{k}:</span>
                          <span className="text-slate-300 font-bold">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Wind detail block */}
                  <div className="bg-slate-950/40 dark:bg-slate-100 p-3 rounded-xl border border-purple-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <Wind className="w-4 h-4 text-purple-400 spin-slow" />
                      <span className="text-[9px] font-extrabold uppercase text-purple-400">Wind Turbine Generation</span>
                      <span className={`status-led ml-auto ${telemetry.Wind_Power > 0 ? 'online' : 'warning'}`}></span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 text-[9px] font-mono">
                      {[
                        ['Output Power', `${telemetry.Wind_Power.toFixed(2)} kW`],
                        ['Rotor Speed', `${telemetry.Wind_RPM.toFixed(0)} RPM`],
                        ['Wind Speed', `${telemetry.Wind_Speed.toFixed(1)} m/s`],
                        ['Cp Coefficient', '0.42'],
                        ['Gen. Temp', `${(38.5 + telemetry.Wind_Power * 0.12).toFixed(1)} °C`],
                        ['Pitch Angle', `${(telemetry.Wind_Power > 0 ? 8.5 : 90).toFixed(1)}°`],
                      ].map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-slate-500">{k}:</span>
                          <span className="text-slate-300 font-bold">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Live trend chart */}
                <div className="lg:col-span-8 glass-panel p-4">
                  <div className="flex items-center gap-1.5 mb-3 border-b border-slate-800 dark:border-slate-200 pb-2">
                    <Sun className="w-4 h-4 text-yellow-500" />
                    <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide">Solar & Wind Generation Trends (Live)</h4>
                  </div>
                  <div className="h-[260px] w-full" style={{minHeight:'260px'}}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={liveChartData}>
                        <defs>
                          <linearGradient id="renS" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#eab308" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="renW" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="time" stroke="#64748b" fontSize={8} />
                        <YAxis stroke="#64748b" fontSize={8} unit=" kW" />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '9px' }} />
                        <Legend wrapperStyle={{ fontSize: '9px' }} />
                        <Area type="monotone" dataKey="solar" stroke="#eab308" strokeWidth={2} fillOpacity={1} fill="url(#renS)" name="Solar Output (kW)" />
                        <Area type="monotone" dataKey="wind" stroke="#a855f7" strokeWidth={2} fillOpacity={1} fill="url(#renW)" name="Wind Output (kW)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: GRID */}
          {activeTab === 'grid' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Grid import/export details */}
                <div className="lg:col-span-5 glass-panel p-4 space-y-4">
                  <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-600 tracking-wider mb-2.5 block border-b border-slate-800 pb-1">Utility Grid Status</span>
                  
                  <div className="bg-slate-950/40 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-350 space-y-1">
                    <span className="text-[8.5px] text-slate-450 dark:text-slate-550 block font-bold uppercase">Grid Tie Power</span>
                    <div className="flex justify-between items-baseline">
                      <span className="font-mono text-base font-extrabold text-white dark:text-slate-900">
                        {telemetry.Grid_Power > 0 ? `Import: ${telemetry.Grid_Power.toFixed(2)}` : telemetry.Grid_Power < 0 ? `Export: ${Math.abs(telemetry.Grid_Power).toFixed(2)}` : '0.00'}
                      </span>
                      <span className="text-[9px] font-semibold text-slate-500">kW</span>
                    </div>
                  </div>

                  <div className="bg-slate-950/40 dark:bg-slate-100 p-3 rounded-xl border border-slate-900 dark:border-slate-350 space-y-1">
                    <span className="text-[8.5px] text-slate-450 dark:text-slate-550 block font-bold uppercase">Grid Voltage & Frequency</span>
                    <div className="flex justify-between items-baseline">
                      <span className="font-mono text-base font-extrabold text-white dark:text-slate-900">{telemetry.Grid_Voltage.toFixed(0)} V</span>
                      <span className="text-[9px] font-semibold text-slate-500">{telemetry.Grid_Frequency.toFixed(3)} Hz</span>
                    </div>
                  </div>
                </div>

                {/* Grid chart */}
                <div className="lg:col-span-7 glass-panel p-4">
                  <div className="flex items-center gap-1.5 mb-3 border-b border-slate-800 dark:border-slate-200 pb-2">
                    <Zap className="w-4 h-4 text-blue-500" />
                    <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide">Grid Tie Import/Export Trends (24h)</h4>
                  </div>
                  <div className="h-[210px] w-full" style={{minHeight:'210px'}}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={liveChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="time" stroke="#64748b" fontSize={8} />
                        <YAxis stroke="#64748b" fontSize={8} />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '9px' }} />
                        <Legend wrapperStyle={{ fontSize: '9px' }} />
                        <Line type="monotone" dataKey="grid" stroke="#3b82f6" strokeWidth={2.5} dot={false} name="Grid Active Power (kW)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: AI ANALYTICS */}
          {activeTab === 'ai' && (
            <div className="space-y-5">
              <div className="glass-panel p-4">
                <div className="flex justify-between items-center mb-3.5 border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <h4 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">24-Hour Predictive AI Dispatch & Load Forecast</h4>
                  </div>
                  <span className="text-[9px] bg-slate-900 text-emerald-400 dark:bg-slate-200 px-2 py-0.5 rounded font-bold">XGBoost & LSTM Forecast</span>
                </div>

                <div className="h-[230px] w-full" style={{minHeight:'230px'}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={forecastExtended}>
                      <defs>
                        <linearGradient id="solF" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#eab308" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#eab308" stopOpacity={0.0}/>
                        </linearGradient>
                        <linearGradient id="ldF" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis dataKey="hour" stroke="#64748b" fontSize={8} tickFormatter={(h) => `${h.toString().padStart(2, '0')}:00`} />
                      <YAxis stroke="#64748b" fontSize={8} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '9px' }} />
                      <Legend wrapperStyle={{ fontSize: '9px' }} />
                      <Area type="monotone" dataKey="solar" stroke="#eab308" strokeWidth={1.5} fillOpacity={1} fill="url(#solF)" name="Forecasted Solar (kW)" />
                      <Area type="monotone" dataKey="load" stroke="#f43f5e" strokeWidth={1.5} fillOpacity={1} fill="url(#ldF)" name="Forecasted Load Demand (kW)" />
                      <Line type="monotone" dataKey="battery_soc" stroke="#10b981" strokeWidth={2} dot={false} name="Forecasted Battery SOC (%)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: ALARMS */}
          {activeTab === 'alarms' && (() => {
            const criticalCount = activeAlarms.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE').length;
            const warningCount  = activeAlarms.filter(a => a.severity === 'WARNING'  && a.status === 'ACTIVE').length;
            const ackCount      = activeAlarms.filter(a => a.status === 'ACKNOWLEDGED').length;
            const filteredAlarms = activeAlarms.filter(a => {
              if (alarmFilter === 'ALL') return a.status !== 'CLEARED';
              if (alarmFilter === 'CRITICAL') return a.severity === 'CRITICAL' && a.status === 'ACTIVE';
              if (alarmFilter === 'WARNING')  return a.severity === 'WARNING'  && a.status === 'ACTIVE';
              if (alarmFilter === 'ACKNOWLEDGED') return a.status === 'ACKNOWLEDGED';
              return true;
            });

            return (
              <div className="space-y-5">
                {/* ── Header + Filters ── */}
                <div className="glass-panel p-4">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 mb-4 border-b border-slate-800 dark:border-slate-300 pb-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-500 animate-pulse" />
                      <h4 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">
                        Supervisory Alarm &amp; Fault Advisor
                      </h4>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {[
                        { key: 'ALL',          label: `All (${activeAlarms.filter(a=>a.status!=='CLEARED').length})`,   cls: 'bg-slate-800 dark:bg-slate-200 text-slate-200 dark:text-slate-700 border-slate-700 dark:border-slate-300' },
                        { key: 'CRITICAL',     label: `Critical (${criticalCount})`,  cls: 'bg-rose-900/60 text-rose-300 border-rose-700/40' },
                        { key: 'WARNING',      label: `Warning (${warningCount})`,    cls: 'bg-amber-900/60 text-amber-300 border-amber-700/40' },
                        { key: 'ACKNOWLEDGED', label: `Ack'd (${ackCount})`,          cls: 'bg-slate-800 dark:bg-slate-200 text-slate-400 dark:text-slate-500 border-slate-700' },
                      ].map(f => (
                        <button
                          key={f.key}
                          onClick={() => setAlarmFilter(f.key)}
                          className={`px-3 py-1 rounded-lg text-[10px] font-extrabold border transition-all ${f.cls} ${alarmFilter === f.key ? 'ring-2 ring-offset-1 ring-offset-slate-950 ring-rose-400' : 'opacity-60 hover:opacity-100'}`}
                        >{f.label}</button>
                      ))}
                    </div>
                  </div>

                  {/* ── Alarm List ── */}
                  <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1 text-xs">
                    {filteredAlarms.length > 0 ? filteredAlarms.map((alarm) => (
                      <AlarmRow
                        key={alarm.id}
                        alarm={alarm}
                        userRole={userRole}
                        ackAlarm={ackAlarm}
                        clearAlarm={clearAlarm}
                        repairAlarm={repairAlarm}
                      />
                    )) : (
                      <div className="bg-slate-950/30 dark:bg-slate-100 p-8 rounded-xl border border-slate-900 dark:border-slate-300 text-center font-bold text-emerald-400 uppercase tracking-wider">
                        {alarmFilter === 'ALL'
                          ? '✅ No active microgrid anomalies. All nodes online.'
                          : `No ${alarmFilter.toLowerCase()} alarms found.`}
                      </div>
                    )}
                  </div>
                </div>

                {/* ── System Health Summary ── */}
                <div className="glass-panel p-4">
                  <p className="text-[9px] uppercase font-extrabold tracking-widest text-slate-500 mb-3">🩺 Fault Advisor — System Health Summary</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    {[
                      { label: 'Active CRITICAL', value: criticalCount, color: criticalCount > 0 ? 'text-rose-400' : 'text-emerald-400', bg: criticalCount > 0 ? 'bg-rose-950/40 border-rose-800/40' : 'bg-emerald-950/30 border-emerald-900/30' },
                      { label: 'Active WARNING',  value: warningCount,  color: warningCount  > 0 ? 'text-amber-400' : 'text-emerald-400', bg: warningCount  > 0 ? 'bg-amber-950/40 border-amber-800/40' : 'bg-emerald-950/30 border-emerald-900/30' },
                      { label: 'Acknowledged',    value: ackCount,      color: 'text-slate-400', bg: 'bg-slate-900/40 border-slate-800/40' },
                      { label: 'Overall Status',  value: criticalCount > 0 ? 'FAULT' : warningCount > 0 ? 'WARNING' : 'HEALTHY', color: criticalCount > 0 ? 'text-rose-400' : warningCount > 0 ? 'text-amber-400' : 'text-emerald-400', bg: 'bg-slate-900/40 border-slate-800/40' },
                    ].map((item, i) => (
                      <div key={i} className={`p-3 rounded-xl border ${item.bg}`}>
                        <p className="text-[8px] text-slate-500 uppercase font-bold tracking-wider mb-1">{item.label}</p>
                        <p className={`text-lg font-extrabold font-mono ${item.color}`}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })()}


          {/* TAB 8: REPORTS */}
          {activeTab === 'reports' && (
            <div className="space-y-5">
              <div className="glass-panel p-5 space-y-4 print:p-0 print:border-none print:shadow-none print-only">
                <div className="flex justify-between items-center border-b border-slate-850 pb-3 mb-2 no-print">
                  <div className="flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">Microgrid System Savings & Sustainability Report</h3>
                  </div>
                  
                  {/* PDF Print Trigger */}
                  <button 
                    onClick={() => window.print()}
                    className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-extrabold px-3 py-1.5 rounded-lg text-[10px] uppercase shadow transition-all flex items-center gap-1"
                  >
                    <Database className="w-3.5 h-3.5" /> Export PDF Report
                  </button>
                </div>

                <div className="font-sans text-xs space-y-4">
                  {/* Corporate header details for print view */}
                  <div className="border-b border-slate-900 pb-3 space-y-1">
                    <h2 className="text-base font-extrabold uppercase text-slate-200 dark:text-slate-850">Apex Microgrid Audit Summary</h2>
                    <div className="flex flex-wrap gap-x-6 text-[10px] text-slate-500 font-medium uppercase font-mono">
                      <span>Report Timestamp: {new Date().toLocaleString()}</span>
                      <span>Auditor: System Operator Role ({userRole})</span>
                    </div>
                  </div>

                  {/* Auditor table */}
                  <table className="w-full text-left text-xs font-mono border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-500 uppercase tracking-wider text-[10px]">
                        <th className="py-2.5">Indicator Parameter</th>
                        <th className="py-2.5">Unit</th>
                        <th className="py-2.5 text-right">Registered Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900/40 text-slate-300 dark:text-slate-700">
                      <tr>
                        <td className="py-3 font-semibold">Total Green Energy Generated (Solar + Wind)</td>
                        <td className="py-3">kWh</td>
                        <td className="py-3 text-right font-bold text-white dark:text-slate-900">
                          {((cumulativeEnergy.solar + cumulativeEnergy.wind)).toFixed(2)}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Equivalent CO₂ Footprint Saved</td>
                        <td className="py-3">kg CO₂</td>
                        <td className="py-3 text-right font-bold text-emerald-400 dark:text-emerald-600">
                          {carbonMetrics.co2_saved_kg.toFixed(2)}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Average Clean Energy Penetration Offset</td>
                        <td className="py-3">%</td>
                        <td className="py-3 text-right font-bold text-purple-400 dark:text-purple-600">
                          {carbonMetrics.renewable_share_pct.toFixed(1)}%
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Total Cumulative Grid Imports</td>
                        <td className="py-3">kWh</td>
                        <td className="py-3 text-right font-bold text-white dark:text-slate-900">
                          {carbonMetrics.grid_import_kwh.toFixed(2)}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Total Cumulative Grid Exports</td>
                        <td className="py-3">kWh</td>
                        <td className="py-3 text-right font-bold text-white dark:text-slate-900">
                          {(carbonMetrics.grid_export_kwh || 0).toFixed(2)}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Calculated Tariff Arbitrage Savings Rate</td>
                        <td className="py-3">₹/hr</td>
                        <td className="py-3 text-right font-bold text-emerald-400 dark:text-emerald-600">
                          ₹{(telemetry.electricity_cost * 3600).toFixed(2)}
                        </td>
                      </tr>
                    </tbody>
                  </table>

                  <div className="mt-4 flex justify-end gap-2.5">
                    <a
                      href={`${API_BASE}/api/export/grid-exports`}
                      download
                      className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[9px] font-extrabold bg-blue-600 hover:bg-blue-500 text-white transition-all shadow hover:shadow-lg hover:shadow-blue-500/20"
                    >
                      <Download className="w-3 h-3" /> Download Grid Exports (CSV)
                    </a>
                    <a
                      href={`${API_BASE}/api/export/full-telemetry`}
                      download
                      className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[9px] font-extrabold bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-all shadow hover:shadow-lg hover:shadow-emerald-500/20"
                    >
                      <Database className="w-3 h-3" /> Download Full Telemetry (CSV)
                    </a>
                  </div>

                  
                  <div className="pt-5 border-t border-slate-900/40 text-[9px] text-slate-500 font-mono mt-4">
                    * This is a dynamically generated microgrid operations telemetry report saved under the scada_historian database engine.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 9: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* EMS Optimization Settings */}
                <div className="lg:col-span-6 glass-panel p-5 space-y-4">
                  <div className="flex items-center gap-1.5 border-b border-slate-800 pb-2">
                    <Settings className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">System Optimization Configurations</h3>
                  </div>

                  {userRole !== 'admin' && userRole !== 'engineer' && (
                    <div className="bg-rose-950/40 border border-rose-900/60 rounded-xl p-3 text-rose-300 flex items-start gap-2.5">
                      <ShieldAlert className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                      <div>
                        <span className="font-bold block text-[10px] uppercase tracking-wide">Read-Only Operator Level</span>
                        <p className="text-[9px] text-rose-450 mt-0.5">
                          You must request authentication authorization as an Engineer or Administrator to toggle optimization and simulation settings.
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">EMS Optimization Mode:</label>
                      <select
                        value={settings.optimization_mode}
                        onChange={(e) => setSettings(prev => ({ ...prev, optimization_mode: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-bold"
                      >
                        <option value="NORMAL">Normal Operation (Tariff Arbitrage)</option>
                        <option value="MAX_GREEN">Max Renewable Self-Consumption</option>
                        <option value="BATTERY_SAVE">Preserve Battery Lifespan (Low Discharge)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">Grid Export Settings:</label>
                      <select
                        value={settings.export_enabled}
                        onChange={(e) => setSettings(prev => ({ ...prev, export_enabled: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-bold"
                      >
                        <option value="true">Allowed (Feed-In Tariff)</option>
                        <option value="false">Lockout (Zero Export Limit)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">Peak Billing Tariff (₹/kWh):</label>
                      <input 
                        type="number"
                        step="0.01"
                        value={settings.tariff_peak_rate}
                        onChange={(e) => setSettings(prev => ({ ...prev, tariff_peak_rate: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-mono font-bold"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">Off-Peak Billing Tariff (₹/kWh):</label>
                      <input 
                        type="number"
                        step="0.01"
                        value={settings.tariff_offpeak_rate}
                        onChange={(e) => setSettings(prev => ({ ...prev, tariff_offpeak_rate: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-mono font-bold"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">Min Battery SOC Guard (%):</label>
                      <input 
                        type="number"
                        min="5" max="50"
                        value={settings.battery_min_soc}
                        onChange={(e) => setSettings(prev => ({ ...prev, battery_min_soc: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-mono font-bold"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-450 mb-1 font-semibold uppercase tracking-wider text-[9px]">Max Battery SOC Limit (%):</label>
                      <input 
                        type="number"
                        min="80" max="100"
                        value={settings.battery_max_soc}
                        onChange={(e) => setSettings(prev => ({ ...prev, battery_max_soc: e.target.value }))}
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        className="w-full text-xs font-mono font-bold"
                      />
                    </div>
                  </div>

                  {(userRole === 'admin' || userRole === 'engineer') && (
                    <button
                      onClick={() => {
                        saveSetting('battery_min_soc', settings.battery_min_soc);
                        saveSetting('battery_max_soc', settings.battery_max_soc);
                        saveSetting('tariff_peak_rate', settings.tariff_peak_rate);
                        saveSetting('tariff_offpeak_rate', settings.tariff_offpeak_rate);
                        saveSetting('optimization_mode', settings.optimization_mode);
                        saveSetting('export_enabled', settings.export_enabled);
                      }}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-extrabold py-2 rounded-xl text-xs transition-all"
                    >
                      Save All Configuration
                    </button>
                  )}

                  <div className="pt-1">
                    <span className="block text-[8px] text-slate-500 font-mono">* Adjusting these limits affects simulated dispatch rate and battery charge profiles dynamically.</span>
                  </div>
                </div>

                {/* Dataset Upload Section */}
                <div className="lg:col-span-6 glass-panel p-5 space-y-4">
                  <div className="flex items-center gap-1.5 border-b border-slate-800 pb-2">
                    <Database className="w-4 h-4 text-blue-400" />
                    <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-300 dark:text-slate-700">Dataset Replay Upload</h3>
                    {replayActive && (
                      <span className="ml-auto text-[8px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 px-2 py-0.5 rounded-full font-extrabold uppercase">REPLAY ACTIVE</span>
                    )}
                  </div>

                  <p className="text-[9px] text-slate-500 font-mono">
                    Upload CSV files per energy source to replay historical datasets through the EMS simulator. Each CSV must contain a timestamp column and the relevant power/telemetry columns.
                  </p>

                  <div className="space-y-2.5">
                    {/* Unified Master CSV Upload */}
                    <div className="flex items-center gap-2 bg-purple-950/20 dark:bg-purple-100/30 p-2.5 rounded-xl border border-purple-900/40">
                      <span className="text-purple-400 flex-shrink-0"><Database className="w-3 h-3" /></span>
                      <span className="text-[9px] font-bold uppercase tracking-wide text-purple-400 w-36">Unified Master Dataset</span>
                      <input
                        type="file"
                        accept=".csv"
                        disabled={userRole !== 'admin' && userRole !== 'engineer'}
                        onChange={(e) => uploadSectionDataset('master', e.target.files?.[0])}
                        className="flex-1 text-[8px] text-slate-500 file:text-[8px] file:font-bold file:bg-purple-800 file:text-purple-100 file:border-0 file:rounded file:px-2 file:py-1 file:mr-2 cursor-pointer disabled:opacity-40"
                      />
                      {uploadingSections['master'] && <RefreshCw className="w-3 h-3 text-purple-400 animate-spin shrink-0" />}
                      {sectionSizes['master'] > 0 && <span className="text-[8px] font-mono text-purple-400 shrink-0">{sectionSizes['master']}r</span>}
                      {uploadMsgs['master'] && <span className="text-[8px] font-mono text-amber-400 truncate max-w-[80px]">{uploadMsgs['master']}</span>}
                    </div>

                    {[
                      { key: 'solar', label: 'Solar PV Dataset', color: 'text-yellow-400', icon: <Sun className="w-3 h-3" /> },
                      { key: 'wind', label: 'Wind Turbine Dataset', color: 'text-purple-400', icon: <Wind className="w-3 h-3" /> },
                      { key: 'battery', label: 'Battery BESS Dataset', color: 'text-emerald-400', icon: <Battery className="w-3 h-3" /> },
                      { key: 'inverter', label: 'Inverter Dataset', color: 'text-slate-300', icon: <Cpu className="w-3 h-3" /> },
                      { key: 'load', label: 'Load Profile Dataset', color: 'text-rose-400', icon: <Activity className="w-3 h-3" /> },
                      { key: 'grid', label: 'Grid Tie Dataset', color: 'text-blue-400', icon: <Zap className="w-3 h-3" /> },
                    ].map(({ key, label, color, icon }) => (
                      <div key={key} className="flex items-center gap-2 bg-slate-950/40 dark:bg-slate-100 p-2.5 rounded-xl border border-slate-900">
                        <span className={`${color} flex-shrink-0`}>{icon}</span>
                        <span className={`text-[9px] font-bold uppercase tracking-wide ${color} w-36`}>{label}</span>
                        <input
                          type="file"
                          accept=".csv"
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          onChange={(e) => uploadSectionDataset(key, e.target.files?.[0])}
                          className="flex-1 text-[8px] text-slate-500 file:text-[8px] file:font-bold file:bg-slate-800 file:text-slate-300 file:border-0 file:rounded file:px-2 file:py-1 file:mr-2 cursor-pointer disabled:opacity-40"
                        />
                        <a 
                          href={`${API_BASE}/api/download-sample/${key}`}
                          download
                          title="Download Sample CSV Template"
                          className="p-1 rounded bg-slate-900 hover:bg-slate-850 dark:bg-slate-250 dark:hover:bg-slate-350 border border-slate-850 hover:border-slate-700 text-slate-400 hover:text-white dark:text-slate-700 dark:hover:text-black transition-all shrink-0"
                        >
                          <Download className="w-3 h-3" />
                        </a>
                        {uploadingSections[key] && <RefreshCw className="w-3 h-3 text-emerald-400 animate-spin shrink-0" />}
                        {sectionSizes[key] > 0 && <span className="text-[8px] font-mono text-emerald-400 shrink-0">{sectionSizes[key]}r</span>}
                        {uploadMsgs[key] && <span className="text-[8px] font-mono text-amber-400 truncate max-w-[80px]">{uploadMsgs[key]}</span>}
                      </div>
                    ))}
                  </div>

                  {(userRole === 'admin' || userRole === 'engineer') && (
                    <div className="flex gap-2 pt-1">
                      <button
                        onClick={toggleReplayState}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-extrabold transition-all ${
                          replayActive
                            ? 'bg-rose-600 hover:bg-rose-500 text-white'
                            : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950'
                        }`}
                      >
                        {replayActive ? <><RotateCcw className="w-3.5 h-3.5" /> Stop Replay</> : <><Play className="w-3.5 h-3.5" /> Start Replay</>}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB: DATA SOURCES */}
          {activeTab === 'data_sources' && (
            <div className="space-y-5">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-cyan-400" />
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-300 dark:text-slate-700">Data Acquisition Sources</h2>
                </div>
                <span className="text-[9px] bg-slate-950/80 text-emerald-400 px-2.5 py-1 rounded border border-emerald-500/20 font-bold font-mono">
                  5 ACTIVE CHANNELS
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
                {Object.entries({
                  solar: {
                    name: "Solar Generation",
                    icon: <Sun className="w-5 h-5 text-yellow-400" />,
                    protocols: ["Sample CSV", "MQTT", "Modbus TCP", "Modbus RTU", "OPC-UA", "REST API"],
                    sensorCount: 8,
                    sensors: [
                      { key: "irradiance", label: "Irradiance", unit: "W/m²" },
                      { key: "ambient_temp", label: "Ambient Temp", unit: "°C" },
                      { key: "panel_temp", label: "Panel Temp", unit: "°C" },
                      { key: "dc_voltage", label: "DC Voltage", unit: "V" },
                      { key: "dc_current", label: "DC Current", unit: "A" },
                      { key: "ac_power", label: "AC Power", unit: "kW" },
                      { key: "inverter_status", label: "Inv Status", unit: "" },
                      { key: "inverter_efficiency", label: "Inv Efficiency", unit: "%" }
                    ]
                  },
                  wind: {
                    name: "Wind Generation",
                    icon: <Wind className="w-5 h-5 text-purple-400" />,
                    protocols: ["Sample CSV", "MQTT", "Modbus TCP", "Modbus RTU", "OPC-UA", "REST API"],
                    sensorCount: 8,
                    sensors: [
                      { key: "wind_speed", label: "Wind Speed", unit: "m/s" },
                      { key: "wind_direction", label: "Wind Direction", unit: "°" },
                      { key: "air_density", label: "Air Density", unit: "kg/m³" },
                      { key: "blade_angle", label: "Blade Angle", unit: "°" },
                      { key: "turbine_rpm", label: "Turbine RPM", unit: "RPM" },
                      { key: "generator_voltage", label: "Gen Voltage", unit: "V" },
                      { key: "generator_current", label: "Gen Current", unit: "A" },
                      { key: "generated_power", label: "Gen Power", unit: "kW" }
                    ]
                  },
                  battery: {
                    name: "Battery BESS",
                    icon: <Battery className="w-5 h-5 text-emerald-400" />,
                    protocols: ["Sample CSV", "Direct BMS", "MQTT", "Modbus TCP", "OPC-UA", "REST API"],
                    sensorCount: 9,
                    sensors: [
                      { key: "soc", label: "SOC", unit: "%" },
                      { key: "soh", label: "SOH", unit: "%" },
                      { key: "voltage", label: "Voltage", unit: "V" },
                      { key: "current", label: "Current", unit: "A" },
                      { key: "temperature", label: "Temperature", unit: "°C" },
                      { key: "cell_voltage", label: "Cell Voltage", unit: "V" },
                      { key: "cell_temperature", label: "Cell Temp", unit: "°C" },
                      { key: "charge_rate", label: "Charge Rate", unit: "kW" },
                      { key: "discharge_rate", label: "Discharge Rate", unit: "kW" }
                    ]
                  },
                  grid: {
                    name: "Utility Grid",
                    icon: <Zap className="w-5 h-5 text-blue-400" />,
                    protocols: ["Sample CSV", "Modbus TCP", "MQTT", "OPC-UA", "REST API", "Modbus RTU"],
                    sensorCount: 6,
                    sensors: [
                      { key: "voltage", label: "Voltage", unit: "V" },
                      { key: "current", label: "Current", unit: "A" },
                      { key: "frequency", label: "Frequency", unit: "Hz" },
                      { key: "power_factor", label: "Power Factor", unit: "" },
                      { key: "import_power", label: "Import Power", unit: "kW" },
                      { key: "export_power", label: "Export Power", unit: "kW" }
                    ]
                  },
                  load: {
                    name: "Load Feeder",
                    icon: <Activity className="w-5 h-5 text-rose-400" />,
                    protocols: ["Sample CSV", "Modbus TCP", "MQTT", "OPC-UA", "REST API", "Modbus RTU"],
                    sensorCount: 6,
                    sensors: [
                      { key: "load_voltage", label: "Load Voltage", unit: "V" },
                      { key: "load_current", label: "Load Current", unit: "A" },
                      { key: "active_power", label: "Active Power", unit: "kW" },
                      { key: "reactive_power", label: "Reactive Power", unit: "kVAR" },
                      { key: "apparent_power", label: "Apparent Power", unit: "kVA" },
                      { key: "energy_consumption", label: "Total Energy", unit: "kWh" }
                    ]
                  }
                }).map(([key, cfg]) => {
                  const state = assetsState[key] || {};
                  const isConnected = state.status === "CONNECTED";
                  const isConnecting = state.status === "CONNECTING";
                  const isDisconnected = state.status === "DISCONNECTED" || !state.status;
                  
                  let statusColor = "bg-rose-500";
                  let statusText = "DISCONNECTED";
                  if (isConnected) {
                    statusColor = "bg-emerald-500";
                    statusText = "CONNECTED";
                  } else if (isConnecting) {
                    statusColor = "bg-amber-500 animate-pulse";
                    statusText = "CONNECTING";
                  }

                  return (
                    <div key={key} className="glass-panel p-4 flex flex-col space-y-3 relative overflow-hidden float-up border border-slate-800">
                      {/* Card Header */}
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-1">
                        <div className="flex items-center gap-2">
                          {cfg.icon}
                          <span className="font-extrabold text-[10px] uppercase text-slate-350">{cfg.name}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className={`w-1.5 h-1.5 rounded-full ${statusColor}`} />
                          <span className="text-[7.5px] font-extrabold tracking-wider text-slate-400">{statusText}</span>
                        </div>
                      </div>

                      {/* Protocol selector */}
                      <div>
                        <label className="block text-[8px] text-slate-500 uppercase font-bold mb-1">Protocol</label>
                        <select
                          value={assetProtocolInputs[key] || state.protocol || cfg.protocols[0]}
                          onChange={(e) => setAssetProtocolInputs(prev => ({ ...prev, [key]: e.target.value }))}
                          disabled={!isDisconnected}
                          className="w-full text-[9px] font-bold bg-slate-900 border border-slate-800 text-slate-300 py-1"
                        >
                          {cfg.protocols.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </div>

                      {/* Channel Stats */}
                      <div className="grid grid-cols-2 gap-2 bg-slate-950/40 p-2 rounded border border-slate-900/60 font-mono text-[8px] text-slate-450">
                        <div>
                          <span className="block text-slate-600 font-bold uppercase text-[7px]">Sensors</span>
                          <span>{cfg.sensorCount} Tags</span>
                        </div>
                        <div>
                          <span className="block text-slate-600 font-bold uppercase text-[7px]">Active</span>
                          <span>{isConnected && state.collecting ? cfg.sensorCount : 0} Tags</span>
                        </div>
                        <div>
                          <span className="block text-slate-600 font-bold uppercase text-[7px]">Data Rate</span>
                          <span>{state.collecting ? (state.protocol === "Modbus RTU" ? "1.0 Hz" : "5.0 Hz") : "0.0 Hz"}</span>
                        </div>
                        <div>
                          <span className="block text-slate-600 font-bold uppercase text-[7px]">Last Update</span>
                          <span className="truncate max-w-full block">
                            {state.last_updated && state.last_updated > 0 
                              ? new Date(state.last_updated * 1000).toLocaleTimeString([], { hour12: false })
                              : "Never"}
                          </span>
                        </div>
                      </div>

                      {/* Animated activity visualizer */}
                      {state.collecting && (
                        <div className="h-1 bg-slate-900 rounded overflow-hidden relative">
                          <div className="h-full bg-emerald-500 animate-pulse w-full shadow shadow-emerald-500/80" />
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="grid grid-cols-2 gap-1.5 pt-1">
                        {isDisconnected ? (
                          <button
                            onClick={() => handleConnectAsset(key, assetProtocolInputs[key] || cfg.protocols[0])}
                            className="col-span-2 w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-extrabold py-1.5 rounded text-[9px] uppercase transition-all"
                          >
                            Connect
                          </button>
                        ) : (
                          <>
                            <button
                              onClick={() => handleDisconnectAsset(key)}
                              className="w-full bg-rose-700 hover:bg-rose-600 text-white font-extrabold py-1.5 rounded text-[9px] uppercase transition-all"
                            >
                              Disconnect
                            </button>

                            {state.collecting ? (
                              <button
                                onClick={() => handleStopCollection(key)}
                                className="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-1.5 rounded text-[9px] uppercase transition-all"
                              >
                                Stop Ingest
                              </button>
                            ) : (
                              <button
                                onClick={() => handleStartCollection(key)}
                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-extrabold py-1.5 rounded text-[9px] uppercase transition-all"
                              >
                                Start Ingest
                              </button>
                            )}
                          </>
                        )}
                      </div>

                      {/* Live Values Drawer */}
                      {isConnected && state.sensor_values && Object.keys(state.sensor_values).length > 0 && (
                        <div className="border-t border-slate-900 pt-2.5 mt-1 space-y-1 max-h-[145px] overflow-y-auto pr-1">
                          {cfg.sensors.map(s => {
                            const val = state.sensor_values[s.key];
                            return (
                              <div key={s.key} className="flex justify-between items-center text-[8.5px] font-mono border-b border-slate-950/20 pb-0.5">
                                <span className="text-slate-500">{s.label}:</span>
                                <span className="text-emerald-400 font-extrabold">
                                  {typeof val === 'number' ? val.toFixed(1) : val} {s.unit}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB: LIVE DISPLAY */}
          {activeTab === 'live_display' && (
            <div className="space-y-5">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-300 dark:text-slate-700">Live Acquisition Metrics</h2>
                </div>
                <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-extrabold uppercase tracking-wider">WebSocket Stream</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
                {/* Solar Live Card */}
                <div className="glass-panel p-4 flex flex-col space-y-4 border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                    <span className="text-[10px] font-extrabold uppercase text-yellow-400 flex items-center gap-1.5">
                      <Sun className="w-4 h-4" /> Solar Array
                    </span>
                    <span className="text-[8px] font-mono text-slate-500">
                      {assetsState.solar?.collecting ? "STREAMING" : "OFFLINE"}
                    </span>
                  </div>
                  {assetsState.solar?.collecting ? (
                    <div className="space-y-3 flex-1 flex flex-col justify-between">
                      <div className="flex flex-col items-center py-2 relative">
                        <div className="w-20 h-20 rounded-full border-4 border-yellow-500/20 flex items-center justify-center relative">
                          <div className="absolute inset-0 rounded-full border-4 border-yellow-500 border-t-transparent animate-spin" style={{animationDuration: '4s'}} />
                          <span className="text-[10px] font-extrabold font-mono text-yellow-400">
                            {parseFloat(assetsState.solar.sensor_values.irradiance || 0).toFixed(0)}
                          </span>
                        </div>
                        <span className="text-[7.5px] uppercase font-bold text-slate-500 mt-1.5">Irradiance (W/m²)</span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Panel Temp:</span>
                          <span className="font-mono text-orange-400 font-extrabold">{parseFloat(assetsState.solar.sensor_values.panel_temp || 0).toFixed(1)}°C</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">MPPT Voltage:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.solar.sensor_values.dc_voltage || 0).toFixed(1)}V</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px] bg-yellow-500/10 p-1.5 rounded border border-yellow-500/10">
                          <span className="text-yellow-400 font-extrabold">AC Output Power:</span>
                          <span className="font-mono text-yellow-400 font-extrabold text-xs">{parseFloat(assetsState.solar.sensor_values.ac_power || 0).toFixed(2)} kW</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-10 text-[9px] text-slate-500 text-center font-mono">
                      <Sun className="w-8 h-8 opacity-20 mb-2 animate-pulse text-yellow-400" />
                      Connect to solar data sensors in "Data Sources" to activate live dashboard dials.
                    </div>
                  )}
                </div>

                {/* Wind Live Card */}
                <div className="glass-panel p-4 flex flex-col space-y-4 border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                    <span className="text-[10px] font-extrabold uppercase text-purple-400 flex items-center gap-1.5">
                      <Wind className="w-4 h-4" /> Wind Turbine
                    </span>
                    <span className="text-[8px] font-mono text-slate-500">
                      {assetsState.wind?.collecting ? "STREAMING" : "OFFLINE"}
                    </span>
                  </div>
                  {assetsState.wind?.collecting ? (
                    <div className="space-y-3 flex-1 flex flex-col justify-between">
                      <div className="flex flex-col items-center py-2">
                        <div className="w-20 h-20 rounded-full border-4 border-purple-500/20 flex items-center justify-center relative">
                          <div className="absolute inset-0 rounded-full border-4 border-purple-500 border-t-transparent animate-spin" style={{animationDuration: `${Math.max(1, 10 - (assetsState.wind.sensor_values.wind_speed || 0))}s`}} />
                          <span className="text-[10px] font-extrabold font-mono text-purple-400">
                            {parseFloat(assetsState.wind.sensor_values.wind_speed || 0).toFixed(1)}
                          </span>
                        </div>
                        <span className="text-[7.5px] uppercase font-bold text-slate-500 mt-1.5">Wind Speed (m/s)</span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Rotor Speed:</span>
                          <span className="font-mono text-purple-300 font-extrabold">{parseFloat(assetsState.wind.sensor_values.turbine_rpm || 0).toFixed(0)} RPM</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Blade Angle:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.wind.sensor_values.blade_angle || 0).toFixed(1)}°</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px] bg-purple-500/10 p-1.5 rounded border border-purple-500/10">
                          <span className="text-purple-400 font-extrabold">Generated Power:</span>
                          <span className="font-mono text-purple-400 font-extrabold text-xs">{parseFloat(assetsState.wind.sensor_values.generated_power || 0).toFixed(2)} kW</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-10 text-[9px] text-slate-500 text-center font-mono">
                      <Wind className="w-8 h-8 opacity-20 mb-2 animate-pulse text-purple-400" />
                      Connect to wind turbine sensors in "Data Sources" to activate live dashboard dials.
                    </div>
                  )}
                </div>

                {/* Battery Live Card */}
                <div className="glass-panel p-4 flex flex-col space-y-4 border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                    <span className="text-[10px] font-extrabold uppercase text-emerald-400 flex items-center gap-1.5">
                      <Battery className="w-4 h-4" /> Battery BESS
                    </span>
                    <span className="text-[8px] font-mono text-slate-500">
                      {assetsState.battery?.collecting ? "STREAMING" : "OFFLINE"}
                    </span>
                  </div>
                  {assetsState.battery?.collecting ? (
                    <div className="space-y-3 flex-1 flex flex-col justify-between">
                      <div className="flex flex-col items-center py-2">
                        <div className="w-20 h-20 rounded-full border-4 border-emerald-500/20 flex items-center justify-center relative">
                          <span className="text-xs font-extrabold font-mono text-emerald-400">
                            {parseFloat(assetsState.battery.sensor_values.soc || 0).toFixed(0)}%
                          </span>
                        </div>
                        <span className="text-[7.5px] uppercase font-bold text-slate-500 mt-1.5">State of Charge</span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Pack Voltage:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.battery.sensor_values.voltage || 0).toFixed(1)}V</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Pack Temp:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.battery.sensor_values.temperature || 0).toFixed(1)}°C</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px] bg-emerald-500/10 p-1.5 rounded border border-emerald-500/10">
                          <span className="text-emerald-400 font-extrabold">Pack Current:</span>
                          <span className="font-mono text-emerald-400 font-extrabold text-xs">{parseFloat(assetsState.battery.sensor_values.current || 0).toFixed(1)} A</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-10 text-[9px] text-slate-500 text-center font-mono">
                      <Battery className="w-8 h-8 opacity-20 mb-2 animate-pulse text-emerald-400" />
                      Connect to battery sensors in "Data Sources" to activate live dashboard dials.
                    </div>
                  )}
                </div>

                {/* Grid Live Card */}
                <div className="glass-panel p-4 flex flex-col space-y-4 border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                    <span className="text-[10px] font-extrabold uppercase text-blue-400 flex items-center gap-1.5">
                      <Zap className="w-4 h-4" /> Grid Connection
                    </span>
                    <span className="text-[8px] font-mono text-slate-500">
                      {assetsState.grid?.collecting ? "STREAMING" : "OFFLINE"}
                    </span>
                  </div>
                  {assetsState.grid?.collecting ? (
                    <div className="space-y-3 flex-1 flex flex-col justify-between">
                      <div className="flex flex-col items-center py-2">
                        <div className="w-20 h-20 rounded-full border-4 border-blue-500/20 flex items-center justify-center relative">
                          <span className="text-[10px] font-extrabold font-mono text-blue-400">
                            {parseFloat(assetsState.grid.sensor_values.frequency || 0).toFixed(2)}Hz
                          </span>
                        </div>
                        <span className="text-[7.5px] uppercase font-bold text-slate-500 mt-1.5">Line Frequency</span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Line Voltage:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.grid.sensor_values.voltage || 0).toFixed(0)}V</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Line Current:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.grid.sensor_values.current || 0).toFixed(1)}A</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px] bg-blue-500/10 p-1.5 rounded border border-blue-500/10">
                          <span className="text-blue-400 font-extrabold">Import/Export:</span>
                          <span className="font-mono text-blue-400 font-extrabold text-xs">
                            {parseFloat(assetsState.grid.sensor_values.import_power || 0) > 0 
                              ? `Imp: ${parseFloat(assetsState.grid.sensor_values.import_power).toFixed(1)}kW` 
                              : `Exp: ${parseFloat(assetsState.grid.sensor_values.export_power).toFixed(1)}kW`}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-10 text-[9px] text-slate-500 text-center font-mono">
                      <Zap className="w-8 h-8 opacity-20 mb-2 animate-pulse text-blue-400" />
                      Connect to grid ties in "Data Sources" to activate live dashboard dials.
                    </div>
                  )}
                </div>

                {/* Load Live Card */}
                <div className="glass-panel p-4 flex flex-col space-y-4 border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                    <span className="text-[10px] font-extrabold uppercase text-rose-400 flex items-center gap-1.5">
                      <Activity className="w-4 h-4" /> Load Demand
                    </span>
                    <span className="text-[8px] font-mono text-slate-500">
                      {assetsState.load?.collecting ? "STREAMING" : "OFFLINE"}
                    </span>
                  </div>
                  {assetsState.load?.collecting ? (
                    <div className="space-y-3 flex-1 flex flex-col justify-between">
                      <div className="flex flex-col items-center py-2">
                        <div className="w-20 h-20 rounded-full border-4 border-rose-500/20 flex items-center justify-center relative">
                          <span className="text-[10px] font-extrabold font-mono text-rose-400">
                            {parseFloat(assetsState.load.sensor_values.active_power || 0).toFixed(0)}kW
                          </span>
                        </div>
                        <span className="text-[7.5px] uppercase font-bold text-slate-500 mt-1.5">Active Demand</span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Feeder Voltage:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.load.sensor_values.load_voltage || 0).toFixed(0)}V</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px]">
                          <span className="text-slate-400">Total Consumption:</span>
                          <span className="font-mono text-slate-200 font-extrabold">{parseFloat(assetsState.load.sensor_values.energy_consumption || 0).toFixed(2)} kWh</span>
                        </div>
                        <div className="flex justify-between items-center text-[9px] bg-rose-500/10 p-1.5 rounded border border-rose-500/10">
                          <span className="text-rose-400 font-extrabold">Reactive Power:</span>
                          <span className="font-mono text-rose-400 font-extrabold text-xs">{parseFloat(assetsState.load.sensor_values.reactive_power || 0).toFixed(1)} kVAR</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-10 text-[9px] text-slate-500 text-center font-mono">
                      <Activity className="w-8 h-8 opacity-20 mb-2 animate-pulse text-rose-400" />
                      Connect to factory load sensors in "Data Sources" to activate live dashboard dials.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}


        </main>
      </div>

      {/* 7. HMI BLOCK DETAILS FACEPLATE MODAL */}
      {activeFaceplate && (() => {
        const details = getFaceplateDetails();
        if (!details) return null;
        
        const timestamp = telemetry.timestamp || Date.now() / 1000;
        
        // Phase/String calculation helper
        let v = 0;
        let i_tot = 0;
        let p_tot = 0;
        let isDC = false;
        let pf = 1.0;
        let minV = 0, maxV = 600;
        let minI = 0, maxI = 150;
        let minP = 0, maxP = 150;
        
        switch (activeFaceplate) {
          case 'solar':
            v = telemetry.Solar_Voltage;
            i_tot = telemetry.Solar_Current;
            p_tot = telemetry.Solar_Power;
            isDC = true;
            pf = 1.0;
            minV = 0; maxV = 600;
            minI = 0; maxI = 120;
            minP = 0; maxP = 80;
            break;
          case 'wind':
            v = telemetry.Wind_Power > 0 ? 398.5 + (Math.sin(timestamp) * 1.5) : 0;
            i_tot = telemetry.Wind_Power > 0 ? (telemetry.Wind_Power * 1000) / (1.73205 * 400 * 0.95) : 0;
            p_tot = telemetry.Wind_Power;
            pf = 0.95;
            minV = 0; maxV = 600;
            minI = 0; maxI = 250;
            minP = 0; maxP = 150;
            break;
          case 'battery':
            v = telemetry.Battery_Voltage;
            i_tot = Math.abs(telemetry.Battery_Current);
            p_tot = Math.abs(telemetry.Battery_Voltage * telemetry.Battery_Current / 1000);
            isDC = true;
            pf = 1.0;
            minV = 0; maxV = 600;
            minI = 0; maxI = 150;
            minP = 0; maxP = 100;
            break;
          case 'inverter':
            v = telemetry.Inverter_Output_Power !== 0 ? 400.0 + (Math.sin(timestamp * 1.2) * 1.0) : 0;
            i_tot = telemetry.Inverter_Output_Power !== 0 ? Math.abs(telemetry.Inverter_Output_Power * 1000) / (1.73205 * 400 * 0.98) : 0;
            p_tot = Math.abs(telemetry.Inverter_Output_Power);
            pf = 0.98;
            minV = 0; maxV = 600;
            minI = 0; maxI = 200;
            minP = 0; maxP = 120;
            break;
          case 'grid':
            v = telemetry.Grid_Status === 1 ? telemetry.Grid_Voltage : 0;
            i_tot = telemetry.Grid_Status === 1 ? Math.abs(telemetry.Grid_Power * 1000) / (1.73205 * 400 * 0.98) : 0;
            p_tot = Math.abs(telemetry.Grid_Power);
            pf = 0.98;
            minV = 0; maxV = 600;
            minI = 0; maxI = 250;
            minP = 0; maxP = 150;
            break;
          case 'load':
            v = telemetry.Load_Voltage;
            i_tot = telemetry.Load_Current;
            p_tot = telemetry.Load_Demand;
            pf = 0.92;
            minV = 0; maxV = 600;
            minI = 0; maxI = 200;
            minP = 0; maxP = 150;
            break;
          default:
            break;
        }

        // DC / AC helper variables
        let v1 = 0, v2 = 0, i1 = 0, i2 = 0, p1 = 0, p2 = 0;
        let v_ll = [0, 0, 0], v_ln = [0, 0, 0], i_phases = [0, 0, 0], p_phases = [0, 0, 0];
        
        if (isDC) {
          v1 = v > 0 ? v * 1.01 + Math.sin(timestamp)*0.5 : 0;
          v2 = v > 0 ? v * 0.99 + Math.cos(timestamp)*0.5 : 0;
          i1 = i_tot > 0 ? i_tot * 0.52 + Math.sin(timestamp)*0.1 : 0;
          i2 = i_tot > 0 ? i_tot * 0.48 - Math.sin(timestamp)*0.1 : 0;
          p1 = p_tot > 0 ? p_tot * 0.52 + Math.sin(timestamp)*0.08 : 0;
          p2 = p_tot > 0 ? p_tot * 0.48 - Math.sin(timestamp)*0.08 : 0;
        } else {
          const hasPower = p_tot > 0;
          const v_ab = hasPower ? v + Math.sin(timestamp) * 0.3 : 0;
          const v_bc = hasPower ? v + Math.cos(timestamp * 1.1) * 0.3 : 0;
          const v_ca = hasPower ? v - Math.sin(timestamp * 0.9) * 0.3 : 0;
          
          v_ll = [v_ab, v_bc, v_ca];
          v_ln = [v_ab / 1.73205, v_bc / 1.73205, v_ca / 1.73205];
          
          const i_a = hasPower ? i_tot * 0.35 + Math.sin(timestamp)*0.1 : 0;
          const i_b = hasPower ? i_tot * 0.33 + Math.cos(timestamp)*0.08 : 0;
          const i_c = hasPower ? i_tot * 0.32 - Math.sin(timestamp)*0.08 : 0;
          
          i_phases = [Math.max(0, i_a), Math.max(0, i_b), Math.max(0, i_c)];
          
          const p_a = hasPower ? p_tot * 0.35 + Math.sin(timestamp)*0.05 : 0;
          const p_b = hasPower ? p_tot * 0.33 + Math.cos(timestamp)*0.04 : 0;
          const p_c = hasPower ? p_tot * 0.32 - Math.sin(timestamp)*0.04 : 0;
          
          p_phases = [Math.max(0, p_a), Math.max(0, p_b), Math.max(0, p_c)];
        }
        
        // Generate peak values based on power levels
        const hasP = p_tot > 0;
        const peaks = {
          lastHour: hasP ? p_tot * 0.94 : 0,
          today: hasP ? Math.max(p_tot * 1.05, p_tot + 2.4) : 0,
          thisWeek: hasP ? Math.max(p_tot * 1.15, p_tot + 5.1) : 0,
          thisMonth: hasP ? Math.max(p_tot * 1.25, p_tot + 9.8) : 0,
          tillDate: hasP ? Math.max(p_tot * 1.55, p_tot + 20.4) : 0
        };

        // Get tailored historical data for line chart
        const getChartData = () => {
          const rawSource = (historicalData && historicalData.length > 0) ? historicalData : Array.from({ length: 20 }).map((_, idx) => ({
            timestamp: (Date.now() / 1000) - (20 - idx) * 60,
            Solar_Power: telemetry.Solar_Power * (0.8 + Math.random()*0.4),
            Solar_Voltage: telemetry.Solar_Voltage * (0.95 + Math.random()*0.1),
            Solar_Current: telemetry.Solar_Current * (0.8 + Math.random()*0.4),
            Solar_Temperature: telemetry.Solar_Temperature * (0.95 + Math.random()*0.1),
            Wind_Power: telemetry.Wind_Power * (0.7 + Math.random()*0.6),
            Battery_SOC: telemetry.Battery_SOC + (Math.random() - 0.5)*2,
            Battery_Voltage: telemetry.Battery_Voltage * (0.98 + Math.random()*0.04),
            Battery_Current: telemetry.Battery_Current * (0.8 + Math.random()*0.4),
            Battery_Temperature: telemetry.Battery_Temperature + (Math.random() - 0.5),
            Inverter_Output_Power: telemetry.Inverter_Output_Power * (0.8 + Math.random()*0.4),
            Grid_Power: telemetry.Grid_Power * (0.8 + Math.random()*0.4),
            Grid_Voltage: telemetry.Grid_Voltage * (0.99 + Math.random()*0.02),
            Grid_Frequency: telemetry.Grid_Frequency + (Math.random() - 0.5)*0.02,
            Load_Demand: telemetry.Load_Demand * (0.9 + Math.random()*0.2),
            Load_Voltage: telemetry.Load_Voltage * (0.99 + Math.random()*0.2),
            Load_Current: telemetry.Load_Current * (0.9 + Math.random()*0.2),
          }));

          const source = rawSource.map(d => {
            const normalized = {};
            for (const key in d) {
              normalized[key] = d[key];
              let pascalKey = key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('_');
              if (pascalKey === 'Battery_Soc') pascalKey = 'Battery_SOC';
              normalized[pascalKey] = d[key];
            }
            return normalized;
          });

          return source.map(d => {
            const tStr = new Date(d.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            switch (activeFaceplate) {
              case 'solar':
                return {
                  time: tStr,
                  Power: d.Solar_Power || 0,
                  Voltage: d.Solar_Voltage || 0,
                  Current: d.Solar_Current || 0,
                  Temp: d.Solar_Temperature || 0
                };
              case 'wind':
                const windP = d.Wind_Power || 0;
                const windV = windP > 0 ? 398.5 + (Math.sin(d.timestamp) * 1.5) : 0;
                const windI = windP > 0 ? (windP * 1000) / (1.73205 * 400 * 0.95) : 0;
                const windTemp = 38.5 + windP * 0.12;
                return {
                  time: tStr,
                  Power: windP,
                  Voltage: windV,
                  Current: windI,
                  Temp: windTemp
                };
              case 'battery':
                const batP = Math.abs((d.Battery_Voltage || 0) * (d.Battery_Current || 0) / 1000);
                return {
                  time: tStr,
                  Power: batP,
                  Voltage: d.Battery_Voltage || 0,
                  Current: Math.abs(d.Battery_Current || 0),
                  Temp: d.Battery_Temperature || 0,
                  SOC: d.Battery_SOC || 0
                };
              case 'inverter':
                const invP = Math.abs(d.Inverter_Output_Power || 0);
                const invV = invP > 0 ? 400.0 + (Math.sin(d.timestamp * 1.2) * 1.0) : 0;
                const invI = invP > 0 ? invP * 1000 / (1.73205 * 400 * 0.98) : 0;
                const invTemp = 35.0 + invP * 0.22;
                return {
                  time: tStr,
                  Power: invP,
                  Voltage: invV,
                  Current: invI,
                  Temp: invTemp
                };
              case 'grid':
                const gridP = Math.abs(d.Grid_Power || 0);
                const gridV = d.Grid_Voltage || 400.0;
                const gridI = gridP > 0 ? gridP * 1000 / (1.73205 * 400 * 0.98) : 0;
                const freq = d.Grid_Frequency || 50.0;
                return {
                  time: tStr,
                  Power: gridP,
                  Voltage: gridV,
                  Current: gridI,
                  Freq: freq
                };
              case 'load':
                return {
                  time: tStr,
                  Power: d.Load_Demand || 0,
                  Voltage: d.Load_Voltage || 0,
                  Current: d.Load_Current || 0,
                  Temp: 25.0 + (d.Load_Demand || 0) * 0.05
                };
              default:
                return { time: tStr };
            }
          });
        };

        const chartData = getChartData();

        return (
          <>
            <div 
              className="faceplate-overlay active"
              onClick={() => setActiveFaceplate(null)}
            />
            <div 
              className="faceplate-modal active transition-all duration-300"
              style={{ maxWidth: modalTab === 'live' ? '980px' : '640px', width: '95%', maxHeight: '90vh', overflowY: 'auto' }}
            >
              {/* Header block with multi-tab structure */}
              <div className="faceplate-header flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800/80 dark:border-slate-200 pb-3 mb-4 gap-3">
                <div className="flex items-center gap-2">
                  <button 
                    className="p-1 rounded-md hover:bg-slate-800/80 dark:hover:bg-slate-200 text-slate-400 hover:text-white dark:hover:text-black transition-colors"
                    onClick={() => setActiveFaceplate(null)}
                    title="Back to Grid Schema"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>
                  {details.icon}
                  <h3 className="font-extrabold text-sm tracking-wider uppercase">{details.title}</h3>
                </div>
                
                {/* Custom Tab Selector */}
                <div className="flex items-center gap-1 bg-slate-950/60 dark:bg-slate-200 p-0.5 rounded-lg border border-slate-800/80 dark:border-slate-300 text-[10px] font-bold">
                  {[
                    { id: 'live', label: 'SE Live' },
                    { id: 'stats', label: 'SE Stats' },
                    { id: 'settings', label: 'SE Setting' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setModalTab(tab.id)}
                      className={`px-3 py-1.5 rounded-md transition-all ${
                        modalTab === tab.id
                          ? 'bg-emerald-500 text-slate-950 font-extrabold shadow'
                          : 'text-slate-400 hover:text-slate-200 dark:text-slate-600 dark:hover:text-slate-900'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                  {/* Visual non-clickable tabs for style sync */}
                  {['SE Graph', 'SE Reports', 'Open Issues'].map((lbl) => (
                    <span
                      key={lbl}
                      className="px-2.5 py-1.5 text-[9px] font-semibold text-slate-600 dark:text-slate-400 select-none cursor-not-allowed hidden md:inline"
                    >
                      {lbl}
                    </span>
                  ))}
                </div>

                <button 
                  className="faceplate-close text-2xl leading-none text-slate-400 hover:text-white dark:hover:text-black hidden md:block focus:outline-none"
                  onClick={() => setActiveFaceplate(null)}
                >
                  &times;
                </button>
              </div>

              {/* Status indicator bar with Quick Isolation Toggle */}
              <div className="flex items-center justify-between mb-4 bg-slate-950/30 dark:bg-slate-100/60 p-2.5 rounded-lg border border-slate-900 dark:border-slate-300 gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 dark:text-slate-555 font-bold uppercase tracking-wider">Device Status Log:</span>
                  <div className={`faceplate-status-badge text-[9px] font-extrabold uppercase px-2 py-0.5 rounded ${
                    details.statusClass === 'green' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    details.statusClass === 'critical' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse' :
                    'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}>
                    {details.statusText}
                  </div>
                </div>

                {/* Direct Manual Component Isolation Switch */}
                {['solar', 'wind', 'battery', 'grid'].includes(activeFaceplate) && (
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-slate-450 dark:text-slate-550 font-bold uppercase">Manual Control:</span>
                    <button
                      onClick={() => {
                        if (activeFaceplate === 'solar') handleComponentToggle('solar', !solarEnabled);
                        if (activeFaceplate === 'wind') handleComponentToggle('wind', !windEnabled);
                        if (activeFaceplate === 'battery') handleComponentToggle('battery', !batteryEnabled);
                        if (activeFaceplate === 'grid') handleComponentToggle('grid', !gridEnabled);
                      }}
                      disabled={userRole !== 'admin' && userRole !== 'engineer'}
                      className={`px-3 py-1 rounded text-[9px] font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                        (activeFaceplate === 'solar' ? solarEnabled :
                         activeFaceplate === 'wind' ? windEnabled :
                         activeFaceplate === 'battery' ? batteryEnabled : gridEnabled)
                          ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                          : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                      }`}
                      title={userRole !== 'admin' && userRole !== 'engineer' ? "Requires Engineer or Admin privileges" : "Toggle Component Connection State"}
                    >
                      {(activeFaceplate === 'solar' ? solarEnabled :
                        activeFaceplate === 'wind' ? windEnabled :
                        activeFaceplate === 'battery' ? batteryEnabled : gridEnabled)
                          ? 'DISCONNECT FEEDER (OFF)' : 'CONNECT FEEDER (ON)'}
                    </button>
                    {activeFaceplate === 'grid' && (
                      <a
                        href={`${API_BASE}/api/export/grid-exports`}
                        download
                        className="px-3 py-1 rounded text-[9px] font-extrabold border transition-all bg-blue-600/15 text-blue-400 border-blue-500/30 hover:bg-blue-600/25 flex items-center gap-1.5 shrink-0 animate-pulse hover:animate-none"
                        title="Download Grid Exports Dataset (CSV)"
                      >
                        <Download className="w-3 h-3" /> EXPORTS DATASET (CSV)
                      </a>
                    )}
                  </div>
                )}
              </div>

              {/* Tab Bodies */}
              {modalTab === 'live' && (
                <div className="space-y-4">
                  {/* Breadcrumb path */}
                  <div className="text-[9px] text-slate-500 dark:text-slate-550 font-mono flex items-center gap-1 border-b border-slate-900/30 pb-1.5 mb-2 uppercase tracking-wider">
                    <span>Home</span> &gt;&gt;
                    <span>SCADA Hybrid EMS</span> &gt;&gt;
                    <span>Floor 1</span> &gt;&gt;
                    <span>Feeders</span> &gt;&gt;
                    <span className="text-emerald-400 dark:text-emerald-600 font-bold">{details.title}</span>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Left Meters Grid (7 columns) */}
                    <div className="lg:col-span-7 bg-slate-950/40 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-300 flex flex-col justify-between">
                      <div className="flex items-center gap-1.5 mb-2.5">
                        <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
                        <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide">Real-time Phase Metering</h4>
                      </div>

                      {/* 3 Gauges row */}
                      <div className="grid grid-cols-3 gap-2.5 justify-items-center">
                        <div className="flex flex-col items-center w-full">
                          <DialGauge min={minV} max={maxV} value={v} title="Voltage" unit="V" />
                          
                          {/* Phase detail display under Voltage dial */}
                          {isDC ? (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5 text-slate-400 dark:text-slate-500">
                              <div className="flex justify-between px-1 border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>Bus Total:</span>
                                <span className="text-white dark:text-slate-800 font-bold">{v.toFixed(1)}V</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-semibold text-slate-500">
                                <span>S1: {v1.toFixed(1)}V</span>
                                <span>S2: {v2.toFixed(1)}V</span>
                              </div>
                            </div>
                          ) : (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5">
                              <div className="flex justify-between px-1 text-slate-400 dark:text-slate-550 font-semibold border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>V L-L avg:</span>
                                <span className="text-white dark:text-slate-850 font-bold">{v.toFixed(1)}V</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-bold">
                                <span className="text-red-400 dark:text-red-600">{v_ln[0].toFixed(0)}V</span>
                                <span className="text-yellow-400 dark:text-yellow-600">{v_ln[1].toFixed(0)}V</span>
                                <span className="text-blue-400 dark:text-cyan-600">{v_ln[2].toFixed(0)}V</span>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col items-center w-full">
                          <DialGauge min={minI} max={maxI} value={i_tot} title="Current" unit="A" />
                          
                          {/* Phase detail display under Current dial */}
                          {isDC ? (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5 text-slate-400 dark:text-slate-500">
                              <div className="flex justify-between px-1 border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>Pack DC:</span>
                                <span className="text-white dark:text-slate-800 font-bold">{i_tot.toFixed(1)}A</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-semibold text-slate-500">
                                <span>I1: {i1.toFixed(1)}A</span>
                                <span>I2: {i2.toFixed(1)}A</span>
                              </div>
                            </div>
                          ) : (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5">
                              <div className="flex justify-between px-1 text-slate-400 dark:text-slate-550 font-semibold border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>Total:</span>
                                <span className="text-white dark:text-slate-850 font-bold">{i_tot.toFixed(1)}A</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-bold">
                                <span className="text-red-400 dark:text-red-600">{i_phases[0].toFixed(1)}A</span>
                                <span className="text-yellow-400 dark:text-yellow-600">{i_phases[1].toFixed(1)}A</span>
                                <span className="text-blue-400 dark:text-cyan-600">{i_phases[2].toFixed(1)}A</span>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col items-center w-full">
                          <DialGauge min={minP} max={maxP} value={p_tot} title="Power" unit="kW" />
                          
                          {/* Phase detail display under Power dial */}
                          {isDC ? (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5 text-slate-400 dark:text-slate-500">
                              <div className="flex justify-between px-1 border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>Total kW:</span>
                                <span className="text-white dark:text-slate-800 font-bold">{p_tot.toFixed(1)}kW</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-semibold text-slate-500">
                                <span>P1: {p1.toFixed(1)}kW</span>
                                <span>P2: {p2.toFixed(1)}kW</span>
                              </div>
                            </div>
                          ) : (
                            <div className="mt-2 text-[9px] font-mono w-full text-center space-y-0.5">
                              <div className="flex justify-between px-1 text-slate-400 dark:text-slate-550 font-semibold border-b border-slate-900/20 dark:border-slate-300 pb-0.5">
                                <span>Active Total:</span>
                                <span className="text-white dark:text-slate-850 font-bold">{p_tot.toFixed(1)}kW</span>
                              </div>
                              <div className="flex justify-between px-1 text-[8px] font-bold">
                                <span className="text-red-400 dark:text-red-600">{p_phases[0].toFixed(1)}kW</span>
                                <span className="text-yellow-400 dark:text-yellow-600">{p_phases[1].toFixed(1)}kW</span>
                                <span className="text-blue-400 dark:text-cyan-600">{p_phases[2].toFixed(1)}kW</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Energy / Peak Power Table (5 columns) */}
                    <div className="lg:col-span-5 bg-slate-950/40 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-300 flex flex-col justify-between">
                      {/* Odometer block */}
                      <div className="bg-slate-950/50 dark:bg-slate-200/50 rounded-lg p-2.5 border border-slate-900 dark:border-slate-300">
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="bg-blue-600 text-white font-extrabold px-2 py-0.5 rounded text-[8px] tracking-wider uppercase inline-block">Cumulative Energy</span>
                          <span className="text-[8px] text-slate-500 dark:text-slate-500 font-semibold">Offset: 0.00 kWh</span>
                        </div>
                        <Odometer value={cumulativeEnergy[activeFaceplate] || 0} />
                        
                        {/* Frequency / PF rows */}
                        <div className="flex items-center justify-between gap-2.5 mt-2">
                          <div className="bg-slate-950 dark:bg-slate-50 p-1.5 rounded border border-slate-900 dark:border-slate-300 w-1/2 flex items-center justify-between">
                            <span className="text-[7.5px] uppercase font-bold text-slate-500 dark:text-slate-555">Frequency</span>
                            <span className="font-mono text-[10px] font-bold text-emerald-400 dark:text-emerald-600">
                              {isDC ? "0.00 Hz" : `${(telemetry.Grid_Frequency || 50.00).toFixed(2)} Hz`}
                            </span>
                          </div>
                          <div className="bg-slate-950 dark:bg-slate-50 p-1.5 rounded border border-slate-900 dark:border-slate-300 w-1/2 flex items-center justify-between">
                            <span className="text-[7.5px] uppercase font-bold text-slate-500 dark:text-slate-555">Powerfactor</span>
                            <span className="font-mono text-[10px] font-bold text-emerald-400 dark:text-emerald-600">
                              {pf.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Peak Power table */}
                      <div className="bg-slate-950/20 dark:bg-slate-200/20 rounded-lg border border-slate-900 dark:border-slate-300 p-2.5 mt-2.5">
                        <span className="text-[8.5px] font-bold uppercase text-slate-400 dark:text-slate-555 tracking-wider mb-1.5 block">Peak Power Log</span>
                        <table className="w-full text-left text-[8.5px] font-mono">
                          <thead>
                            <tr className="border-b border-slate-800 dark:border-slate-300 text-slate-500 dark:text-slate-500 uppercase tracking-wide">
                              <th className="pb-1">Interval</th>
                              <th className="pb-1 text-right">Peak (kW)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-900/30 dark:divide-slate-300/30 text-slate-300 dark:text-slate-700">
                            <tr>
                              <td className="py-0.5">Last Hour</td>
                              <td className="py-0.5 text-right font-extrabold text-white dark:text-slate-900">{peaks.lastHour.toFixed(1)}</td>
                            </tr>
                            <tr>
                              <td className="py-0.5">Today</td>
                              <td className="py-0.5 text-right font-extrabold text-white dark:text-slate-900">{peaks.today.toFixed(1)}</td>
                            </tr>
                            <tr>
                              <td className="py-0.5">This Week</td>
                              <td className="py-0.5 text-right font-extrabold text-white dark:text-slate-900">{peaks.thisWeek.toFixed(1)}</td>
                            </tr>
                            <tr>
                              <td className="py-0.5">This Month</td>
                              <td className="py-0.5 text-right font-extrabold text-white dark:text-slate-900">{peaks.thisMonth.toFixed(1)}</td>
                            </tr>
                            <tr>
                              <td className="py-0.5">Till Date</td>
                              <td className="py-0.5 text-right font-extrabold text-white dark:text-slate-900">{peaks.tillDate.toFixed(1)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* Vitals Trend Chart (Large at bottom) */}
                  <div className="bg-slate-950/40 dark:bg-slate-100 p-3.5 rounded-xl border border-slate-900 dark:border-slate-300">
                    <div className="flex flex-col sm:flex-row justify-between sm:items-center border-b border-slate-900/40 pb-2 mb-2 gap-2">
                      <div className="flex items-center gap-1.5">
                        <TrendingUp className="w-4 h-4 text-emerald-400" />
                        <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide">
                          Voltage - Current - Power - Temperature Trends (24h)
                        </h4>
                      </div>
                      
                      {/* Legend toggle controls matching HMI screen */}
                      <div className="flex gap-1.5 text-[8.5px] font-bold">
                        <button 
                          onClick={() => setShowLegends(true)}
                          className={`px-2 py-0.5 rounded border transition-colors ${
                            showLegends 
                              ? 'bg-emerald-600 text-white border-emerald-500' 
                              : 'bg-slate-955 text-slate-400 border-slate-900 hover:text-white dark:bg-slate-200 dark:text-slate-700 dark:border-slate-300'
                          }`}
                        >
                          Show all legends
                        </button>
                        <button 
                          onClick={() => setShowLegends(false)}
                          className={`px-2 py-0.5 rounded border transition-colors ${
                            !showLegends 
                              ? 'bg-rose-600 text-white border-rose-500' 
                              : 'bg-slate-955 text-slate-400 border-slate-900 hover:text-white dark:bg-slate-200 dark:text-slate-700 dark:border-slate-300'
                          }`}
                        >
                          Hide all legends
                        </button>
                      </div>
                    </div>

                    <div ref={chartContainerRef} className="h-[210px] w-full mt-2.5" style={{minHeight:'210px'}}>
                      {isChartReady ? (
                        <LineChart width={chartWidth} height={210} data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="time" stroke="#64748b" fontSize={8} />
                          <YAxis yAxisId="left" stroke="#64748b" fontSize={8} tickFormatter={(val) => `${val}`} />
                          <YAxis yAxisId="right" orientation="right" stroke="#f59e0b" fontSize={8} domain={['dataMin - 10', 'dataMax + 10']} tickFormatter={(val) => `${Math.round(val)}V`} />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: '#0f172a', 
                              borderColor: '#1e293b', 
                              color: '#f8fafc',
                              fontSize: '9px',
                              borderRadius: '8px'
                            }} 
                          />
                          {showLegends && <Legend wrapperStyle={{ fontSize: '9px', paddingTop: '5px' }} />}
                          
                          <Line yAxisId="left" type="monotone" dataKey="Power" stroke="#10b981" strokeWidth={2} dot={false} name="Active Power (kW)" />
                          <Line yAxisId="right" type="monotone" dataKey="Voltage" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Voltage (V)" />
                          <Line yAxisId="left" type="monotone" dataKey="Current" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Current (A)" />
                          
                          {activeFaceplate === 'grid' && (
                            <Line yAxisId="left" type="monotone" dataKey="Freq" stroke="#ec4899" strokeWidth={1.5} dot={false} name="Frequency (Hz)" />
                          )}
                          {activeFaceplate === 'battery' && (
                            <>
                              <Line yAxisId="left" type="monotone" dataKey="SOC" stroke="#a855f7" strokeWidth={2} dot={false} name="Battery SOC (%)" />
                              <Line yAxisId="left" type="monotone" dataKey="Temp" stroke="#f43f5e" strokeWidth={1.5} dot={false} name="Battery Temp (°C)" />
                            </>
                          )}
                          {activeFaceplate !== 'grid' && activeFaceplate !== 'battery' && (
                            <Line yAxisId="left" type="monotone" dataKey="Temp" stroke="#ec4899" strokeWidth={1.5} dot={false} name="Temp (°C)" />
                          )}
                        </LineChart>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-slate-500 font-mono text-[9px] uppercase tracking-wider">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping mr-2"></span>
                          Initializing Telemetry Chart...
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {modalTab === 'stats' && (
                <div className="space-y-4">
                  <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300">
                    <div className="flex items-center gap-1.5 border-b border-slate-900/30 pb-2 mb-3">
                      <Info className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide">System Asset Registry</h4>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs font-sans">
                      {details.assets.map((a, idx) => (
                        <div key={idx} className="flex flex-col border-b border-slate-900/10 dark:border-slate-300/30 pb-2">
                          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wide">{a.name}</span>
                          <span className="text-slate-200 dark:text-slate-800 font-semibold font-mono mt-0.5">{a.val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {modalTab === 'settings' && (
                <div className="space-y-4 text-xs font-sans">
                  {userRole !== 'admin' && userRole !== 'engineer' && (
                    <div className="bg-rose-950/40 border border-rose-900/60 rounded-lg p-3 text-rose-300 flex items-start gap-2.5">
                      <ShieldAlert className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                      <div>
                        <span className="font-bold block text-[10px] uppercase tracking-wide">Read-Only Operator Level</span>
                        <p className="text-[9px] text-rose-400/90 mt-0.5">
                          You are currently authorized as a viewer/operator. Modifying system parameters requires upgrading your authorization code to Engineer or Administrator.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Solar Settings */}
                  {activeFaceplate === 'solar' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-3">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">Solar PV Configuration</h4>
                      <div>
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Manual Power Generation Limit (kW)</label>
                        <div className="flex gap-2">
                          <input 
                            type="number"
                            placeholder="Auto (Normal Solar Curves)"
                            value={solarOverride}
                            onChange={(e) => setSolarOverride(e.target.value)}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1 text-xs text-white dark:text-black w-full font-mono"
                          />
                          {solarOverride !== "" && (
                            <button 
                              onClick={() => setSolarOverride("")}
                              disabled={userRole !== 'admin' && userRole !== 'engineer'}
                              className="bg-rose-900/40 text-rose-300 border border-rose-900 hover:bg-rose-900/60 transition px-2.5 py-1 rounded text-xs font-bold"
                            >
                              Clear
                            </button>
                          )}
                        </div>
                        <span className="text-[8.5px] text-slate-500 mt-1 block">Forces the solar array generator to stay capped at the user threshold.</span>
                      </div>
                      <div className="border-t border-slate-900/30 pt-3">
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-2">Component Isolation</label>
                        <button
                          onClick={() => handleComponentToggle('solar', !solarEnabled)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className={`w-full py-2 rounded-lg text-xs font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                            solarEnabled
                              ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                              : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                          }`}
                        >
                          {solarEnabled ? "DISCONNECT SOLAR (OFF)" : "CONNECT SOLAR (ON)"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Wind Settings */}
                  {activeFaceplate === 'wind' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-3">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">Wind Turbine Configuration</h4>
                      <div>
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Manual Power Generation Override (kW)</label>
                        <div className="flex gap-2">
                          <input 
                            type="number"
                            placeholder="Auto (Wind Simulation Curves)"
                            value={windOverride}
                            onChange={(e) => setWindOverride(e.target.value)}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1 text-xs text-white dark:text-black w-full font-mono"
                          />
                          {windOverride !== "" && (
                            <button 
                              onClick={() => setWindOverride("")}
                              disabled={userRole !== 'admin' && userRole !== 'engineer'}
                              className="bg-rose-900/40 text-rose-300 border border-rose-900 hover:bg-rose-900/60 transition px-2.5 py-1 rounded text-xs font-bold"
                            >
                              Clear
                            </button>
                          )}
                        </div>
                        <span className="text-[8.5px] text-slate-500 mt-1 block">Forces the wind generator turbine to stay clamped at this capacity.</span>
                      </div>
                      <div className="border-t border-slate-900/30 pt-3">
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-2">Component Isolation</label>
                        <button
                          onClick={() => handleComponentToggle('wind', !windEnabled)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className={`w-full py-2 rounded-lg text-xs font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                            windEnabled
                              ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                              : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                          }`}
                        >
                          {windEnabled ? "DISCONNECT TURBINES (OFF)" : "CONNECT TURBINES (ON)"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Battery Settings */}
                  {activeFaceplate === 'battery' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-4">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">BESS Safe Boundary Limits</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Min SOC Guard Limit (%)</label>
                          <input 
                            type="number"
                            value={settings.battery_min_soc}
                            onChange={(e) => setSettings(prev => ({ ...prev, battery_min_soc: e.target.value }))}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1.5 text-xs text-white dark:text-black w-full font-mono font-bold"
                          />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Max SOC Guard Limit (%)</label>
                          <input 
                            type="number"
                            value={settings.battery_max_soc}
                            onChange={(e) => setSettings(prev => ({ ...prev, battery_max_soc: e.target.value }))}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1.5 text-xs text-white dark:text-black w-full font-mono font-bold"
                          />
                        </div>
                      </div>
                      <span className="text-[8.5px] text-slate-550 block font-medium">Triggers load shedding or grid fallback when battery state drifts outside thresholds.</span>
                      <div className="border-t border-slate-900/30 pt-3">
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1.5">BESS Cooling Fan Override</label>
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            { value: null, label: 'AUTO (TEMP)' },
                            { value: 'ON', label: 'MANUAL ON' },
                            { value: 'OFF', label: 'MANUAL OFF' }
                          ].map((opt) => (
                            <button
                              key={opt.label}
                              onClick={() => handleFanOverrideToggle(opt.value)}
                              disabled={userRole !== 'admin' && userRole !== 'engineer'}
                              className={`py-1.5 rounded-lg text-[9px] font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                                fanOverride === opt.value
                                  ? 'bg-blue-600/20 text-blue-400 border-blue-500/50 hover:bg-blue-600/30'
                                  : 'bg-slate-900/40 text-slate-400 border-slate-800 hover:bg-slate-900 dark:bg-white dark:border-slate-350 dark:hover:bg-slate-200'
                              }`}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="border-t border-slate-900/30 pt-3">
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-2">Component Isolation</label>
                        <button
                          onClick={() => handleComponentToggle('battery', !batteryEnabled)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className={`w-full py-2 rounded-lg text-xs font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                            batteryEnabled
                              ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                              : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                          }`}
                        >
                          {batteryEnabled ? "DISCONNECT BESS (OFF)" : "CONNECT BESS (ON)"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Inverter Settings */}
                  {activeFaceplate === 'inverter' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-3">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">Inverter DSP Controls</h4>
                      <div>
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">EMS Dispatch Optimization Mode</label>
                        <select
                          value={settings.optimization_mode}
                          onChange={(e) => setSettings(prev => ({ ...prev, optimization_mode: e.target.value }))}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1.5 text-xs text-white dark:text-black w-full font-bold"
                        >
                          <option value="NORMAL">Normal Operation (Tariff Arbitrage)</option>
                          <option value="MAX_GREEN">Max Renewable Self-Consumption</option>
                          <option value="BATTERY_SAVE">Preserve Battery Lifespan (Low Discharge)</option>
                        </select>
                        <span className="text-[8.5px] text-slate-550 mt-1 block font-medium">Dynamically adjusts power factor, thermal limits, and charging schedules.</span>
                      </div>
                    </div>
                  )}

                  {/* Grid Settings */}
                  {activeFaceplate === 'grid' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-3">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">Utility Grid Settings</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Peak Billing Tariff (₹/kWh)</label>
                          <input 
                            type="number"
                            step="0.01"
                            value={settings.tariff_peak_rate}
                            onChange={(e) => setSettings(prev => ({ ...prev, tariff_peak_rate: e.target.value }))}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1.5 text-xs text-white dark:text-black w-full font-mono font-bold"
                          />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Grid Export Lockout</label>
                          <select
                            value={settings.export_enabled}
                            onChange={(e) => setSettings(prev => ({ ...prev, export_enabled: e.target.value }))}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1.5 text-xs text-white dark:text-black w-full font-bold"
                          >
                            <option value="true">Allowed (Feed-In Tariff)</option>
                            <option value="false">Lockout (Zero Export Limit)</option>
                          </select>
                        </div>
                      </div>
                      <div className="border-t border-slate-900/30 pt-3">
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-2">Component Isolation</label>
                        <button
                          onClick={() => handleComponentToggle('grid', !gridEnabled)}
                          disabled={userRole !== 'admin' && userRole !== 'engineer'}
                          className={`w-full py-2 rounded-lg text-xs font-extrabold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                            gridEnabled
                              ? 'bg-emerald-600/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/25'
                              : 'bg-rose-600/15 text-rose-400 border-rose-500/30 hover:bg-rose-600/25'
                          }`}
                        >
                          {gridEnabled ? "ISLAND MICROGRID (DISCONNECT GRID)" : "CONNECT UTILITY GRID (ON)"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Load Settings */}
                  {activeFaceplate === 'load' && (
                    <div className="bg-slate-950/40 dark:bg-slate-100 p-4 rounded-xl border border-slate-900 dark:border-slate-300 space-y-3">
                      <h4 className="text-[10px] font-bold text-slate-300 dark:text-slate-700 uppercase tracking-wide border-b border-slate-900/30 pb-1.5">Load Feeder Configuration</h4>
                      <div>
                        <label className="block text-[9px] font-bold text-slate-400 dark:text-slate-550 uppercase tracking-wide mb-1">Manual Power Demand Override (kW)</label>
                        <div className="flex gap-2">
                          <input 
                            type="number"
                            placeholder="Auto (Normal Load Curves)"
                            value={loadOverride}
                            onChange={(e) => setLoadOverride(e.target.value)}
                            disabled={userRole !== 'admin' && userRole !== 'engineer'}
                            className="bg-slate-950 dark:bg-white border border-slate-800 dark:border-slate-300 rounded px-2.5 py-1 text-xs text-white dark:text-black w-full font-mono"
                          />
                          {loadOverride !== "" && (
                            <button 
                              onClick={() => setLoadOverride("")}
                              disabled={userRole !== 'admin' && userRole !== 'engineer'}
                              className="bg-rose-900/40 text-rose-300 border border-rose-900 hover:bg-rose-900/60 transition px-2.5 py-1 rounded text-xs font-bold"
                            >
                              Clear
                            </button>
                          )}
                        </div>
                        <span className="text-[8.5px] text-slate-500 mt-1 block">Forces the microgrid load demands to clamp at this rating.</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        );
      })()}

      {/* 8. SECURITY AUTHENTICATION SELECTOR MODAL */}
      <AnimatePresence>
        {showLoginModal && (
          <>
            <div 
              className="faceplate-overlay active"
              onClick={() => setShowLoginModal(false)}
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, x: "-50%", y: "-45%" }}
              animate={{ opacity: 1, scale: 1, x: "-50%", y: "-50%" }}
              exit={{ opacity: 0, scale: 0.9, x: "-50%", y: "-45%" }}
              className="faceplate-modal active max-w-sm"
            >
              <div className="faceplate-header">
                <div className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-extrabold">Authorize Control Role</h3>
                </div>
                <button className="faceplate-close" onClick={() => setShowLoginModal(false)}>&times;</button>
              </div>

              <form onSubmit={handleLogin} className="space-y-4 text-xs">
                {loginError && (
                  <div className="bg-red-950/60 border border-red-500/30 text-red-200 p-2.5 rounded-lg font-semibold">
                    {loginError}
                  </div>
                )}
                
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Username / Role ID:</label>
                  <input 
                    type="text" 
                    placeholder="admin, operator, engineer, viewer"
                    value={usernameInput}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    className="w-full text-xs animate-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Security Pin / Password:</label>
                  <input 
                    type="password" 
                    placeholder="Enter role name as password"
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    className="w-full text-xs animate-none"
                    required
                  />
                </div>

                <div className="bg-slate-900/60 dark:bg-slate-100 p-2 rounded-lg text-[10px] text-slate-400 dark:text-slate-500 font-mono space-y-0.5">
                  <div>* Admin (settings edits) | pass: admin</div>
                  <div>* Engineer (overrides, faults) | pass: engineer</div>
                  <div>* Operator (ack alarms) | pass: operator</div>
                </div>

                <div className="flex gap-2 justify-end pt-2">
                  <button 
                    type="button"
                    onClick={() => setShowLoginModal(false)}
                    className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-1.5 rounded-lg font-bold"
                  >
                    Login
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

    </div>
  );
}
