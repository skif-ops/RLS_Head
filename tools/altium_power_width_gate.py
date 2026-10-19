from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


SCHEMA = "ALTIUM-POWER-WIDTH-GATE-001"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def required_width_mm(
    *,
    current_a: float,
    copper_um: float,
    temp_rise_c: float,
) -> float:
    # IPC-2221 external-conductor screening equation.
    # Area is in mil^2, copper thickness in mil, width returned in mm.
    k = 0.048
    area_mil2 = (
        current_a
        / (
            k
            * temp_rise_c ** 0.44
        )
    ) ** (1.0 / 0.725)

    copper_mil = (
        copper_um
        / 25.4
    )
    width_mil = area_mil2 / copper_mil
    return width_mil * 0.0254


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    model_path = (
        root
        / "altium"
        / "ALTIUM_POWER_WIDTH_SYS_001.csv"
    )
    budget_path = root / "POWER_BUDGET_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    if not model_path.is_file():
        errors.append("missing_power_width_model")
    if not budget_path.is_file():
        errors.append("missing_power_budget")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }

    model_rows = read_csv(model_path)
    budget_rows = read_csv(budget_path)

    budget_capacity: dict[str, float] = {}
    for row in budget_rows:
        rail = str(row.get("rail", "")).strip()
        if not rail:
            continue
        try:
            capacity = float(
                str(row.get("capacity", "")).strip()
            )
        except ValueError:
            continue
        budget_capacity[rail] = max(
            capacity,
            budget_capacity.get(rail, 0.0),
        )

    expected_currents = {
        "VIN_RAW": budget_capacity.get("12V_IN", 0.0),
        "VIN_PROTECTED": budget_capacity.get("12V_IN", 0.0),
        "RADAR_12V": budget_capacity.get("RADAR_12V", 0.0),
        "3V3_TRUNK": budget_capacity.get("3V3", 0.0),
    }

    results: list[dict] = []
    ids: set[str] = set()

    for row in model_rows:
        model_id = str(row.get("model_id", "")).strip()
        net = str(row.get("net_or_class", "")).strip()
        if not model_id:
            errors.append("blank_model_id")
            continue
        if model_id in ids:
            errors.append(f"duplicate_model_id:{model_id}")
        ids.add(model_id)

        current = float(row["current_a"])
        copper = float(row["copper_um"])
        temp_rise = float(row["allowed_temp_rise_c"])
        stated = float(row["calculated_min_width_mm"])
        selected = float(row["selected_width_mm"])

        calculated = required_width_mm(
            current_a=current,
            copper_um=copper,
            temp_rise_c=temp_rise,
        )

        if abs(calculated - stated) > 0.03:
            errors.append(
                f"calculation_mismatch:{model_id}:"
                f"{calculated:.3f}!={stated:.3f}"
            )

        if selected + 1e-9 < calculated:
            errors.append(
                f"selected_width_too_small:{model_id}:"
                f"{selected:.3f}<{calculated:.3f}"
            )

        expected = expected_currents.get(net)
        if expected is None:
            errors.append(
                f"unknown_power_net:{model_id}:{net}"
            )
        elif not math.isclose(
            current,
            expected,
            rel_tol=0.0,
            abs_tol=0.02,
        ):
            errors.append(
                f"current_budget_mismatch:{model_id}:"
                f"{current:.2f}!={expected:.2f}"
            )

        if row.get("status", "").strip() != "EVT_CALCULATED":
            errors.append(
                f"status:{model_id}"
            )

        results.append(
            {
                "model_id": model_id,
                "net_or_class": net,
                "current_a": current,
                "calculated_min_width_mm": round(
                    calculated,
                    3,
                ),
                "selected_width_mm": selected,
                "margin_mm": round(
                    selected - calculated,
                    3,
                ),
            }
        )

    if ids != {
        "PWR-001",
        "PWR-002",
        "PWR-003",
        "PWR-004",
    }:
        errors.append("model_set")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "models": results,
        "method": "IPC-2221_EXTERNAL_TRACE_SCREEN",
        "production_review_required": True,
        "notes": [
            (
                "This calculation is a conservative EVT routing-start "
                "screen only. Production release requires final copper, "
                "stackup and thermal review."
            ),
            (
                "Power routes should use polygons/pours where practical; "
                "the selected widths are minimum neck values."
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
