from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


SCHEMA = "ALTIUM-IMPEDANCE-GATE-001"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def f(value: str) -> float:
    return float(str(value).strip())


def microstrip_z0(
    *,
    width_mm: float,
    height_mm: float,
    er: float,
) -> float:
    ratio = width_mm / height_mm
    effective_er = (
        (er + 1.0) / 2.0
        + (er - 1.0)
        / 2.0
        * (
            1.0 / math.sqrt(1.0 + 12.0 / ratio)
            + (
                0.04 * (1.0 - ratio) ** 2
                if ratio < 1.0
                else 0.0
            )
        )
    )

    if ratio <= 1.0:
        return (
            60.0
            / math.sqrt(effective_er)
            * math.log(
                8.0 / ratio
                + 0.25 * ratio
            )
        )

    return (
        120.0
        * math.pi
        / (
            math.sqrt(effective_er)
            * (
                ratio
                + 1.393
                + 0.667
                * math.log(ratio + 1.444)
            )
        )
    )


def edge_coupled_diff_z(
    *,
    width_mm: float,
    gap_mm: float,
    height_mm: float,
    er: float,
) -> float:
    single = microstrip_z0(
        width_mm=width_mm,
        height_mm=height_mm,
        er=er,
    )
    return (
        2.0
        * single
        * (
            1.0
            - 0.48
            * math.exp(
                -0.96 * gap_mm / height_mm
            )
        )
    )


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    stack_path = (
        root
        / "altium"
        / "ALTIUM_EVT_STACKUP_SYS_002.csv"
    )
    impedance_path = (
        root
        / "altium"
        / "ALTIUM_IMPEDANCE_START_SYS_001.csv"
    )

    errors: list[str] = []
    warnings: list[str] = []

    for path in (stack_path, impedance_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }

    stack = rows(stack_path)
    impedance = rows(impedance_path)

    total_thickness = sum(
        f(row["thickness_mm"])
        for row in stack
    )
    if not math.isclose(
        total_thickness,
        1.6,
        abs_tol=0.01,
    ):
        errors.append(
            f"stack_thickness:{total_thickness:.4f}"
        )

    l1_l2 = next(
        (
            row
            for row in stack
            if row["item"] == "DIELECTRIC"
            and row["altium_layer"] == "L1-L2"
        ),
        None,
    )
    if l1_l2 is None:
        errors.append("missing_l1_l2_dielectric")
        h = er = 0.0
    else:
        h = f(l1_l2["thickness_mm"])
        er = f(l1_l2["er_nominal"])
        if l1_l2["status"] != "EVT_PROVISIONAL":
            errors.append("l1_l2_status")

    results: list[dict] = []

    for row in impedance:
        model_id = row["model_id"]
        width = f(row["trace_width_mm"])
        target = f(row["target_ohm"])
        tolerance = f(row["tolerance_pct"])
        expected = f(row["calculated_ohm"])
        structure = row["structure"]

        if row["status"] != "EVT_CALCULATED":
            errors.append(
                f"impedance_status:{model_id}"
            )

        if structure == "MICROSTRIP":
            calculated = microstrip_z0(
                width_mm=width,
                height_mm=h,
                er=er,
            )
        elif structure == "EDGE_COUPLED_MICROSTRIP":
            gap = f(row["pair_gap_mm"])
            calculated = edge_coupled_diff_z(
                width_mm=width,
                gap_mm=gap,
                height_mm=h,
                er=er,
            )
        else:
            errors.append(
                f"unsupported_structure:{model_id}:{structure}"
            )
            continue

        if abs(calculated - expected) > 0.75:
            errors.append(
                f"calculated_mismatch:{model_id}:"
                f"{calculated:.2f}!={expected:.2f}"
            )

        allowed = target * tolerance / 100.0
        if abs(calculated - target) > allowed:
            errors.append(
                f"target_outside_tolerance:{model_id}:"
                f"{calculated:.2f}"
            )

        results.append(
            {
                "model_id": model_id,
                "target_ohm": target,
                "calculated_ohm": round(
                    calculated,
                    3,
                ),
                "error_pct": round(
                    100.0
                    * (calculated - target)
                    / target,
                    3,
                ),
                "trace_width_mm": width,
                "pair_gap_mm": (
                    f(row["pair_gap_mm"])
                    if row["pair_gap_mm"].strip()
                    else None
                ),
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "warnings": sorted(warnings),
        "stack_total_mm": round(total_thickness, 4),
        "l1_l2_dielectric_mm": h,
        "er_nominal": er,
        "models": results,
        "production_binding_required": True,
        "notes": [
            (
                "This is an EVT routing-start estimate only. "
                "Production impedance must be rebound to the selected "
                "fabricator stack and field-solver result."
            ),
            (
                "The analytical model intentionally provides a stable "
                "repository check, not a substitute for the fabricator "
                "impedance coupon/solver."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("system_carrier_root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.system_carrier_root)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
