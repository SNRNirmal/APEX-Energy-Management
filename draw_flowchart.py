import os
from PIL import Image, ImageDraw, ImageFont

def draw_flowchart():
    # Image properties: 1200 x 960 (Retina-grade resolution)
    width, height = 1200, 960
    bg_color = (248, 250, 252) # slate-50
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try loading fonts, fallback to default if not found
    font_paths = [
        "arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    font = None
    title_font = None
    for p in font_paths:
        try:
            font = ImageFont.truetype(p, 15)
            title_font = ImageFont.truetype(p, 18)
            break
        except Exception:
            continue
            
    if font is None:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Themes colors
    border_blue = (30, 58, 138)  # dark blue
    fill_blue = (239, 246, 255)  # light blue
    text_color = (15, 23, 42)    # slate-900
    arrow_color = (148, 163, 184) # slate-400
    
    def draw_rounded_box(cx, cy, w, h, title, subtitle_lines):
        x1, y1 = cx - w//2, cy - h//2
        x2, y2 = cx + w//2, cy + h//2
        # Draw shadow
        draw.rounded_rectangle([x1 + 3, y1 + 3, x2 + 3, y2 + 3], radius=8, fill=(226, 232, 240))
        # Draw box
        draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=fill_blue, outline=border_blue, width=2)
        # Draw title
        draw.text((cx, y1 + 15), title, fill=border_blue, font=title_font, anchor="mm")
        # Draw divider
        draw.line([x1 + 20, y1 + 30, x2 - 20, y1 + 30], fill=border_blue, width=1)
        # Draw subtitle lines
        y_text = y1 + 45
        for line in subtitle_lines:
            draw.text((x1 + 20, y_text), line, fill=text_color, font=font, anchor="lm")
            y_text += 20

    def draw_arrow(x, y_start, y_end):
        # Vertical line
        draw.line([x, y_start, x, y_end], fill=arrow_color, width=2)
        # Arrowhead
        draw.polygon([x - 6, y_end - 8, x + 6, y_end - 8, x, y_end], fill=border_blue)

    # 1. Start Box
    draw_rounded_box(600, 80, 420, 80, "1. Start: 1Hz Daemon Timer", [
        "• Non-blocking worker loop triggers every 1.0 second.",
        "• Restores context states and updates clock offsets."
    ])
    
    draw_arrow(600, 120, 180)
    
    # 2. Ingestion Box
    draw_rounded_box(600, 240, 480, 100, "2. Telemetry Data Scanning", [
        "• Checks asset connection state (Dropdown sources).",
        "• Fallback (Sample CSV): Loads next row sequence from cache.",
        "• Connected (Live): Ingests simulated mathematical physics."
    ])
    
    draw_arrow(600, 290, 360)
    
    # 3. AI Diagnostic Box
    draw_rounded_box(600, 420, 480, 100, "3. Diagnostic & Predictive Layer", [
        "• Outlier Classifier: Scores grid/inverter data via Isolation Forest.",
        "• Component Health: Integrates inverter heatsink thermal decay.",
        "• Battery State: Computes BESS capacity fades & RUL hours."
    ])
    
    draw_arrow(600, 470, 540)
    
    # 4. EMS State Machine Box
    draw_rounded_box(600, 600, 520, 100, "4. EMS Dispatch Decision Matrix", [
        "• Clamps commands to protect cells: SOC limits (20% - 95%).",
        "• Battery temperature safety: Derates or isolates cell flows.",
        "• Connected priority: Renewables support -> Charge -> Grid Export.",
        "• Outage priority: Support Load via BESS -> Tiered Load Shedding."
    ])
    
    draw_arrow(600, 650, 720)
    
    # 5. Historian & Logs Box
    draw_rounded_box(600, 770, 480, 80, "5. Logging & Alarm Commits", [
        "• Commits 1Hz metrics snapshot to time-series historian.",
        "• Evaluates safety bounds: fires/clears alarms in alarms_log."
    ])
    
    draw_arrow(600, 810, 880)
    
    # 6. Broadcast Box
    draw_rounded_box(600, 915, 460, 70, "6. Fieldbus Encoders & Broadcast", [
        "• Packs CAN Bus BMS frames and updates Modbus registers.",
        "• Broadcasts real-time JSON payload to WebSockets clients."
    ])
    
    # Loop-back connector drawing
    # Line left from Box 6
    draw.line([370, 915, 200, 915], fill=arrow_color, width=2)
    # Line up from bottom to top
    draw.line([200, 915, 200, 80], fill=arrow_color, width=2)
    # Line right into Box 1
    draw.line([200, 80, 390, 80], fill=arrow_color, width=2)
    # Arrow head pointing to Box 1
    draw.polygon([382, 80 - 6, 382, 80 + 6, 390, 80], fill=border_blue)
    
    # Save Image
    image.save("flowchart.png")
    print("Flowchart image generated successfully: flowchart.png")

if __name__ == "__main__":
    draw_flowchart()
