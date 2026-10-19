from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-AUDIT-RESULT-001"

RULE_KIND_ALIASES = {
    "DifferentialPairRouting": "DiffPairsRouting",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _norm_scope(value: object) -> str:
    return re.sub(r"\\s+", "", _clean(value)).lower()


def validate(
    *,
    system_root: str | Path,
    audit_dir: str | Path,
) -> dict:
    system = Path(system_root)
    audit = Path(audit_dir)

    paths = {
        "component_inventory": audit / "component_inventory.csv",
        "net_inventory": audit / "net_inventory.csv",
        "rule_inventory": audit / "rule_inventory.csv",
        "pad_net_inventory": audit / "pad_net_inventory.csv",
        "layer_stack_inventory": audit / "layer_stack_inventory.csv",
    }

    errors: list[str] = []
    warnings: list[str] = []

    for artifact_id, path in paths.items():
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    components = read_csv(paths["component_inventory"])
    nets = read_csv(paths["net_inventory"])
    rules = read_csv(paths["rule_inventory"])
    pad_nets = read_csv(paths["pad_net_inventory"])
    layer_stack = read_csv(paths["layer_stack_inventory"])

    input_sha256 = {
        artifact_id: sha256_file(path)
        for artifact_id, path in paths.items()
    }

    component_refs = {
        _clean(row.get("designator"))
        for row in components
        if _clean(row.get("designator"))
    }

    with (
        system / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        bom_rows = list(csv.DictReader(handle))

    expected_refs = {
        _clean(row.get("ref"))
        for row in bom_rows
        if _clean(row.get("ref"))
    }

    missing_refs = sorted(expected_refs - component_refs)
    extra_refs = sorted(component_refs - expected_refs)

    if missing_refs:
        errors.append("missing_components:" + ",".join(missing_refs))
    if extra_refs:
        warnings.append("extra_components:" + ",".join(extra_refs))

    blank_patterns = sorted(
        _clean(row.get("designator"))
        for row in components
        if _clean(row.get("designator"))
        and not _clean(row.get("pattern"))
    )
    if blank_patterns:
        errors.append(
            "blank_footprint_pattern:" + ",".join(blank_patterns)
        )

    actual_nets = {
        _clean(row.get("net_name"))
        for row in nets
        if _clean(row.get("net_name"))
    }

    with (
        system / "NETLIST_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        net_rows = list(csv.DictReader(handle))

    required_nets = {
        _clean(row.get("net_name"))
        for row in net_rows
        if _clean(row.get("net_name"))
        and _clean(row.get("criticality")) in {"P0", "P1"}
    }

    missing_nets = sorted(required_nets - actual_nets)
    if missing_nets:
        errors.append("missing_p0_p1_nets:" + ",".join(missing_nets))

    actual_rules = {
        _clean(row.get("rule_name")): {
            "kind": _clean(row.get("rule_kind")),
            "scope_1": _clean(row.get("scope_1")),
            "scope_2": _clean(row.get("scope_2")),
            "enabled": _clean(row.get("drc_enabled")).lower(),
        }
        for row in rules
        if _clean(row.get("rule_name"))
    }

    with (
        system / "altium" / "ALTIUM_RULE_QUERY_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        rule_rows = list(csv.DictReader(handle))

    missing_rules: list[str] = []
    wrong_rule_kinds: list[str] = []
    for row in rule_rows:
        name = _clean(row.get("rule_name"))
        if not name:
            continue
        expected_kind = RULE_KIND_ALIASES.get(
            _clean(row.get("rule_family")),
            _clean(row.get("rule_family")),
        )
        if name not in actual_rules:
            missing_rules.append(name)
            continue

        actual_rule = actual_rules[name]
        if actual_rule["kind"] != expected_kind:
            wrong_rule_kinds.append(
                f"{name}:{expected_kind}!={actual_rule['kind']}"
            )

        if _norm_scope(actual_rule["scope_1"]) != _norm_scope(
            row.get("scope_1")
        ):
            errors.append(f"rule_scope_1_mismatch:{name}")
        if _norm_scope(actual_rule["scope_2"]) != _norm_scope(
            row.get("scope_2")
        ):
            errors.append(f"rule_scope_2_mismatch:{name}")
        if actual_rule["enabled"] not in {"true", "1", "yes"}:
            errors.append(f"rule_disabled:{name}")

    if missing_rules:
        errors.append("missing_rules:" + ",".join(sorted(missing_rules)))
    if wrong_rule_kinds:
        errors.append(
            "rule_kind_mismatch:" + ",".join(sorted(wrong_rule_kinds))
        )

    pad_map: dict[tuple[str, str], str] = {}
    duplicate_pads: list[str] = []
    for row in pad_nets:
        designator = _clean(row.get("designator"))
        pad_name = _clean(row.get("pad_name"))
        net_name = _clean(row.get("net_name"))
        if not designator or not pad_name:
            continue
        key = (designator, pad_name)
        previous = pad_map.get(key)
        if previous is not None and previous != net_name:
            duplicate_pads.append(
                f"{designator}.{pad_name}:{previous}|{net_name}"
            )
        pad_map[key] = net_name

    if duplicate_pads:
        errors.append(
            "conflicting_pad_records:"
            + ",".join(sorted(duplicate_pads))
        )

    with (
        system / "PINMAP_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        pinmap_rows = list(csv.DictReader(handle))

    pinmap_mismatches: list[str] = []
    pinmap_checked = 0
    for row in pinmap_rows:
        pin = _clean(row.get("physical_pin"))
        expected_net = _clean(row.get("net_name"))
        if not pin or not expected_net:
            continue
        pinmap_checked += 1
        actual_net = pad_map.get(("U1", pin), "")
        if actual_net != expected_net:
            pinmap_mismatches.append(
                f"U1.{pin}:{expected_net}!={actual_net or 'MISSING'}"
            )

    if pinmap_mismatches:
        errors.append(
            "pinmap_net_mismatch:"
            + ",".join(sorted(pinmap_mismatches))
        )

    with (
        system / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        symbol_pin_rows = list(csv.DictReader(handle))

    symbol_pin_mismatches: list[str] = []
    symbol_pin_checked = 0
    for row in symbol_pin_rows:
        if _clean(row.get("policy")) != "CONNECT":
            continue
        ref = _clean(row.get("ref"))
        pin = _clean(row.get("pin_number"))
        expected_net = _clean(row.get("connection"))
        if not ref or not pin or not expected_net:
            continue
        symbol_pin_checked += 1
        actual_net = pad_map.get((ref, pin), "")
        if actual_net != expected_net:
            symbol_pin_mismatches.append(
                f"{ref}.{pin}:{expected_net}!={actual_net or 'MISSING'}"
            )

    if symbol_pin_mismatches:
        errors.append(
            "symbol_pin_net_mismatch:"
            + ",".join(sorted(symbol_pin_mismatches))
        )

    with (
        system / "altium" / "ALTIUM_LAYER_STACK_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        expected_layer_rows = list(csv.DictReader(handle))

    expected_layers = [
        _clean(row.get("altium_layer"))
        for row in sorted(
            expected_layer_rows,
            key=lambda row: int(_clean(row.get("order")) or "0"),
        )
        if _clean(row.get("altium_layer"))
    ]
    actual_layers = [
        _clean(row.get("layer_name"))
        for row in sorted(
            layer_stack,
            key=lambda row: int(_clean(row.get("order")) or "0"),
        )
        if _clean(row.get("layer_name"))
    ]

    if actual_layers != expected_layers:
        errors.append(
            "layer_stack_mismatch:"
            + "|".join(expected_layers)
            + "!="
            + "|".join(actual_layers)
        )

    audit_status = "PASS" if not errors else "FAIL"
    verified_checks = {
        "native_pcb_audit": audit_status,
        "pinmap_equivalence": (
            "PASS" if not pinmap_mismatches else "FAIL"
        ),
        "stackup_equivalence": (
            "PASS" if actual_layers == expected_layers else "FAIL"
        ),
        "rules_equivalence": (
            "PASS"
            if not missing_rules
            and not wrong_rule_kinds
            and not any(
                item.startswith("rule_scope_")
                or item.startswith("rule_disabled:")
                for item in errors
            )
            else "FAIL"
        ),
    }

    return {
        "schema": SCHEMA,
        "status": audit_status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "component_count": len(component_refs),
        "expected_component_count": len(expected_refs),
        "net_count": len(actual_nets),
        "required_p0_p1_net_count": len(required_nets),
        "rule_count": len(actual_rules),
        "required_rule_count": len(rule_rows),
        "pad_record_count": len(pad_map),
        "pinmap_checked_count": pinmap_checked,
        "symbol_pin_checked_count": symbol_pin_checked,
        "layer_stack_count": len(actual_layers),
        "expected_layer_stack_count": len(expected_layers),
        "input_sha256": input_sha256,
        "verified_checks": verified_checks,
        "notes": [
            (
                "PASS cross-checks native components, P0/P1 net names, "
                "rule names/families, MCU pin-to-net assignments, direct "
                "symbol pin contracts and the four-layer copper stack."
            ),
            (
                "Exact footprint equivalence, hierarchy/port semantics, "
                "connector aggregate semantics and full rule scope/value "
                "equivalence remain controlled by dedicated evidence."
            ),
            (
                "The full ALTIUM_EQUIVALENCE_GATE still controls layout authority."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        audit_dir=args.audit_dir,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
