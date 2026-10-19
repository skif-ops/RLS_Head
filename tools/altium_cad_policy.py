from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "ALTIUM-CAD-POLICY-RESULT-001"


def _csv_ids(path: Path, field: str) -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or field not in reader.fieldnames:
            raise ValueError(f"{path}: missing {field}")
        return {
            str(row.get(field, "")).strip()
            for row in reader
            if str(row.get(field, "")).strip()
        }


def validate(root: str | Path) -> dict:
    root = Path(root)
    errors: list[str] = []
    warnings: list[str] = []

    authority_path = root / "CAD_AUTHORITY_SYS_001.json"
    import_path = root / "altium" / "ALTIUM_IMPORT_PROFILE_SYS_001.json"
    project_path = root / "altium" / "EVT_SYS_CARRIER.PrjPcb"
    stack_path = root / "altium" / "ALTIUM_LAYER_STACK_SYS_001.csv"
    rules_path = root / "altium" / "ALTIUM_RULES_SYS_001.csv"
    net_classes_path = root / "altium" / "ALTIUM_NET_CLASSES_SYS_001.csv"
    placement_path = root / "altium" / "ALTIUM_PLACEMENT_PLAN_SYS_001.csv"
    source_rules_path = root / "PCB_LAYOUT_CONSTRAINTS_SYS_001.csv"

    for path in (
        authority_path,
        import_path,
        project_path,
        stack_path,
        rules_path,
        net_classes_path,
        placement_path,
        source_rules_path,
    ):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    profile = json.loads(import_path.read_text(encoding="utf-8"))

    if authority.get("status") != "ALTIUM_PRIMARY":
        errors.append("authority_status")
    if authority.get("primary_cad") != "Altium Designer":
        errors.append("primary_cad")
    if authority.get("preserve_kicad") is not True:
        errors.append("preserve_kicad")
    if authority.get("delete_kicad_sources") is not False:
        errors.append("delete_kicad_sources")
    if authority.get("equivalence_gate_required") is not True:
        errors.append("equivalence_gate_required")

    project_text = project_path.read_text(encoding="utf-8-sig")
    if "[Design]" not in project_text:
        errors.append("prjpcb_design_section")
    if "DefaultConfiguration=Sources" not in project_text:
        errors.append("prjpcb_sources_configuration")

    if profile.get("target_cad") != "Altium Designer":
        errors.append("import_target_cad")
    if profile.get("preserve_source_files") is not True:
        errors.append("import_preserve_source")

    expected = {
        "compile_zero_errors",
        "compile_zero_warnings",
        "bom_designator_mpn_equivalence",
        "pinmap_equivalence",
        "connector_pinout_equivalence",
        "netlist_equivalence",
        "footprint_equivalence",
        "no_76_81GHz_rf_on_system_carrier",
    }
    actual = set(profile.get("post_import_checks", []))
    if not expected.issubset(actual):
        errors.append("post_import_checks")

    source_ids = _csv_ids(source_rules_path, "rule_id")
    mapped_ids = _csv_ids(rules_path, "source_rule_id")
    if source_ids != mapped_ids:
        errors.append(
            "altium_rule_mapping:"
            f"missing={sorted(source_ids - mapped_ids)}:"
            f"extra={sorted(mapped_ids - source_ids)}"
        )

    net_class_ids = _csv_ids(net_classes_path, "class_id")
    placement_ids = _csv_ids(placement_path, "zone_id")
    if len(net_class_ids) < 8:
        errors.append("net_class_count")
    if len(placement_ids) < 7:
        errors.append("placement_zone_count")

    with stack_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4:
        errors.append(f"layer_count:{len(rows)}!=4")
    else:
        orders = [str(row.get("order", "")).strip() for row in rows]
        if orders != ["1", "2", "3", "4"]:
            errors.append("layer_order")
        if "solid GND" not in str(rows[1].get("role", "")):
            errors.append("l2_ground_role")

    native_status = str(authority.get("native_document_status", ""))
    if native_status != "PENDING_ALTIUM_IMPORT":
        warnings.append(f"native_document_status:{native_status}")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "warnings": sorted(warnings),
        "source_rule_count": len(source_ids),
        "mapped_rule_count": len(mapped_ids),
        "layer_count": len(rows),
        "net_class_count": len(net_class_ids),
        "placement_zone_count": len(placement_ids),
        "primary_cad": authority.get("primary_cad"),
        "preserve_kicad": authority.get("preserve_kicad"),
        "native_document_status": native_status,
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
