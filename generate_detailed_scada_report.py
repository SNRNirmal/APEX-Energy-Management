import os
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

def draw_page_decorations(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#cbd5e1')) # slate-300
    canvas.setLineWidth(0.5)
    
    # Draw page border
    canvas.rect(36, 36, 612 - 72, 792 - 72, fill=0, stroke=1)
    
    # Draw header text
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor('#475569'))
    canvas.drawString(45, 765, "APEX MICROGRID SCADA & EMS — TECHNICAL REPORT")
    
    # Draw header divider line
    canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
    canvas.line(36, 756, 612 - 36, 756)
    
    # Draw footer divider line
    canvas.line(36, 54, 612 - 36, 54)
    
    # Draw page number in footer
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.HexColor('#64748b'))
    canvas.drawString(45, 42, f"Detailed Project Report | Page {doc.page}")
    canvas.drawRightString(612 - 45, 42, "CONFIDENTIAL — FOR INTERNAL USE ONLY")
    canvas.restoreState()

def generate_detailed_report():
    pdf_filename = "APEX_Microgrid_SCADA_EMS_Detailed_System_Report.pdf"
    
    # Document margin settings
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Styles Definition
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=3,
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=12,
        alignment=0
    )
    
    h1_style = ParagraphStyle(
        'H1Heading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'H2Heading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.0,
        leading=11.0,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        textColor=colors.white,
        alignment=0
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.0,
        textColor=colors.HexColor('#1e293b')
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e3a8a')
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=3
    )

    story = []
    
    # ================= PAGE 1 =================
    story.append(Spacer(1, 15))
    story.append(Paragraph("APEX MICROGRID SCADA & EMS SYSTEM REPORT", title_style))
    story.append(Paragraph("Comprehensive Technical Specifications, Dataset Analytics & Working Architecture", subtitle_style))
    
    # Metadata block
    metadata_data = [
        [Paragraph("<b>Project Name</b>", table_cell_bold), Paragraph("APEX EMS — Hybrid Microgrid Energy Management System & SCADA Platform", table_cell_style)],
        [Paragraph("<b>Project Type</b>", table_cell_bold), Paragraph("Supervisory Control, High-Frequency Logger, AI Optimizer & Fault Advisor", table_cell_style)],
        [Paragraph("<b>Execution Rate</b>", table_cell_bold), Paragraph("1Hz Non-Blocking Continuous Daemon Loop (1-second intervals)", table_cell_style)],
        [Paragraph("<b>Communications</b>", table_cell_bold), Paragraph("WebSockets Broadcasts, REST APIs, Modbus TCP, CAN Bus, OPC UA, IEC 61850", table_cell_style)],
    ]
    meta_table = Table(metadata_data, colWidths=[100, 440])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("1. Project Overview & Scope", h1_style))
    story.append(Paragraph(
        "The <b>APEX Microgrid SCADA & EMS</b> is a production-grade supervisory control and data acquisition system integrated "
        "with a rule-based state machine and reinforcement learning AI agent. The platform coordinates a hybrid electrical "
        "network consisting of Solar PV generation, Wind turbine generation, a Battery Energy Storage System (BESS), utility "
        "grid coupling, and dynamic facility loads. Operating at a <b>1Hz execution frequency</b>, the background daemon handles "
        "telemetry ingestion, executes safety checks, runs forecasting models, updates simulated physics, and dispatches "
        "optimized charge/discharge profiles. It ensures microgrid stability, minimizes tariff-based import fees, protects "
        "battery chemistry under temperature excursions, and generates structured alarms for immediate field restoration.",
        body_style
    ))
    
    story.append(Paragraph("2. Core Requirements", h1_style))
    story.append(Paragraph("&bull; <b>High-Fidelity Synoptic Visualization:</b> Render browser-based HMI dashboards mapping active power flows with dynamic speed animation, colored tag displays, and diagnostic faceplates.", bullet_style))
    story.append(Paragraph("&bull; <b>Continuous Replay Loop Fallback:</b> Loop default sample CSV datasets sequentially at 1Hz if sensors are disconnected or in the 'Sample CSV' state. Promotion to live simulated physical metrics occurs automatically on successful protocol connection.", bullet_style))
    story.append(Paragraph("&bull; <b>AI In-situ Optimization:</b> Utilize reinforcement learning (Q-Learning) and machine learning forecasters (Neural Networks, Gradient Boosting) pre-trained on historical datasets to project load demand/weather variables and charge/discharge batteries cost-effectively.", bullet_style))
    story.append(Paragraph("&bull; <b>Industrial Protocol Mapping:</b> Interface physical asset tags with standardized automation layers including Modbus TCP registers, CAN Bus BMS binary frames, OPC UA structures, and IEC 61850 Logical Nodes.", bullet_style))
    story.append(Paragraph("&bull; <b>Fault Diagnostics & Advisory System:</b> Deploy Isolation Forest anomaly detection to isolate sensor drifts, evaluate remaining useful life (RUL) of components, and pair system warnings with structured fault troubleshooting steps.", bullet_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("3. Technology Stack", h1_style))
    
    tech_headers = ["Layer", "Technology", "Purpose & Implementation"]
    tech_rows = [
        ["Frontend UI", "React 19, TailwindCSS, Chart.js, Vite", "Renders responsive HMI dashboards, connections widgets, historical logs tables, and event journal views."],
        ["Vanilla HMI", "Vanilla Javascript, HTML5 Canvas, HSL CSS", "Legacy browser HMI displaying a synoptic interactive power flow graphic with animated line speeds and faceplates."],
        ["Backend Core", "FastAPI (Python 3.10+), Uvicorn", "Asynchronous web server hosting REST controller routing and high-performance WebSockets broadcast sockets."],
        ["Historian DB", "SQLite (PostgreSQL compatible)", "Maintains settings (ems_settings), alarm histories (alarms_log), and time-series telemetry tables."],
        ["AI & Diagnostic", "Scikit-Learn, MLP Neural Networks, isolation Forest", "Predicts diurnal parameters, isolates outliers, and calculates battery capacity degradation."],
        ["Automation", "Modbus TCP, CAN Bus, OPC UA, IEC 61850", "Simulates register mappings, binary BMS packets, OPC UA address space, and breakers logical nodes."]
    ]
    tech_data = [[Paragraph(h, table_header_style) for h in tech_headers]]
    for r in tech_rows:
        tech_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style)
        ])
    tech_table = Table(tech_data, colWidths=[80, 140, 320])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(tech_table)
    
    story.append(PageBreak())
    
    # ================= PAGE 2 =================
    story.append(Paragraph("4. Telemetry Dataset Architecture", h1_style))
    story.append(Paragraph(
        "The APEX system preloads default historical datasets to pretrain machine learning models and to drive "
        "dashboard telemetry tags during fallback mode when hardware sensors are disconnected or configured to 'Sample CSV'.",
        body_style
    ))
    
    dataset_headers = ["Dataset File", "Primary Columns", "Physical Dynamics & Formulas", "Role & Size"]
    dataset_rows = [
        ["solar_dataset.csv", "timestamp, Solar_Power, Solar_Voltage, Solar_Current, Solar_Temperature", 
         "100 kW max capacity. Sinusoidal power peak at 12:00 PM: P = 100 * sin(pi * (h-6)/12). Panels heat up under sunlight: T = T_ambient + 15 * IrradFactor. Volt = 380-420V DC.", "202 rows.<br/>Pretrains solar GB models & loop fallback."],
        
        ["wind_dataset.csv", "timestamp, Wind_Power, Wind_Speed, Wind_RPM", 
         "50 kW max capacity. Cut-in: 3.0 m/s, Rated: 12.0 m/s, Cut-out: 25.0 m/s. Cubic curve P = 50 * ((v-3)/9)^3. RPM scales: RPM = 100 + 400 * ((v-3)/9).", "202 rows.<br/>Pretrains wind turbine GB model."],
        
        ["battery_dataset.csv", "timestamp, Battery_SOC, Battery_Voltage, Battery_Current, Battery_Temp, Battery_SOH", 
         "200 kWh BESS pack. 96S configuration. Pack voltage: V = 320.0 + 95.0 * (SOC/100) + I * 0.15. Charge current is negative; discharge is positive.", "202 rows.<br/>Pretrains battery SOC GB model."],
        
        ["load_dataset.csv", "timestamp, Load_Demand, Load_Voltage, Load_Current", 
         "Dynamic load with dual daily peaks (8 AM and 7 PM). Base load of 25 kW. Single phase AC feeder: V = 230V, I = (P * 1000) / V.", "202 rows.<br/>Pretrains auto-regressive MLP demand forecaster."],
        
        ["inverter_dataset.csv", "timestamp, Inverter_Output_Power, Inverter_Efficiency, Inverter_Status", 
         "Conversion efficiency scales from 95% to 99%, dipping at low capacities due to core losses: Eff = 98.5 - (1.5 / LoadRatio).", "202 rows.<br/>Fallback telemetry loop data source."],
        
        ["grid_dataset.csv", "timestamp, Grid_Power, Grid_Voltage, Grid_Frequency", 
         "Nominal 400V 3-phase connection at 50 Hz. Positive = Import from utility, Negative = Export. Frequency drifts slightly with network load.", "202 rows.<br/>Grid coupling billing logs fallback."],
        
        ["grid_exports_dataset.csv", "datetime, timestamp, solar_power, wind_power, battery_soc, grid_power, load_demand, ems_action, electricity_cost...", 
         "Log-traces all 26 telemetry points in the microgrid system at 1Hz execution frequency. Used to validate reinforcement learning optimizer.", "13,422 rows (2.67 MB).<br/>Audits dispatch logic, cost analytics & neural nets."]
    ]
    
    dataset_data = [[Paragraph(h, table_header_style) for h in dataset_headers]]
    for r in dataset_rows:
        dataset_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style),
            Paragraph(r[3], table_cell_style)
        ])
    dataset_table = Table(dataset_data, colWidths=[95, 100, 245, 100])
    dataset_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(dataset_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("5. Key Parameters & Safety Thresholds", h1_style))
    story.append(Paragraph(
        "SCADA supervisors continuously evaluate measurements against physical limits to trigger safety overrides "
        "and register alarms in the Event Journal.",
        body_style
    ))
    
    thresh_headers = ["Parameter", "Normal Range", "Warning Limit", "Critical Limit", "Automated Mitigation Action"]
    thresh_rows = [
        ["Battery SOC", "20.0% - 95.0%", "SOC <= 20.0%", "SOC <= 15.0%", "Activates tiered load shedding in islanding mode to protect battery cells."],
        ["Battery Temp", "15.0C - 35.0C", "Temp >= 45.0C", "Temp >= 55.0C / Temp <= -10.0C", "Warning derates charge rates by 50%. Critical isolates BESS (0 kW flow)."],
        ["Feeder Current", "10A - 150A", "Current >= 160A", "Current >= 180A", "Triggers over-current warning (LOAD-OC-001) and opens circuit breakers."],
        ["Grid Voltage", "380V - 420V", "Voltage >= 430V", "Voltage >= 440V", "Registers grid overvoltage fault (GRID-OV-001). Isolates inverter."],
        ["Grid Frequency", "49.8 - 50.2 Hz", "Freq <= 49.5 / >= 50.5 Hz", "Freq <= 49.0 / >= 51.0 Hz", "Registers warning alarm. Triggers utility sync mismatch warning."],
        ["Inverter Eff", "90.0% - 99.0%", "Eff <= 88.0%", "Eff <= 85.0%", "Flags inverter thermal cooling or IGBT wear anomalies in diagnostic suite."]
    ]
    
    thresh_data = [[Paragraph(h, table_header_style) for h in thresh_headers]]
    for r in thresh_rows:
        thresh_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style),
            Paragraph(r[3], table_cell_style),
            Paragraph(r[4], table_cell_style)
        ])
    thresh_table = Table(thresh_data, colWidths=[80, 80, 95, 95, 190])
    thresh_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(thresh_table)
    
    story.append(PageBreak())
    
    # ================= PAGE 3 =================
    story.append(Paragraph("6. System Working & Dispatch Logic", h1_style))
    
    story.append(Paragraph("6.1 EMS Power Flow State Machine", h2_style))
    story.append(Paragraph(
        "At each second, net surplus is evaluated: P_surplus = P_solar + P_wind - P_load. The dispatcher routes flows based on priority rules:<br/>"
        "1. <b>Renewables Priority</b>: PV and Wind are routed directly to satisfy Load demand first.<br/>"
        "2. <b>Renewable Surplus (P_surplus >= 0)</b>: Surplus power is directed to charge the battery bank. If Battery SOC >= 95%, the surplus is exported to the Grid.<br/>"
        "3. <b>Renewable Deficit (P_surplus < 0)</b>: If Battery SOC > 20%, the battery discharges to cover the load. Grid import is used as a final fallback.<br/>"
        "4. <b>Islanding Mode (Grid Outage)</b>: Utility grid status drops to 0. Breakers open. Tiered load shedding initiates based on SOC:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <i>SOC <= 25% (Level 1)</i>: Shed 30% load (isolate non-critical facility blocks).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <i>SOC <= 20% (Level 2)</i>: Shed 60% load (isolate heavy HVAC machinery).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <i>SOC <= 15% (Level 3)</i>: Shed 85% load (vital infrastructure hospital/safety lines only).",
        body_style
    ))
    
    story.append(Paragraph("6.2 Q-Learning Tariff Optimizer", h2_style))
    story.append(Paragraph(
        "A reinforcement learning agent schedules charge/discharge offsets during grid-connected modes to minimize costs:<br/>"
        "&bull; <b>Discretized States:</b> S = (hour_bin, soc_bin, surplus_bin) where hour is grouped in 4-hour bins, SOC in 20% bins, and surplus into [Deficit, Balanced, Surplus].<br/>"
        "&bull; <b>Discrete Actions:</b> A = [-20 kW (Discharge), 0 kW (Standby), +20 kW (Charge)].<br/>"
        "&bull; <b>Time-of-Use Tariff rates:</b> ₹7.50 / kWh peak (14:00 - 20:00), and ₹4.50 / kWh off-peak.<br/>"
        "&bull; <b>Reward Function:</b> Reward = -(Electricity Cost) - beta * |I_battery|, where beta represents a cell degradation cycling penalty.<br/>"
        "&bull; <b>Bellman Q-Value updates:</b> Q(s,a) = Q(s,a) + alpha * [Reward + gamma * max_a(Q(s', a')) - Q(s,a)].",
        body_style
    ))
    
    story.append(Paragraph("6.3 Isolation Forest Anomaly Detection", h2_style))
    story.append(Paragraph(
        "Identifies sensor deviations or dropouts by evaluating the feature vector: X = [Grid_Voltage, Load_Current, Battery_Temperature, Inverter_Efficiency] "
        "against an isolation model trained with a Contamination factor of 3%. Outlier scores closer to -1.0 trigger alarm 'AI-ANOM-001' with troubleshooting steps.",
        body_style
    ))
    
    story.append(Paragraph("6.4 Predictive Maintenance RUL Formulas", h2_style))
    story.append(Paragraph(
        "Computes hardware health metrics and Remaining Useful Life (RUL) values in hours:<br/>"
        "&bull; <b>PCS Inverter Health:</b> H_inv = 98.2 - 1.5 * max(0, (T_inverter - 50.0) / 30.0). Inverter RUL = 12000 hours * (H_inv / 100).<br/>"
        "&bull; <b>Battery SOH thermal aging:</b> Degradation is exponential to temperature: Kappa = exp(0.04 * (T_battery - 25.0)). BESS RUL = (6000 * SOH / 100) / Kappa.",
        body_style
    ))
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("7. Backend & Frontend Code Design", h1_style))
    
    code_headers = ["File Name", "Component / Functions", "Operational Description"]
    code_rows = [
        ["backend/main.py", "FastAPI App Server<br/>run_microgrid_loop()<br/>ws_endpoint()", "Runs non-blocking 1Hz daemon. Loosely reads CSV datasets in fallback, processes active WebSockets telemetry streams, and services REST overrides."],
        ["backend/database.py", "SQLite Database Manager<br/>log_telemetry()<br/>trigger_alarm()", "Logs 1Hz historian metrics to relational tables. Prevents alarm database duplication spam using message prefix-matching rules."],
        ["backend/ems.py", "EMSEngine Core<br/>compute_dispatch()<br/>detect_alarms()", "Executes rule state machine, derates charge currents based on thermal stress, and matches alarms with field repair guides."],
        ["backend/ai_models.py", "AI & Forecasting Suite<br/>LSTMLoadForecaster<br/>AnomalyDetector", "MLP neural networks forecast loads. Isolation Forest classifies outliers. Computes component degradation & RUL calculations."],
        ["backend/protocols.py", "Register Brokers<br/>ModbusTCPSimulator<br/>CANBusSimulator", "Maps metrics to Holding registers (40001+). Packs voltage, current, and temp bytes into 8-byte frames at CAN ID 0x18F009A1."],
        ["backend/simulator.py", "Physics Twin Simulation<br/>update_battery_physics()", "Simulates dynamic ambient walks, panel irradiance heat, battery cell internal resistance voltage drop, and fan active cooling flows."],
        ["frontend/src/App.jsx", "React HMI Panel View", "Responsive dashboard containing dynamic SVG synoptic flows (animated speeds), Data Sources manager, Historian logger, and alarm acknowledge buttons."],
        ["index.js / html", "Vanilla HMI client", "Legacy local dashboard mapping SVG particles and canvas trend graphs."]
    ]
    
    code_data = [[Paragraph(h, table_header_style) for h in code_headers]]
    for r in code_rows:
        code_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style)
        ])
    code_table = Table(code_data, colWidths=[105, 155, 280])
    code_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(code_table)
    
    story.append(PageBreak())
    
    # ================= PAGE 4 =================
    story.append(Paragraph("8. Database Schema & Mappings", h1_style))
    story.append(Paragraph(
        "The relational storage database (SQLite) manages system settings, alarm chronicles, and high-frequency time-series telemetry.",
        body_style
    ))
    
    schema_headers = ["Table Name", "Columns Schema", "Mapping Description"]
    schema_rows = [
        ["ems_settings", "key (TEXT PRIMARY KEY), value (TEXT)", "Stores configuration setpoints (e.g. battery_min_soc: 20.0, tariff_peak_rate: 7.50)."],
        ["alarms_log", "id (INTEGER PK AUTOINCREMENT), timestamp (REAL), severity (TEXT), source (TEXT), message (TEXT), status (TEXT)", "Chronological alarms journal. Status values: ACTIVE, ACKNOWLEDGED, CLEARED."],
        ["scada_historian", "timestamp (REAL PRIMARY KEY), solar_power (REAL), solar_voltage (REAL), wind_power (REAL), battery_soc (REAL), battery_soh (REAL), battery_voltage (REAL), battery_current (REAL), battery_temperature (REAL), grid_status (INTEGER), grid_voltage (REAL), grid_frequency (REAL), grid_power (REAL), load_demand (REAL), load_current (REAL), load_voltage (REAL), inverter_status (TEXT), inverter_efficiency (REAL), inverter_output_power (REAL), ems_action (TEXT), electricity_cost (REAL)", "Stores 1Hz historical telemetry points of the microgrid system. Used for off-line diagnostics and analytical performance audits."],
        ["solar_realtime", "timestamp (REAL PRIMARY KEY), irradiance, ambient_temp, panel_temp, dc_voltage, dc_current, ac_power, inverter_status...", "Stores high-frequency sensor readings specifically connected to the Solar generation stack."],
        ["wind_realtime", "timestamp (REAL PRIMARY KEY), wind_speed, wind_direction, air_density, blade_angle, turbine_rpm, generator_voltage...", "Stores high-frequency sensor readings connected to the Wind turbine generation stack."],
        ["battery_realtime", "timestamp (REAL PRIMARY KEY), soc, soh, voltage, current, temperature, cell_voltage, cell_temperature, charge_rate...", "Stores high-frequency BMS readings connected to the BESS stack."],
        ["grid_realtime", "timestamp (REAL PRIMARY KEY), voltage, current, frequency, power_factor, import_power, export_power", "Stores grid voltage, frequencies and importing/exporting active power stats."],
        ["load_realtime", "timestamp (REAL PRIMARY KEY), load_voltage, load_current, active_power, reactive_power, apparent_power...", "Stores active/reactive power readings and feeder energy consumption totals."]
    ]
    
    schema_data = [[Paragraph(h, table_header_style) for h in schema_headers]]
    for r in schema_rows:
        schema_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style)
        ])
    schema_table = Table(schema_data, colWidths=[105, 230, 205])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(schema_table)
    story.append(Spacer(1, 10))
    
    # Implementation Timeline
    story.append(Paragraph("9. Implementation Timeline", h1_style))
    
    timeline_headers = ["Phase", "Milestone", "Deliverables", "Status"]
    timeline_rows = [
        ["P1", "Infrastructure setup", "FastAPI web server layout, SQLite database schemas mapping.", "Completed"],
        ["P2", "Responsive Web HMI", "Dynamic SVG synoptic flow animations, live canvas gauges.", "Completed"],
        ["P3", "Settings Management", "Relational configuration setpoints, peak/off-peak pricing overrides API.", "Completed"],
        ["P4", "Modbus TCP Protocol", "Holding registers mapping (40001 - 40010) and scaling equations.", "Completed"],
        ["P5", "CAN Bus BMS Gateway", "8-byte hexadecimal telemetry package framing, checksums.", "Completed"],
        ["P6", "AI Q-Learning Agent", "State space discretizations, Bellman policy updates, tariff shifts reward models.", "Completed"],
        ["P7", "OPC UA & IEC Nodes", "Node set directories, Circuit Breakers logical node statuses.", "Completed"],
        ["P8", "Fallback Replay Loop", "Caching dataset lists at boot, 1Hz sequential row looping.", "Completed"],
        ["P9", "Report Compilation", "Unit test validations, ReportLab PDF compilation, technical report.", "Completed"]
    ]
    
    timeline_data = [[Paragraph(h, table_header_style) for h in timeline_headers]]
    for r in timeline_rows:
        status_color = "#065f46" if r[3] == "Completed" else "#92400e"
        status_bg = "#d1fae5" if r[3] == "Completed" else "#fef3c7"
        
        # Inline badge table
        badge_p = Paragraph(f"<font color='{status_color}'><b>{r[3]}</b></font>", table_cell_style)
        badge = Table([[badge_p]], colWidths=[65], rowHeights=[12])
        badge.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(status_bg)),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(status_bg)),
        ]))
        
        timeline_data.append([
            Paragraph(r[0], table_cell_bold),
            Paragraph(r[1], table_cell_style),
            Paragraph(r[2], table_cell_style),
            badge
        ])
    timeline_table = Table(timeline_data, colWidths=[40, 110, 310, 80])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(timeline_table)
    story.append(Spacer(1, 10))
    
    # Conclusion box
    conclusion_text = (
        "<b>Conclusion</b><br/>"
        "APEX is a modular, high-fidelity microgrid SCADA and Energy Management System platform. By integrating "
        "industrial communication protocols (Modbus, CAN Bus, OPC UA, IEC 61850) with automated dispatch logic and "
        "reinforcement learning cost optimization, it achieves significant operational utility cost reductions while "
        "protecting BESS storage assets. The dual HMI client web panels and resilient cached fallback loops provide "
        "robust, reliable supervisory control and time-series telemetry data acquisition suitable for modern microgrid utilities."
    )
    conclusion_p = Paragraph(conclusion_text, ParagraphStyle('ConcText', parent=body_style, textColor=colors.HexColor('#1e3a8a')))
    conclusion_box = Table([[conclusion_p]], colWidths=[540])
    conclusion_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(conclusion_box)
    
    # Build Document
    doc.build(story, onFirstPage=draw_page_decorations, onLaterPages=draw_page_decorations)
    print(f"Detailed Technical Report PDF generated successfully: {pdf_filename}")

if __name__ == "__main__":
    generate_detailed_report()
