"""
APEX-Energy: Forecast Visual Validation Generator
=================================================
Generates high-resolution comparative charts of:
1. Actual Solar vs Predicted Solar vs Baseline (Persistence) over Test Set.
2. Solar Surge & Renewable-Rich Window Detection (12:00 - 15:00).
3. Actual Wind vs Predicted Wind.
Saves figure to sample_datasets/forecast_vs_actual.png
"""

import os
import matplotlib
matplotlib.use('Agg') # Headless backend
import matplotlib.pyplot as plt
import numpy as np
from forecasting import RenewableForecastingEngine

def generate_visual_validation():
    print("[Visualization] Initializing forecasting engine...")
    engine = RenewableForecastingEngine()
    
    # Run multi-step forecast starting at Day 2 08:00 AM through 16:00 PM (8 hours = 96 steps)
    res_surge = engine.predict_multi_step("2026-06-03 08:00:00", horizon_minutes=480, step_minutes=5)
    
    # Extract actuals for comparison
    start_idx = 672 # Day 2 08:00 AM
    actual_solar = [float(engine._raw_solar[start_idx + i]) for i in range(len(res_surge["predictions"]))]
    actual_wind = [float(engine._raw_wind[start_idx + i]) for i in range(len(res_surge["predictions"]))]
    pred_solar = [p["solar_generation_kw"] for p in res_surge["predictions"]]
    pred_wind = [p["wind_generation_kw"] for p in res_surge["predictions"]]
    time_labels = [p["timestamp"].split()[1][:5] for p in res_surge["predictions"]]
    
    # Persistence baseline (t-1 value projected)
    persistence_solar = [actual_solar[0]] + actual_solar[:-1]

    # Create 3-panel figure
    plt.style.use('dark_background')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig.suptitle('APEX-Energy: Phase 2 Renewable Generation Forecasting Validation', fontsize=16, fontweight='bold', color='#10b981', y=0.98)
    
    steps = np.arange(len(actual_solar))
    
    # ----------------------------------------------------
    # Panel 1: Solar Generation Forecast vs Actual
    # ----------------------------------------------------
    ax1.plot(steps, actual_solar, label='Actual Solar PV (kW)', color='#38bdf8', linewidth=2.5, alpha=0.9)
    ax1.plot(steps, pred_solar, label='Gradient Boosting Forecast (kW)', color='#f59e0b', linewidth=2.0, linestyle='--')
    ax1.plot(steps, persistence_solar, label='Persistence Baseline (kW)', color='#94a3b8', linewidth=1.2, linestyle=':', alpha=0.6)
    
    # Highlight Renewable-Rich Window (where solar > 50 kW)
    rich_mask = [p >= 50.0 for p in pred_solar]
    if any(rich_mask):
        first_rich = np.where(rich_mask)[0][0]
        last_rich = np.where(rich_mask)[0][-1]
        ax1.axvspan(first_rich, last_rich, color='#10b981', alpha=0.15, label='Detected Renewable-Rich Window (>50 kW)')
        ax1.text((first_rich + last_rich) / 2, 75, 'RENEWABLE SURGE WINDOW\n(Machine C Shift Opportunity)', 
                 color='#34d399', fontsize=11, fontweight='bold', ha='center',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#064e3b', edgecolor='#10b981', alpha=0.85))

    ax1.set_ylabel('Solar Power (kW)', fontsize=11, fontweight='bold')
    ax1.set_title('Solar PV Forecast vs Actual (Day 2: 08:00 to 16:00)', fontsize=12, fontweight='bold', pad=8)
    ax1.grid(True, alpha=0.2, linestyle='--')
    ax1.legend(loc='upper right', framealpha=0.8)
    ax1.set_ylim(-2, 105)

    # ----------------------------------------------------
    # Panel 2: Forecast Error (Residuals)
    # ----------------------------------------------------
    gb_error = np.array(actual_solar) - np.array(pred_solar)
    base_error = np.array(actual_solar) - np.array(persistence_solar)
    
    ax2.plot(steps, gb_error, label=f'GB Residual Error (MAE: {engine.metrics["solar"]["gb_mae"]} kW)', color='#f59e0b', linewidth=1.5)
    ax2.plot(steps, base_error, label=f'Persistence Error (MAE: {engine.metrics["solar"]["baseline_mae"]} kW)', color='#94a3b8', linewidth=1.0, alpha=0.5)
    ax2.axhline(0, color='#64748b', linestyle='--', linewidth=1)
    ax2.set_ylabel('Forecast Error (kW)', fontsize=11, fontweight='bold')
    ax2.set_title('Solar Forecast Residuals (Actual - Predicted)', fontsize=12, fontweight='bold', pad=8)
    ax2.grid(True, alpha=0.2, linestyle='--')
    ax2.legend(loc='upper right', framealpha=0.8)

    # ----------------------------------------------------
    # Panel 3: Wind Generation Forecast vs Actual
    # ----------------------------------------------------
    ax3.plot(steps, actual_wind, label='Actual Wind Turbine (kW)', color='#a78bfa', linewidth=2.0)
    ax3.plot(steps, pred_wind, label=f'GB Wind Forecast (MAE: {engine.metrics["wind"]["gb_mae"]} kW)', color='#ec4899', linewidth=1.8, linestyle='--')
    ax3.set_ylabel('Wind Power (kW)', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Time of Day (HH:MM)', fontsize=11, fontweight='bold')
    ax3.set_title('Wind Power Generation: Forecast vs Actual', fontsize=12, fontweight='bold', pad=8)
    ax3.grid(True, alpha=0.2, linestyle='--')
    ax3.legend(loc='upper right', framealpha=0.8)
    ax3.set_ylim(-2, 55)

    # Set x-ticks every 6 steps (every 30 mins)
    tick_indices = np.arange(0, len(steps), 6)
    ax3.set_xticks(tick_indices)
    ax3.set_xticklabels([time_labels[i] for i in tick_indices], rotation=45)

    plt.tight_layout()
    
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sample_datasets",
        "forecast_vs_actual.png"
    )
    plt.savefig(output_path, dpi=180)
    plt.close()
    print(f"[Visualization] Successfully generated visual validation chart: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_visual_validation()
