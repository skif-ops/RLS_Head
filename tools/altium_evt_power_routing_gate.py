from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from tools.altium_power_width_gate import validate as validate_power_width


SCHEMA = "ALTIUM-EVT-POWER-ROUTING-GATE-001"
CONTRACT_SCHEMA = "ALTIUM-EVT-POWER-ROUTING-LOCK-001"


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
    contract_path = altium / "ALTIUM_EVT_POWER_ROUTING_LOCK_SYS_001.json"
    model_path = altium / "ALTIUM_POWER_WIDTH_SYS_001.csv"
    rule_path = altium / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv"
    budget_path = root / "POWER_BUDGET_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path in (contract_path, model_path, rule_path, budget_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
            "evt_power_routing_locked": False,
            "production_power_geometry_locked": False,
            "production_review_required": True,
        }

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"contract_parse:{exc}"],
            "warnings": warnings,
            "evt_power_routing_locked": False,
            "production_power_geometry_locked": False,
            "production_review_required": True,
        }

    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("contract_schema")
    if contract.get("status") != "EVT_ROUTING_LOCKED":
        errors.append("contract_status")
    if contract.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("contract_board_id")
    if contract.get("hardware_revision") != "A":
        errors.append("contract_hardware_revision")
    if contract.get("method") != "IPC-2221_EXTERNAL_TRACE_SCREEN":
        errors.append("contract_method")

    contract_copper = as_float(
        contract.get("copper_um"),
        field="contract.copper_um",
        errors=errors,
    )
    contract_temp = as_float(
        contract.get("allowed_temp_rise_c"),
        field="contract.allowed_temp_rise_c",
        errors=errors,
    )
    if not close(contract_copper, 35.0):
        errors.append("contract_copper_um")
    if not close(contract_temp, 10.0):
        errors.append("contract_temp_rise")

    production = contract.get("production")
    if not isinstance(production, dict):
        errors.append("contract_production")
        production = {}
    for field in (
        "final_copper_weight_review_required",
        "final_stack_review_required",
        "thermal_review_required",
    ):
        if production.get(field) is not True:
            errors.append(f"production_requirement:{field}")
    if production.get("production_power_geometry_locked") is not False:
        errors.append("production_power_geometry_locked_must_be_false")

    routing_policy = contract.get("routing_policy")
    if not isinstance(routing_policy, dict):
        errors.append("contract_routing_policy")
        routing_policy = {}
    for field in (
        "prefer_polygons_or_pours",
        "selected_widths_are_minimum_necks",
        "local_pin_neckdown_allowed_only_when_required",
    ):
        if routing_policy.get(field) is not True:
            errors.append(f"routing_policy:{field}")

    expected_sources = {
        "hardware/system_carrier/altium/ALTIUM_POWER_WIDTH_SYS_001.csv",
        "hardware/system_carrier/altium/ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
        "hardware/system_carrier/POWER_BUDGET_SYS_001.csv",
    }
    locked_sources = contract.get("locked_sources")
    if not isinstance(locked_sources, list):
        errors.append("locked_sources")
    elif set(str(item) for item in locked_sources) != expected_sources:
        errors.append("locked_sources_set")

    net_contracts = contract.get("nets")
    if not isinstance(net_contracts, dict):
        errors.append("contract_nets")
        net_contracts = {}

    model_rows = read_csv(model_path)
    model_by_net = {
        str(row.get("net_or_class", "")).strip(): row
        for row in model_rows
        if str(row.get("net_or_class", "")).strip()
    }
    expected_nets = {
        "VIN_RAW",
        "VIN_PROTECTED",
        "RADAR_12V",
        "3V3_TRUNK",
        "5V_GNSS",
    }
    if set(model_by_net) != expected_nets:
        errors.append("power_model_net_set")
    if set(net_contracts) != expected_nets:
        errors.append("contract_net_set")

    for net in sorted(expected_nets):
        expected = net_contracts.get(net)
        row = model_by_net.get(net)
        if not isinstance(expected, dict) or row is None:
            continue

        current = as_float(
            row.get("current_a"),
            field=f"{net}.current_a",
            errors=errors,
        )
        copper = as_float(
            row.get("copper_um"),
            field=f"{net}.copper_um",
            errors=errors,
        )
        temp = as_float(
            row.get("allowed_temp_rise_c"),
            field=f"{net}.allowed_temp_rise_c",
            errors=errors,
        )
        selected = as_float(
            row.get("selected_width_mm"),
            field=f"{net}.selected_width_mm",
            errors=errors,
        )
        expected_current = as_float(
            expected.get("current_a"),
            field=f"contract.{net}.current_a",
            errors=errors,
        )
        expected_width = as_float(
            expected.get("min_neck_width_mm"),
            field=f"contract.{net}.min_neck_width_mm",
            errors=errors,
        )
        if not close(current, expected_current, 0.02):
            errors.append(f"power_current:{net}")
        if not close(copper, contract_copper):
            errors.append(f"power_copper:{net}")
        if not close(temp, contract_temp):
            errors.append(f"power_temp_rise:{net}")
        if not close(selected, expected_width):
            errors.append(f"power_selected_width:{net}")
        if str(row.get("status", "")).strip() != "EVT_CALCULATED":
            errors.append(f"power_source_status:{net}")

    rules = {
        str(row.get("rule_id", "")).strip(): row
        for row in read_csv(rule_path)
        if str(row.get("rule_id", "")).strip()
    }
    for net in sorted(expected_nets):
        expected = net_contracts.get(net)
        if not isinstance(expected, dict):
            continue
        rule_id = str(expected.get("rule_id", "")).strip()
        row = rules.get(rule_id)
        if not rule_id or row is None:
            errors.append(f"power_rule_missing:{net}")
            continue
        value = as_float(
            row.get("value"),
            field=f"{rule_id}.value",
            errors=errors,
        )
        expected_width = as_float(
            expected.get("min_neck_width_mm"),
            field=f"contract.{net}.min_neck_width_mm",
            errors=errors,
        )
        if not close(value, expected_width):
            errors.append(f"power_rule_value:{net}")
        if str(row.get("unit", "")).strip() != "mm":
            errors.append(f"power_rule_unit:{net}")

    temp_rule = rules.get("RV-024")
    if temp_rule is None:
        errors.append("power_temp_rule_missing")
    else:
        value = as_float(
            temp_rule.get("value"),
            field="RV-024.value",
            errors=errors,
        )
        if not close(value, contract_temp):
            errors.append("power_temp_rule_value")
        if str(temp_rule.get("unit", "")).strip() != "C":
            errors.append("power_temp_rule_unit")

    model_result = validate_power_width(root)
    if model_result.get("status") != "PASS":
        errors.append("power_width_gate_not_pass")
        errors.extend(
            "power_width_gate:" + str(item)
            for item in model_result.get("errors", [])
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "evt_power_routing_locked": status == "PASS",
        "production_power_geometry_locked": False,
        "production_review_required": True,
        "copper_um": contract_copper,
        "allowed_temp_rise_c": contract_temp,
        "models": model_result.get("models", []),
        "notes": [
            (
                "PASS locks only the EVT routing minimum power neck geometry "
                "and screening assumptions."
            ),
            (
                "Production release still requires final copper weight, stack "
                "and thermal review; this gate does not authorize manufacturing."
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
