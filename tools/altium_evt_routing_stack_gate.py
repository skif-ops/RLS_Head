from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from tools.altium_impedance_gate import validate as validate_impedance


SCHEMA = "ALTIUM-EVT-ROUTING-STACK-GATE-001"
CONTRACT_SCHEMA = "ALTIUM-EVT-ROUTING-STACK-LOCK-001"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def as_float(value: object, *, field: str, errors: list[str]) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        errors.append(f"invalid_number:{field}")
        return math.nan


def close(a: float, b: float, tol: float = 1e-6) -> bool:
    return not math.isnan(a) and abs(a - b) <= tol


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    altium = root / "altium"
    contract_path = altium / "ALTIUM_EVT_ROUTING_STACK_LOCK_SYS_001.json"
    stack_path = altium / "ALTIUM_EVT_STACKUP_SYS_002.csv"
    impedance_path = altium / "ALTIUM_IMPEDANCE_START_SYS_001.csv"
    rule_values_path = altium / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path in (contract_path, stack_path, impedance_path, rule_values_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
            "evt_routing_stack_locked": False,
            "production_stack_locked": False,
            "production_binding_required": True,
        }

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"contract_parse:{exc}"],
            "warnings": warnings,
            "evt_routing_stack_locked": False,
            "production_stack_locked": False,
            "production_binding_required": True,
        }

    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("contract_schema")
    if contract.get("status") != "EVT_ROUTING_LOCKED":
        errors.append("contract_status")
    if contract.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("contract_board_id")
    if contract.get("hardware_revision") != "A":
        errors.append("contract_hardware_revision")

    production = contract.get("production")
    if not isinstance(production, dict):
        errors.append("contract_production")
        production = {}
    for field in (
        "fabricator_binding_required",
        "field_solver_required",
        "impedance_coupon_or_fabricator_control_required",
    ):
        if production.get(field) is not True:
            errors.append(f"production_requirement:{field}")
    if production.get("production_stack_locked") is not False:
        errors.append("production_stack_locked_must_be_false")

    locked_sources = contract.get("locked_sources")
    expected_sources = {
        "hardware/system_carrier/altium/ALTIUM_EVT_STACKUP_SYS_002.csv",
        "hardware/system_carrier/altium/ALTIUM_IMPEDANCE_START_SYS_001.csv",
        "hardware/system_carrier/altium/ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
    }
    if not isinstance(locked_sources, list):
        errors.append("locked_sources")
    elif set(str(item) for item in locked_sources) != expected_sources:
        errors.append("locked_sources_set")

    stack_rows = read_csv(stack_path)
    impedance_rows = read_csv(impedance_path)
    rule_rows = read_csv(rule_values_path)

    stack_contract = contract.get("stack")
    if not isinstance(stack_contract, dict):
        errors.append("contract_stack")
        stack_contract = {}

    expected_total = as_float(
        stack_contract.get("total_thickness_mm"),
        field="contract.stack.total_thickness_mm",
        errors=errors,
    )
    expected_copper = as_float(
        stack_contract.get("copper_um"),
        field="contract.stack.copper_um",
        errors=errors,
    )

    total = 0.0
    for row in stack_rows:
        thickness = as_float(
            row.get("thickness_mm"),
            field=f"stack.{row.get('sequence')}.thickness_mm",
            errors=errors,
        )
        if not math.isnan(thickness):
            total += thickness
        if str(row.get("status", "")).strip() != "EVT_PROVISIONAL":
            errors.append(
                "stack_source_status:"
                + str(row.get("sequence", "")).strip()
            )
        if str(row.get("item", "")).strip() == "COPPER":
            copper = as_float(
                row.get("copper_um"),
                field=f"stack.{row.get('sequence')}.copper_um",
                errors=errors,
            )
            if not close(copper, expected_copper):
                errors.append(
                    "stack_copper_um:"
                    + str(row.get("sequence", "")).strip()
                )

    if not close(total, expected_total, 0.01):
        errors.append(f"stack_total:{total:.4f}!={expected_total:.4f}")

    dielectric_expectations = {
        "L1-L2": stack_contract.get("l1_l2"),
        "L2-L3": stack_contract.get("l2_l3"),
        "L3-L4": stack_contract.get("l3_l4"),
    }
    for layer_name, expected in dielectric_expectations.items():
        if not isinstance(expected, dict):
            errors.append(f"contract_dielectric:{layer_name}")
            continue
        matches = [
            row
            for row in stack_rows
            if str(row.get("item", "")).strip() == "DIELECTRIC"
            and str(row.get("altium_layer", "")).strip() == layer_name
        ]
        if len(matches) != 1:
            errors.append(f"stack_dielectric_count:{layer_name}:{len(matches)}")
            continue
        row = matches[0]
        actual_h = as_float(
            row.get("thickness_mm"),
            field=f"stack.{layer_name}.thickness_mm",
            errors=errors,
        )
        actual_er = as_float(
            row.get("er_nominal"),
            field=f"stack.{layer_name}.er_nominal",
            errors=errors,
        )
        expected_h = as_float(
            expected.get("thickness_mm"),
            field=f"contract.{layer_name}.thickness_mm",
            errors=errors,
        )
        expected_er = as_float(
            expected.get("er_nominal"),
            field=f"contract.{layer_name}.er_nominal",
            errors=errors,
        )
        if not close(actual_h, expected_h):
            errors.append(f"stack_dielectric_height:{layer_name}")
        if not close(actual_er, expected_er):
            errors.append(f"stack_dielectric_er:{layer_name}")

    impedance_contract = contract.get("impedance")
    if not isinstance(impedance_contract, dict):
        errors.append("contract_impedance")
        impedance_contract = {}

    rows_by_class = {
        str(row.get("net_class", "")).strip(): row
        for row in impedance_rows
        if str(row.get("net_class", "")).strip()
    }
    for net_class in ("GNSS_RF", "ETH_MDI"):
        expected = impedance_contract.get(net_class)
        if not isinstance(expected, dict):
            errors.append(f"contract_impedance:{net_class}")
            continue
        row = rows_by_class.get(net_class)
        if row is None:
            errors.append(f"impedance_missing:{net_class}")
            continue
        if str(row.get("status", "")).strip() != "EVT_CALCULATED":
            errors.append(f"impedance_source_status:{net_class}")
        for field in ("structure", "signal_layer", "reference_layer"):
            if str(row.get(field, "")).strip() != str(expected.get(field, "")).strip():
                errors.append(f"impedance_{field}:{net_class}")
        numeric_fields = (
            ("target_ohm", "target_ohm"),
            ("trace_width_mm", "trace_width_mm"),
            ("tolerance_pct", "tolerance_pct"),
        )
        for row_field, expected_field in numeric_fields:
            actual = as_float(
                row.get(row_field),
                field=f"{net_class}.{row_field}",
                errors=errors,
            )
            target = as_float(
                expected.get(expected_field),
                field=f"contract.{net_class}.{expected_field}",
                errors=errors,
            )
            if not close(actual, target):
                errors.append(f"impedance_{row_field}:{net_class}")

        expected_gap = expected.get("pair_gap_mm")
        row_gap = str(row.get("pair_gap_mm", "")).strip()
        if expected_gap is None:
            if row_gap:
                errors.append(f"impedance_pair_gap:{net_class}")
        else:
            actual_gap = as_float(
                row_gap,
                field=f"{net_class}.pair_gap_mm",
                errors=errors,
            )
            target_gap = as_float(
                expected_gap,
                field=f"contract.{net_class}.pair_gap_mm",
                errors=errors,
            )
            if not close(actual_gap, target_gap):
                errors.append(f"impedance_pair_gap:{net_class}")

    rules = {
        str(row.get("rule_id", "")).strip(): row
        for row in rule_rows
        if str(row.get("rule_id", "")).strip()
    }
    expected_rule_values = {
        "RV-019": (0.26, "mm"),
        "RV-020": (0.20, "mm"),
        "RV-021": (0.36, "mm"),
        "RV-022": (0.18, "mm"),
    }
    for rule_id, (expected_value, expected_unit) in expected_rule_values.items():
        row = rules.get(rule_id)
        if row is None:
            errors.append(f"rule_missing:{rule_id}")
            continue
        actual_value = as_float(
            row.get("value"),
            field=f"{rule_id}.value",
            errors=errors,
        )
        if not close(actual_value, expected_value):
            errors.append(f"rule_value:{rule_id}")
        if str(row.get("unit", "")).strip() != expected_unit:
            errors.append(f"rule_unit:{rule_id}")

    impedance_result = validate_impedance(root)
    if impedance_result.get("status") != "PASS":
        errors.append("impedance_gate_not_pass")
        errors.extend(
            "impedance_gate:" + str(item)
            for item in impedance_result.get("errors", [])
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "evt_routing_stack_locked": status == "PASS",
        "production_stack_locked": False,
        "production_binding_required": True,
        "field_solver_required": True,
        "stack_total_mm": round(total, 4),
        "impedance_models": impedance_result.get("models", []),
        "notes": [
            (
                "PASS locks only the repository EVT routing stack and trace "
                "geometry baseline; it does not bind a production fabricator."
            ),
            (
                "Source stack rows intentionally remain EVT_PROVISIONAL and "
                "impedance rows EVT_CALCULATED to preserve production semantics."
            ),
            (
                "Production release still requires selected-fabricator stack "
                "binding and final field-solver/impedance control evidence."
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
