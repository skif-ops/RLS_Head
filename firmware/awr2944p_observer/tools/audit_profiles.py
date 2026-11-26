from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


LIGHT_SPEED_M_S = 299_792_458.0
IF_LIMIT_HZ = 20_000_000.0
ADC_RATE_LIMIT_HZ = 45_000_000.0
TARGET_FREQUENCY_HZ = 78_500_000_000.0
TARGET_RANGE_M = 300.0
TARGET_SPEED_M_S = 190.0 / 3.6
TX_COUNT = 4


def parse_cfg(path: Path) -> dict[str, list[list[str]]]:
    commands: dict[str, list[list[str]]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%"):
            continue
        fields = line.split()
        commands.setdefault(fields[0], []).append(fields[1:])
    return commands


def profile_metrics(fields: list[str]) -> dict[str, float]:
    profile_id = int(fields[0])
    start_frequency_ghz = float(fields[1])
    idle_time_us = float(fields[2])
    adc_start_us = float(fields[3])
    ramp_end_us = float(fields[4])
    slope_mhz_us = float(fields[7])
    adc_samples = int(fields[9])
    sample_rate_hz = float(fields[10]) * 1_000.0
    sample_time_us = adc_samples / sample_rate_hz * 1_000_000.0
    bandwidth_hz = slope_mhz_us * 1.0e12 * sample_time_us * 1.0e-6
    chirp_period_s = (idle_time_us + ramp_end_us) * 1.0e-6
    wavelength_m = LIGHT_SPEED_M_S / TARGET_FREQUENCY_HZ
    unambiguous_velocity_m_s = wavelength_m / (4.0 * TX_COUNT * chirp_period_s)
    return {
        "profile_id": profile_id,
        "start_frequency_ghz": start_frequency_ghz,
        "idle_time_us": idle_time_us,
        "adc_start_us": adc_start_us,
        "ramp_end_us": ramp_end_us,
        "slope_mhz_us": slope_mhz_us,
        "adc_samples": adc_samples,
        "sample_rate_hz": sample_rate_hz,
        "sample_time_us": sample_time_us,
        "bandwidth_hz": bandwidth_hz,
        "range_resolution_m": LIGHT_SPEED_M_S / (2.0 * bandwidth_hz),
        "beat_frequency_at_300m_hz": 2.0 * slope_mhz_us * 1.0e12 * TARGET_RANGE_M / LIGHT_SPEED_M_S,
        "chirp_period_us": chirp_period_s * 1.0e6,
        "native_unambiguous_velocity_m_s": unambiguous_velocity_m_s,
    }


def wrap_velocity(value: float, half_period: float) -> float:
    period = 2.0 * half_period
    return value - period * round(value / period)


def unwrap_velocity(measured: list[float], half_periods: list[float]) -> tuple[float, float]:
    period = 2.0 * half_periods[0]
    minimum_alias = math.ceil((-60.0 - measured[0]) / period)
    maximum_alias = math.floor((60.0 - measured[0]) / period)
    best_score = math.inf
    best_value = 0.0
    best_residual = math.inf
    for alias in range(minimum_alias, maximum_alias + 1):
        candidate = measured[0] + alias * period
        residuals = [
            abs(wrap_velocity(candidate - sample, half_period))
            for sample, half_period in zip(measured, half_periods, strict=True)
        ]
        score = sum(value * value for value in residuals)
        if score < best_score:
            best_score = score
            best_value = candidate
            best_residual = max(residuals)
    return best_value, best_residual


def audit(path: Path) -> dict[str, object]:
    commands = parse_cfg(path)
    profiles = [profile_metrics(fields) for fields in commands.get("profileCfg", [])]
    half_periods = [item["native_unambiguous_velocity_m_s"] for item in profiles]
    velocity_failures: list[dict[str, float]] = []
    if len(half_periods) == 3:
        for step in range(-600, 601):
            true_velocity = step * 0.1
            measured = [wrap_velocity(true_velocity, value) for value in half_periods]
            result, residual = unwrap_velocity(measured, half_periods)
            if abs(result - true_velocity) > 0.051 or residual > 1.5:
                velocity_failures.append({
                    "true_velocity_m_s": true_velocity,
                    "result_m_s": result,
                    "residual_m_s": residual,
                })
    geometry = commands.get("antGeometryCfg", [])
    geometry_pairs = 0
    if geometry:
        geometry_pairs = (len(geometry[0]) - 2) // 2
    operational = len(profiles) == 3
    calculated_range_pass = operational and all(
        item["beat_frequency_at_300m_hz"] < IF_LIMIT_HZ
        and item["sample_rate_hz"] <= ADC_RATE_LIMIT_HZ
        and item["adc_start_us"] + item["sample_time_us"] <= item["ramp_end_us"]
        for item in profiles
    )
    calculated_velocity_pass = operational and not velocity_failures
    return {
        "schema": "awr2944p_profile_audit_v1",
        "profile": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "scope": "calculated configuration audit without physical radar hardware",
        "profiles": profiles,
        "antenna_geometry_virtual_channels": geometry_pairs,
        "requirements": {
            "target_range_m": TARGET_RANGE_M,
            "target_speed_interval_km_h": [130.0, 190.0],
            "target_abs_speed_m_s": TARGET_SPEED_M_S,
            "calculated_range_gate": "PASS" if calculated_range_pass else "NOT_APPLICABLE_OR_FAIL",
            "calculated_three_prf_unwrap_gate": "PASS" if calculated_velocity_pass else "NOT_APPLICABLE_OR_FAIL",
        },
        "velocity_sweep": {
            "range_m_s": [-60.0, 60.0],
            "step_m_s": 0.1,
            "failure_count": len(velocity_failures),
            "first_failures": velocity_failures[:10],
        },
        "hardware_validation": "NOT_RUN",
        "phase_calibration": "NOT_RUN",
        "full_wave_antenna_validation": "NOT_RUN",
        "production_authority": "NOT_AUTHORIZED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profiles", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "reports": [audit(path) for path in args.profiles],
        "production_authority": "NOT_AUTHORIZED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
