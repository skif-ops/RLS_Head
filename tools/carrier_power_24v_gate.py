from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-POWER-24V-GATE-001"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        return list(reader)


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    contract = json.loads(
        (root / "POWER_INPUT_24V_CONTRACT_SYS_001.json").read_text(
            encoding="utf-8"
        )
    )
    tree = _read_csv(root / "POWER_TREE_SYS_001.csv")
    bom = _read_csv(root / "BOM_SYS_CARRIER_LAYOUT_004.csv")
    errors: list[str] = []

    input_spec = contract["input"]
    efuse = contract["efuse"]
    bus = contract["intermediate_bus"]
    surge = contract["surge_protection"]
    authority = contract["authority"]

    input_min = float(input_spec["minimum_v"])
    input_max = float(input_spec["maximum_continuous_v"])
    output_v = float(bus["output_v"])
    output_a = float(bus["output_current_a"])
    efficiency = float(bus["minimum_efficiency_fraction"])
    ilim_nominal = (
        float(efuse["ilim_equation_numerator"])
        / float(efuse["ilim_resistor_ohm"])
    )
    ilim_min = ilim_nominal * (
        1.0 - float(efuse["ilim_tolerance_fraction"])
    )
    required_input_a = output_v * output_a / (input_min * efficiency)
    available_output_w = input_min * ilim_min * efficiency

    frequency = float(bus["switching_frequency_hz"])
    inductance = float(bus["inductance_h"])
    duty_at_max = output_v / input_max
    ripple_at_max_a = (
        (input_max - output_v) * duty_at_max
        / (inductance * frequency)
    )
    ripple_fraction = ripple_at_max_a / output_a
    peak_inductor_a = output_a + ripple_at_max_a / 2.0
    output_capacitance_f = (
        int(bus["output_capacitor_count"])
        * float(bus["output_capacitor_each_f"])
    )
    feedback_v = float(bus["feedback_reference_v"]) * (
        1.0
        + float(bus["feedback_top_ohm"])
        / float(bus["feedback_bottom_ohm"])
    )

    divider = efuse["divider_ohm"]
    r1 = float(divider["r1"])
    r2 = float(divider["r2"])
    r3 = float(divider["r3"])
    divider_total = r1 + r2 + r3
    ovp_v = 1.2 * divider_total / r3
    uvlo_v = 1.2 * divider_total / (r2 + r3)

    if not (17.5 <= uvlo_v <= 18.5):
        errors.append(f"uvlo:{uvlo_v:.3f}V")
    if not (33.0 <= ovp_v <= 34.0):
        errors.append(f"ovp:{ovp_v:.3f}V")
    if input_max >= ovp_v:
        errors.append("continuous_input_not_below_ovp")
    if required_input_a >= ilim_min:
        errors.append("efuse_current_margin")
    if available_output_w < output_v * output_a:
        errors.append("efuse_power_margin")
    if not (0.2 <= ripple_fraction <= 0.4):
        errors.append(f"inductor_ripple:{ripple_fraction:.3f}")
    if peak_inductor_a >= float(bus["inductor_saturation_a"]):
        errors.append("inductor_saturation_margin")
    if output_a >= float(bus["inductor_rms_a"]):
        errors.append("inductor_rms_margin")
    if output_capacitance_f < 150e-6:
        errors.append("output_capacitance")
    if abs(feedback_v - output_v) > 0.15:
        errors.append(f"feedback_voltage:{feedback_v:.3f}V")
    if float(surge["standoff_v"]) <= input_max:
        errors.append("tvs_standoff_margin")
    if (
        float(surge["maximum_clamp_v"])
        >= float(surge["protected_device_transient_limit_v"])
    ):
        errors.append("tvs_clamp_margin")

    by_ref = {
        str(row.get("ref", "")).strip(): row
        for row in bom
        if str(row.get("ref", "")).strip()
    }
    expected_parts = {
        "D1": surge["device"],
        "U6": efuse["device"],
        "U8": bus["regulator"],
        "L8": bus["inductor"],
        "Q6": efuse["reverse_blocking_fet"],
        "Q7": efuse["fast_pulldown_fet"],
    }
    for reference, expected in expected_parts.items():
        actual = str(by_ref.get(reference, {}).get("value_or_mpn", "")).strip()
        if actual != expected:
            errors.append(f"bom:{reference}:{actual}!={expected}")

    transitions = {
        (
            str(row.get("input_net", "")).strip(),
            str(row.get("output_net", "")).strip(),
            str(row.get("device", "")).strip(),
        )
        for row in tree
    }
    required_transitions = {
        ("VIN_RAW", "VIN_PROTECTED_24V", efuse["device"]),
        ("VIN_PROTECTED_24V", "V12_SYS", bus["regulator"]),
        ("V12_SYS", "3V3", "TPS62132RGTR"),
        ("V12_SYS", "5V_GNSS", "TPS62133RGTR"),
        ("V12_SYS", "RADAR_12V", "TPS259470ARPWR"),
    }
    for transition in sorted(required_transitions - transitions):
        errors.append("power_tree:" + "->".join(transition))

    for forbidden in contract["downstream"]["forbidden_direct_input_devices"]:
        if any(
            input_net == "VIN_PROTECTED_24V" and device == forbidden
            for input_net, _, device in transitions
        ):
            errors.append(f"direct_24v_downstream:{forbidden}")

    if authority.get("routing_authority") != "NOT_AUTHORIZED":
        errors.append("routing_authority")
    if authority.get("production_authority") != "NOT_AUTHORIZED":
        errors.append("production_authority")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "calculations": {
            "uvlo_v": round(uvlo_v, 4),
            "ovp_v": round(ovp_v, 4),
            "efuse_current_nominal_a": round(ilim_nominal, 4),
            "efuse_current_minimum_a": round(ilim_min, 4),
            "required_input_current_at_18v_a": round(required_input_a, 4),
            "available_output_power_at_18v_w": round(available_output_w, 3),
            "inductor_ripple_at_32v_a": round(ripple_at_max_a, 4),
            "inductor_ripple_fraction": round(ripple_fraction, 4),
            "inductor_peak_current_a": round(peak_inductor_a, 4),
            "output_capacitance_uf": round(output_capacitance_f * 1e6, 3),
            "feedback_output_v": round(feedback_v, 4),
        },
        "authority": authority,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", default="hardware/system_carrier")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate(args.system_root)
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
