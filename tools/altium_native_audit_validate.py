from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-AUDIT-RESULT-001"


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


def validate(
    *,
    system_root: str | Path,
    audit_dir: str | Path,
) -> dict:
    system = Path(system_root)
    audit = Path(audit_dir)

    component_path = audit / "component_inventory.csv"
    net_path = audit / "net_inventory.csv"
    rule_path = audit / "rule_inventory.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path in (component_path, net_path, rule_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }

    components = read_csv(component_path)
    nets = read_csv(net_path)
    rules = read_csv(rule_path)

    input_sha256 = {
        "component_inventory": sha256_file(component_path),
        "net_inventory": sha256_file(net_path),
        "rule_inventory": sha256_file(rule_path),
    }

    component_refs = {
        str(row.get("designator", "")).strip()
        for row in components
        if str(row.get("designator", "")).strip()
    }

    with (
        system / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        bom_rows = list(csv.DictReader(handle))

    expected_refs = {
        str(row.get("ref", "")).strip()
        for row in bom_rows
        if str(row.get("ref", "")).strip()
    }

    missing_refs = sorted(expected_refs - component_refs)
    extra_refs = sorted(component_refs - expected_refs)

    if missing_refs:
        errors.append("missing_components:" + ",".join(missing_refs))
    if extra_refs:
        warnings.append("extra_components:" + ",".join(extra_refs))

    blank_patterns = sorted(
        str(row.get("designator", "")).strip()
        for row in components
        if str(row.get("designator", "")).strip()
        and not str(row.get("pattern", "")).strip()
    )
    if blank_patterns:
        errors.append(
            "blank_footprint_pattern:" + ",".join(blank_patterns)
        )

    actual_nets = {
        str(row.get("net_name", "")).strip()
        for row in nets
        if str(row.get("net_name", "")).strip()
    }

    with (
        system / "NETLIST_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        net_rows = list(csv.DictReader(handle))

    required_nets = {
        str(row.get("net_name", "")).strip()
        for row in net_rows
        if str(row.get("net_name", "")).strip()
        and str(row.get("criticality", "")).strip() in {"P0", "P1"}
    }

    missing_nets = sorted(required_nets - actual_nets)
    if missing_nets:
        errors.append("missing_p0_p1_nets:" + ",".join(missing_nets))

    actual_rule_names = {
        str(row.get("rule_name", "")).strip()
        for row in rules
        if str(row.get("rule_name", "")).strip()
    }

    with (
        system / "altium" / "ALTIUM_RULE_QUERY_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        rule_rows = list(csv.DictReader(handle))

    required_rule_names = {
        str(row.get("rule_name", "")).strip()
        for row in rule_rows
        if str(row.get("rule_name", "")).strip()
    }

    missing_rules = sorted(required_rule_names - actual_rule_names)
    if missing_rules:
        errors.append("missing_rules:" + ",".join(missing_rules))

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "component_count": len(component_refs),
        "expected_component_count": len(expected_refs),
        "net_count": len(actual_nets),
        "required_p0_p1_net_count": len(required_nets),
        "rule_count": len(actual_rule_names),
        "required_rule_count": len(required_rule_names),
        "input_sha256": input_sha256,
        "notes": [
            (
                "PASS is a native PCB inventory cross-check only; the "
                "full ALTIUM_EQUIVALENCE_GATE still controls layout authority."
            ),
            (
                "Footprint pattern non-empty is checked here; exact footprint "
                "equivalence remains controlled by the dedicated footprint report."
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
