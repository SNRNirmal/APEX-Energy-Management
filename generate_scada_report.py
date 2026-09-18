import os
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Group, Polygon

def draw_page_decorations(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#cbd5e1')) # slate-300
    canvas.setLineWidth(0.5)
    # Draw page border
    canvas.rect(20, 20, 612 - 40, 792 - 40, fill=0, stroke=1)
    
    # Draw page number in handwriting-like or standard font
    canvas.setFont("Helvetica-Oblique", 8.5)
    canvas.setFillColor(colors.HexColor('#64748b'))
    canvas.drawString(40, 32, f"Page - {doc.page}")
    canvas.restoreState()

def make_badge(text, bg_color, text_color, styles):
    p_style = ParagraphStyle(
        'BadgeText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        textColor=colors.HexColor(text_color),
        alignment=1 # Center
    )
    p = Paragraph(text, p_style)
    badge = Table([[p]], colWidths=[60], rowHeights=[13])
    badge.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(bg_color)),
    ]))
    return badge

def get_status_badge(status, styles):
    if status == "Completed":
        return make_badge("Completed", "#d1fae5", "#065f46", styles)
    elif status == "In Progress":
        return make_badge("In Progress", "#fef3c7", "#92400e", styles)
    else:
        return make_badge("Pending", "#f1f5f9", "#475569", styles)

def make_node(drawing, x, y, w, h, title, subtitle, bg_color, border_color, text_color):
    rect = Rect(x, y, w, h, rx=4, ry=4)
    rect.fillColor = colors.HexColor(bg_color)
    rect.strokeColor = colors.HexColor(border_color)
    rect.strokeWidth = 1.0
    drawing.add(rect)
    
    if subtitle:
        t_str = String(x + w/2, y + h/2 + 2, title, textAnchor='middle')
        t_str.fontName = 'Helvetica-Bold'
        t_str.fontSize = 7.5
        t_str.fillColor = colors.HexColor(text_color)
        drawing.add(t_str)
        
        s_str = String(x + w/2, y + h/2 - 7, subtitle, textAnchor='middle')
        s_str.fontName = 'Helvetica'
        s_str.fontSize = 6.0
        s_str.fillColor = colors.HexColor(text_color)
        drawing.add(s_str)
    else:
        t_str = String(x + w/2, y + h/2 - 3, title, textAnchor='middle')
        t_str.fontName = 'Helvetica-Bold'
        t_str.fontSize = 8.5
        t_str.fillColor = colors.HexColor(text_color)
        drawing.add(t_str)

def make_line(drawing, x1, y1, x2, y2, arrow=False, color='#94a3b8'):
    line = Line(x1, y1, x2, y2)
    line.strokeColor = colors.HexColor(color)
    line.strokeWidth = 1.0
    drawing.add(line)
    
    if arrow:
        if y1 > y2 and x1 == x2:
            arrow_head = Polygon([x2 - 3, y2 + 4, x2 + 3, y2 + 4, x2, y2])
            arrow_head.fillColor = colors.HexColor(color)
            arrow_head.strokeColor = colors.HexColor(color)
            drawing.add(arrow_head)
        elif y2 > y1 and x1 == x2:
            arrow_head = Polygon([x2 - 3, y2 - 4, x2 + 3, y2 - 4, x2, y2])
            arrow_head.fillColor = colors.HexColor(color)
            arrow_head.strokeColor = colors.HexColor(color)
            drawing.add(arrow_head)

def make_schema_table(title, columns, styles):
    header_style = ParagraphStyle(
        'SchemaHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        textColor=colors.white,
        alignment=1 # Center
    )
    cell_style = ParagraphStyle(
        'SchemaCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.0,
        leading=7.5
    )
    
    data = [[Paragraph(title, header_style)]]
    for col in columns:
        data.append([Paragraph(col, cell_style)])
        
    t = Table(data, colWidths=[165])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.0),
        ('TOPPADDING', (0,0), (-1,-1), 1.0),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    return t

