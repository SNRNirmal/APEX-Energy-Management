"""
APEX-Energy — Phase 7 Performance Benchmarking & Empirical Metrics Script
========================================================================
Measures and records ACTUAL empirical performance metrics across the platform:
1. End-to-end simulation throughput (timesteps/sec)
2. Individual API endpoint response latency (ms)
3. Energy conservation verification metrics across 2,016 timesteps
4. Production constraint compliance rates across all industrial machinery
5. Generates machine-readable validation report: phase7_validation_report.json
"""

import sys
import os
import time
import json
import statistics

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app
from evaluation import apex_evaluator
from verification import apex_verifier
from decision_engine import apex_decision_engine


def benchmark_platform():
    client = TestClient(app)
    report = {
        "metadata": {
            "platform": "APEX-Energy: Production-Aware Autonomous Energy Orchestration Platform",
            "problem": "SU-01: Renewable Energy + Industrial Load Optimization",
            "phase": "Phase 7: Final Integration, Stress Testing & Demo Readiness",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scope": "Digital / Simulated Industrial Prototype (No claims of real factory deployment)"
        }
    }

    print("=" * 75)
    print("APEX-Energy: Phase 7 Performance & Stress Benchmark")
    print("=" * 75)

    # -------------------------------------------------------------
    # 1. API LATENCY BENCHMARKS
    # -------------------------------------------------------------
    endpoints_to_measure = [
        ("GET /api/scenario/details?day_index=1", "/api/scenario/details?day_index=1"),
        ("GET /api/evaluation/compare", "/api/evaluation/compare"),
        ("GET /api/evaluation/kpis", "/api/evaluation/kpis"),
        ("GET /api/forecast/renewable", "/api/forecast/renewable?horizon_minutes=180"),
        ("GET /api/decision/evaluate", "/api/decision/evaluate?solar_kw=65.0&wind_kw=20.0&battery_soc=60.0"),
        ("GET /api/decision/candidates", "/api/decision/candidates?machine_id=Machine_C"),
        ("GET /api/verification/status", "/api/verification/status"),
        ("GET /api/tags (telemetry)", "/api/tags")
    ]

    api_latency_results = {}
    print("\n[1/4] Measuring API Endpoint Latency (5 iterations per endpoint):")
    for label, url in endpoints_to_measure:
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            res = client.get(url)
            t1 = time.perf_counter()
            if res.status_code == 200:
                latencies.append((t1 - t0) * 1000.0)
            else:
                print(f"  WARNING: {label} returned HTTP {res.status_code}")

        if latencies:
            mean_lat = statistics.mean(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            api_latency_results[label] = {
                "mean_ms": round(mean_lat, 2),
                "min_ms": round(min_lat, 2),
                "max_ms": round(max_lat, 2),
                "samples": len(latencies)
            }
            print(f"  • {label:42s}: {mean_lat:6.2f} ms (min: {min_lat:5.2f}, max: {max_lat:5.2f})")

    report["api_performance"] = api_latency_results

    # -------------------------------------------------------------
    # 2. FULL 7-DAY SIMULATION THROUGHPUT (2,016 TIMESTEPS)
    # -------------------------------------------------------------
    print("\n[2/4] Measuring End-to-End Simulation Throughput (2,016 Timesteps):")
    dataset = apex_evaluator.load_dataset()
    
    t0 = time.perf_counter()
    apex_run = apex_evaluator.evaluate_apex(dataset)
    t1 = time.perf_counter()
    duration_sec = t1 - t0
    timesteps_per_sec = len(dataset) / max(0.0001, duration_sec)

    throughput_metrics = {
        "total_timesteps": len(dataset),
        "total_duration_sec": round(duration_sec, 4),
        "throughput_timesteps_per_sec": round(timesteps_per_sec, 2),
        "ms_per_timestep": round((duration_sec / len(dataset)) * 1000.0, 3)
    }
    report["simulation_throughput"] = throughput_metrics
    print(f"  • Processed {len(dataset)} timesteps in {duration_sec:.4f}s")
    print(f"  • Throughput: {timesteps_per_sec:.2f} timesteps/second ({throughput_metrics['ms_per_timestep']} ms/timestep)")

    # -------------------------------------------------------------
    # 3. STRICT ENERGY CONSERVATION & PHYSICS AUDIT
    # -------------------------------------------------------------
    print("\n[3/4] Running Strict Physics Verification Audit:")
    t0 = time.perf_counter()
    v_report = apex_verifier.verify_timeseries_dataset(tolerance_kw=0.015)
    t1 = time.perf_counter()

    physics_metrics = {
        "total_timesteps_verified": v_report["total_timesteps"],
        "passed_timesteps": v_report["verified_timesteps"],
        "failed_timesteps": v_report["failed_timesteps"],
        "compliance_rate_pct": v_report["compliance_rate_pct"],
        "max_balance_error_kw": v_report["max_balance_error_kw"],
        "mean_balance_error_kw": v_report["mean_balance_error_kw"],
        "verification_time_sec": round(t1 - t0, 4)
    }
    report["physics_validation"] = physics_metrics
    print(f"  • Verification Compliance: {physics_metrics['compliance_rate_pct']}% ({physics_metrics['passed_timesteps']}/{physics_metrics['total_timesteps_verified']})")
    print(f"  • Max Energy Balance Error: {physics_metrics['max_balance_error_kw']} kW")
    print(f"  • Mean Energy Balance Error: {physics_metrics['mean_balance_error_kw']} kW")

    # -------------------------------------------------------------
    # 4. PRODUCTION CONSTRAINT COMPLIANCE AUDIT
    # -------------------------------------------------------------
    print("\n[4/4] Auditing Industrial Production Constraint Compliance:")
    prod_comp = apex_run["production_compliance"]
    production_metrics = {
        "machine_a_continuous_quota_met": prod_comp["machine_a_quota_met"],
        "machine_b_shift_quota_met": prod_comp["machine_b_quota_met"],
        "machine_c_flexible_batch_quota_met": prod_comp["machine_c_quota_met"],
        "all_constraints_respected": prod_comp["all_constraints_respected"],
        "verification_compliance_pct": prod_comp["verification_compliance_pct"]
    }
    report["production_validation"] = production_metrics
    print(f"  • Machine A (25 kW Critical Continuous): {'PASS (100%)' if prod_comp['machine_a_quota_met'] else 'FAIL'}")
    print(f"  • Machine B (20 kW Semi-Flex Shifts):    {'PASS (100%)' if prod_comp['machine_b_quota_met'] else 'FAIL'}")
    print(f"  • Machine C (35 kW Flexible 3h Batch):   {'PASS (100%)' if prod_comp['machine_c_quota_met'] else 'FAIL'}")
    print(f"  • All Constraints Respected:             {prod_comp['all_constraints_respected']}")

    # -------------------------------------------------------------
    # 5. BASELINE VS APEX KEY PERFORMANCE COMPARISON
    # -------------------------------------------------------------
    comp = apex_evaluator.compare_baseline_vs_apex()
    report["kpi_benchmark"] = comp["cumulative_kpi_comparison"]
    report["key_takeaways"] = comp["key_takeaways"]

    out_file = os.path.join(backend_dir, "phase7_validation_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 75)
    print(f"Phase 7 Validation Report written successfully to:\n  {out_file}")
    print("=" * 75)
    return report

if __name__ == "__main__":
    benchmark_platform()