def make_objective(title, text, styles):
    bullet_style = ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#2563eb'),
        alignment=0
    )
    bullet_col = Paragraph("&bull;", bullet_style)
    
    text_content = f"<b>{title}:</b> {text}"
    text_p = Paragraph(text_content, styles['BodyDark'])
    
    t = Table([[bullet_col, text_p]], colWidths=[12, 528])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    return t

def generate_report():
    pdf_filename = "APEX_Microgrid_SCADA_EMS_Report.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=1,
        alignment=0 # Left
    ))
    
    styles.add(ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=8,
        alignment=0
    ))
    
    styles.add(ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))
    
    styles.add(ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.0,
        leading=10.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=2
    ))
    
    styles.add(ParagraphStyle(
        'ObjectiveTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.0,
        leading=10.5,
        textColor=colors.HexColor('#1e3a8a')
    ))
    
    styles.add(ParagraphStyle(
        'ConclusionBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.0,
        leading=11.5,
        textColor=colors.HexColor('#1e3a8a')
    ))
    
    story = []
    
    # --- PAGE 1: TITLE & CORE INFO ---
    story.append(Paragraph("APEX MICROGRID EMS & SCADA", styles['DocTitle']))
    story.append(Paragraph("Hybrid Energy Management System & SCADA Controller Platform", styles['DocSubTitle']))
    
    # Header Info Table
    info_data = [
        [Paragraph("<b>Project Name</b>", styles['ObjectiveTitle']), Paragraph("APEX EMS &mdash; Hybrid Energy Management System &amp; SCADA Platform", styles['BodyDark'])],
        [Paragraph("<b>Project Type</b>", styles['ObjectiveTitle']), Paragraph("Supervisory Power Flow Dispatch, Logger &amp; AI Optimizer", styles['BodyDark'])],
        [Paragraph("<b>Platforms</b>", styles['ObjectiveTitle']), Paragraph("HTML5 Synoptic Dashboard, Modbus TCP, CAN Bus, OPC UA, IEC 61850", styles['BodyDark'])],
    ]
    info_table = Table(info_data, colWidths=[90, 450])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4))
    
    # Project Overview
    story.append(Paragraph("Project Overview", styles['SectionHeading']))
    overview_text = (
        "<b>APEX Microgrid EMS & SCADA</b> is an industrial-grade Energy Management System (EMS) and "
        "supervisory control platform designed to automate and optimize power flows within modern hybrid microgrids. "
        "The platform simulates physical energy assets—including Solar PV arrays, Wind turbines, Battery Energy Storage "
        "Systems (BESS), and Utility Grid ties—in real-time. It operates a rule-based state machine at "
        "1-second intervals to balance local load demands while minimizing energy import costs using a customized "
        "Q-learning reinforcement learning optimizer. A high-performance WebSockets interface feeds live synoptic "
        "HMI dashboard trends, logs historical sensor metrics to a high-frequency historian, and generates structured "
        "alarms for anomalous voltage or temperature excursions."
    )
    story.append(Paragraph(overview_text, styles['BodyDark']))
    story.append(Spacer(1, 4))
    
    # Core Objectives
    story.append(Paragraph("Core Objectives", styles['SectionHeading']))
    objectives = [
        ("Unified Power Flow HMI", "Develop an interactive, browser-based synoptic schematic visualizer with live sensor tags, directional flow animations, and device faceplate detail modals."),
        ("Multi-Protocol Simulation", "Provide bidirectional translation between microgrid physical metrics and common industrial automation protocols (Modbus TCP registers, CAN Bus BMS telemetry frames, OPC UA nodes, and IEC 61850 logical nodes)."),
        ("Intelligent Dispatch Logic", "Implement a robust 1Hz state machine enforcing microgrid energy balance rules across four distinct dispatch modes (Renewables Priority, Grid Export, Battery Support, and Grid Fallback)."),
        ("AI Q-Learning Optimizer", "Integrate a Q-learning agent configured with Time-of-Use (ToU) electricity pricing schemes and battery degradation penalties to dynamically schedule charge/discharge actions."),
        ("Industrial Historian & Alarms", "Build a high-frequency telemetry logging engine that pushes time-series tags and registers system alarms categorized by severity levels (INFO, WARNING, CRITICAL).")
    ]
    for title, text in objectives:
        story.append(make_objective(title, text, styles))
    story.append(Spacer(1, 4))
    
    # Technology Stack
    story.append(Paragraph("Technology Stack", styles['SectionHeading']))
    tech_headers = ["Layer", "Technology", "Purpose"]
    tech_rows = [
        ["Frontend UI", "Vanilla JS + HTML5 + CSS3 + Chart.js", "Ultra-fast load times, canvas-based live trending, synoptic SVG schematic, and modal faceplates."],
        ["Backend Core", "FastAPI (Python 3.10+)", "Asynchronous ASGI gateway serving REST endpoints and persistent WebSockets client streams."],
        ["Databases", "PostgreSQL + InfluxDB + MongoDB", "PostgreSQL settings, InfluxDB time-series telemetry, and MongoDB alarm logs. (Local SQLite fallback)."],
        ["AI & Forecasting", "Q-Learning + Polynomial Regression", "Reinforcement learning for BESS cost optimization and solar/load weather predictions."],
        ["Protocols", "CAN Bus, Modbus TCP, OPC UA, IEC 61850", "Industrial protocols mapped to simulated register arrays, BMS bytes, node trees, and breaker states."],
        ["Scheduler", "Async Background Daemon Loop", "Dedicated non-blocking 1Hz worker thread running state machine rules, DB logging, and telemetry updates."]
    ]
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.0,
        textColor=colors.white,
        alignment=0
    )
    cell_style_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        textColor=colors.HexColor('#1e40af')
    )
    cell_style_normal = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.0,
        leading=9
    )
    
    tech_data = [[Paragraph(h, header_style) for h in tech_headers]]
    for row in tech_rows:
        tech_data.append([
            Paragraph(row[0], cell_style_bold),
            Paragraph(row[1], cell_style_normal),
            Paragraph(row[2], cell_style_normal),
        ])
    
    tech_table = Table(tech_data, colWidths=[90, 180, 270])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1d4ed8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 4))
    
    # System Architecture Paragraph (Page 1 end)
    story.append(Paragraph("System Architecture", styles['SectionHeading']))
    arch_desc = (
        "The APEX platform follows a decoupled client-server architecture. The browser client connects to the FastAPI "
        "gateway using REST for settings changes and persistent WebSockets for live telemetry data streams. The backend "
        "runs an independent background loop mapping simulated microgrid states to databases and industrial protocol "
        "drivers."
    )
    story.append(Paragraph(arch_desc, styles['BodyDark']))
    story.append(PageBreak())
    
    # --- PAGE 2: ARCHITECTURE DIAGRAM & FEATURES ---
    story.append(Paragraph("System Architecture", styles['SectionHeading']))
    
    # Draw Architecture Flowchart
    d = Drawing(540, 270)
    
    # Theme colors definitions
    c_blue_bg, c_blue_bd, c_blue_tx = '#eff6ff', '#1d4ed8', '#1e3a8a'
    c_green_bg, c_green_bd, c_green_tx = '#ecfdf5', '#10b981', '#065f46'
    c_purp_bg, c_purp_bd, c_purp_tx = '#faf5ff', '#a855f7', '#581c87'
    c_amb_bg, c_amb_bd, c_amb_tx = '#fffbeb', '#d97706', '#7c2d12'
    
    # Layer 1: Dashboard UI
    make_node(d, 195, 230, 150, 30, "APEX SCADA Dashboard", "Vanilla JS + HTML5 + CSS3", c_blue_bg, c_blue_bd, c_blue_tx)
    make_line(d, 270, 230, 270, 210, arrow=True)
    
    # Layer 2: FastAPI Gateway
    make_node(d, 170, 180, 200, 30, "FastAPI Gateway Server", "Auth, Controls & REST/WebSockets", c_blue_bg, c_blue_bd, c_blue_tx)
    make_line(d, 270, 180, 270, 170)
    make_line(d, 72.5, 170, 467.5, 170)
    make_line(d, 72.5, 170, 72.5, 160)
    make_line(d, 202.5, 170, 202.5, 160)
    make_line(d, 332.5, 170, 332.5, 160)
    make_line(d, 467.5, 170, 467.5, 160)
    
    make_line(d, 72.5, 160, 72.5, 155, arrow=True)
    make_line(d, 202.5, 160, 202.5, 155, arrow=True)
    make_line(d, 332.5, 160, 332.5, 155, arrow=True)
    make_line(d, 467.5, 160, 467.5, 155, arrow=True)
    
    # Layer 3: Services
    make_node(d, 15, 120, 115, 35, "EMS Dispatcher", "Rule-based state machine", c_green_bg, c_green_bd, c_green_tx)
    make_node(d, 145, 120, 115, 35, "AI Q-Optimizer", "Q-Learning Model Core", c_purp_bg, c_purp_bd, c_purp_tx)
    make_node(d, 275, 120, 115, 35, "Historian & Logger", "Telemetry ingestion loop", c_green_bg, c_green_bd, c_green_tx)
    make_node(d, 405, 120, 120, 35, "Fieldbus Simulators", "Modbus / CAN / OPC drivers", c_green_bg, c_green_bd, c_green_tx)
    
    # Connect Layer 3 -> Layer 4
    make_line(d, 72.5, 120, 72.5, 108)
    make_line(d, 202.5, 120, 202.5, 108)
    make_line(d, 332.5, 120, 332.5, 108)
    make_line(d, 72.5, 108, 332.5, 108)
    make_line(d, 145, 108, 145, 105, arrow=True)
    
    make_line(d, 467.5, 120, 467.5, 108)
    make_line(d, 467.5, 108, 395, 108)
    make_line(d, 395, 108, 395, 105, arrow=True)
    
    # Layer 4: Databases & Protocol bridges
    make_node(d, 40, 70, 210, 35, "Database Storage Layer", "PostgreSQL | InfluxDB | MongoDB", c_green_bg, c_green_bd, c_green_tx)
    make_node(d, 290, 70, 210, 35, "Industrial Fieldbus Core", "Simulated Modbus, CAN & OPC UA", c_green_bg, c_green_bd, c_green_tx)
    
    # Connect Layer 4 -> Layer 5
    make_line(d, 145, 70, 145, 60)
    make_line(d, 72.5, 60, 202.5, 60)
    make_line(d, 72.5, 60, 72.5, 55, arrow=True)
    make_line(d, 202.5, 60, 202.5, 55, arrow=True)
    
    make_line(d, 395, 70, 395, 60)
    make_line(d, 332.5, 60, 467.5, 60)
    make_line(d, 332.5, 60, 332.5, 55, arrow=True)
    make_line(d, 467.5, 60, 467.5, 55, arrow=True)
    
    # Layer 5: Assets
    make_node(d, 15, 20, 115, 35, "Solar PV & Wind", "Renewable Generation", c_amb_bg, c_amb_bd, c_amb_tx)
    make_node(d, 145, 20, 115, 35, "BESS Battery Bank", "BMS CAN Telemetry", c_amb_bg, c_amb_bd, c_amb_tx)
    make_node(d, 275, 20, 115, 35, "Utility Grid Tie", "Modbus TCP / IEC 61850", c_amb_bg, c_amb_bd, c_amb_tx)
    make_node(d, 405, 20, 120, 35, "Microgrid Load", "Active Load Power", c_amb_bg, c_amb_bd, c_amb_tx)
    
    # Diagram Legend at bottom
    leg_y = 5
    r1 = Rect(30, leg_y, 10, 7, rx=1, ry=1)
    r1.fillColor = colors.HexColor(c_blue_bg)
    r1.strokeColor = colors.HexColor(c_blue_bd)
    d.add(r1)
    s1 = String(45, leg_y, "Core SCADA Layer", fontSize=6.5, fontName='Helvetica-Bold', fillColor=colors.HexColor(c_blue_tx))
    d.add(s1)
    
    r2 = Rect(155, leg_y, 10, 7, rx=1, ry=1)
    r2.fillColor = colors.HexColor(c_green_bg)
    r2.strokeColor = colors.HexColor(c_green_bd)
    d.add(r2)
    s2 = String(170, leg_y, "Core EMS Services", fontSize=6.5, fontName='Helvetica-Bold', fillColor=colors.HexColor(c_green_tx))
    d.add(s2)
    
    r3 = Rect(280, leg_y, 10, 7, rx=1, ry=1)
    r3.fillColor = colors.HexColor(c_purp_bg)
    r3.strokeColor = colors.HexColor(c_purp_bd)
    d.add(r3)
    s3 = String(295, leg_y, "AI Forecast & Optim", fontSize=6.5, fontName='Helvetica-Bold', fillColor=colors.HexColor(c_purp_tx))
    d.add(s3)
    
    r4 = Rect(405, leg_y, 10, 7, rx=1, ry=1)
    r4.fillColor = colors.HexColor(c_amb_bg)
    r4.strokeColor = colors.HexColor(c_amb_bd)
    d.add(r4)
    s4 = String(420, leg_y, "Simulated Assets", fontSize=6.5, fontName='Helvetica-Bold', fillColor=colors.HexColor(c_amb_tx))
    d.add(s4)
    
    story.append(d)
    story.append(Spacer(1, 10))
    
    # Core Features heading and Table
    story.append(Paragraph("Core Features", styles['SectionHeading']))
    
    features_headers = ["S.No", "Feature", "Description"]
    features_rows = [
        ["1", "Synoptic Power Flow HMI", "Dynamic SVG graphic displaying live power directions, colored state changes, flow speed animations, and details on active asset cards."],
        ["2", "Intelligent Power Dispatch", "Deterministic EMS state rules prioritizing local renewables, battery charging on surplus, and grid backup on deficit."],
        ["3", "Fieldbus Protocol Simulator", "Simulates bidirectional registers mapping for Modbus TCP, raw CAN frame parsing, and OPC UA/IEC substation node models."],
        ["4", "Q-Learning Energy Optimizer", "Minimizes cumulative microgrid operational electricity fees by shifting loads during peak tariffs based on weather-aware solar forecasts."],
        ["5", "Live Historian & Alarms", "Continuous data logging to sqlite/InfluxDB with threshold alerts (over-temperature, voltage limits) and warning acknowledgements."]
    ]
    
    features_data = [[Paragraph(h, header_style) for h in features_headers]]
    for row in features_rows:
        features_data.append([
            Paragraph(row[0], cell_style_normal),
            Paragraph(row[1], cell_style_bold),
            Paragraph(row[2], cell_style_normal)
        ])
        
    features_table = Table(features_data, colWidths=[40, 150, 350])
    features_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1d4ed8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(features_table)
    
    story.append(PageBreak())
    
    # --- PAGE 3: DATABASE SCHEMA & TIMELINE ---
    story.append(Paragraph("Database Schema", styles['SectionHeading']))
    story.append(Paragraph("Three core entities. PK = Primary Key, FK = Foreign Key.", styles['BodyDark']))
    story.append(Spacer(1, 3))
    
    # Setup sub-tables for schema side-by-side
    cols_settings = [
        "<b>key (PK)</b>",
        "value"
    ]
    cols_historian = [
        "<b>timestamp (PK)</b>",
        "solar_power",
        "solar_voltage",
        "solar_current",
        "solar_temperature",
        "wind_power",
        "wind_speed",
        "wind_rpm",
        "battery_soc",
        "battery_soh",
        "battery_voltage",
        "battery_current",
        "battery_temperature",
        "grid_status",
        "grid_voltage",
        "grid_frequency",
        "grid_power",
        "load_demand",
        "load_current",
        "load_voltage",
        "inverter_status",
        "inverter_efficiency",
        "inverter_output_power",
        "ems_action",
        "electricity_cost"
    ]
    cols_alarms = [
        "<b>id (PK)</b>",
        "timestamp",
        "severity",
        "source",
        "message",
        "status"
    ]
    
    table_settings = make_schema_table("EMS_SETTINGS", cols_settings, styles)
    table_historian = make_schema_table("SCADA_HISTORIAN", cols_historian, styles)
    table_alarms = make_schema_table("ALARMS_LOG", cols_alarms, styles)
    
    # Outer layout table to position three sub-tables side-by-side
    layout_data = [[table_settings, "", table_historian, "", table_alarms]]
    layout_table = Table(layout_data, colWidths=[165, 15, 165, 15, 165])
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(layout_table)
    story.append(Spacer(1, 8))
    
    # Implementation Timeline
    story.append(Paragraph("Implementation Timeline", styles['SectionHeading']))
    
    timeline_headers = ["Phase", "Milestone", "Deliverables", "Start", "End", "Status"]
    timeline_rows = [
        ["P1", "Infrastructure", "FastAPI setup, DB migrations, configuration", "18-05-26", "19-05-26", "Completed"],
        ["P2", "Frontend UI", "HMI SVG schematic, telemetry gauges, Chart.js", "18-05-26", "31-05-26", "Completed"],
        ["P3", "Auth & Admin", "Settings API, database seeding, credentials security", "20-05-26", "21-05-26", "Completed"],
        ["P4", "Modbus Protocol", "Holding registers mapping, inverter status codes", "22-05-26", "23-05-26", "Completed"],
        ["P5", "CAN Bus & BMS", "BMS telemetry frame encoder, checksum verification", "23-05-26", "24-05-26", "Completed"],
        ["P6", "AI Q-Optimizer", "Reinforcement Q-learning agent, state/action spaces", "24-05-26", "25-05-26", "Completed"],
        ["P7", "OPC UA & IEC", "OPC UA hierarchical nodes, IEC 61850 mappings", "26-05-26", "27-05-26", "In Progress"],
        ["P8", "Historian Replay", "Time-series database writer, CSV data upload APIs", "28-05-26", "29-05-26", "Pending"],
        ["P9", "Integration & QA", "Unit test execution, docker compose environment lock", "30-05-26", "31-05-26", "Pending"]
    ]
    
    timeline_data = [[Paragraph(h, header_style) for h in timeline_headers]]
    for row in timeline_rows:
        timeline_data.append([
            Paragraph(row[0], cell_style_bold),
            Paragraph(row[1], cell_style_normal),
            Paragraph(row[2], cell_style_normal),
            Paragraph(row[3], cell_style_normal),
            Paragraph(row[4], cell_style_normal),
            get_status_badge(row[5], styles)
        ])
        
    timeline_table = Table(timeline_data, colWidths=[35, 95, 185, 55, 55, 115])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1d4ed8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bfdbfe')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(timeline_table)
    story.append(Spacer(1, 8))
    
    # Styled Conclusion Box
    conclusion_text = (
        "<b>Conclusion</b><br/>"
        "APEX is a modular, high-fidelity SCADA and Energy Management System (EMS) platform that bridges industrial telemetry "
        "with reinforcement learning optimization. By consolidating fieldbus protocols, autonomous dispatch rules, and "
        "real-time visualization, it provides a comprehensive, production-ready supervisory control layer for modern microgrids."
    )
    conclusion_p = Paragraph(conclusion_text, styles['ConclusionBox'])
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
    print(f"Report generated successfully: {pdf_filename}")

if __name__ == "__main__":
    generate_report()
