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
    board_mechanical_path = root / "altium" / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv"
    placement_coord_path = root / "altium" / "ALTIUM_PLACEMENT_COORD_SYS_002.csv"
    routing_sequence_path = root / "altium" / "ALTIUM_ROUTING_SEQUENCE_SYS_001.csv"
    prelayout_values_path = root / "altium" / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv"
    layout_bom_path = root / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    full_footprint_path = root / "FOOTPRINT_ASSIGNMENT_SYS_002.csv"
    equivalence_checks_path = root / "altium" / "ALTIUM_EQUIVALENCE_CHECKS_SYS_001.csv"
    native_status_path = root / "altium" / "ALTIUM_NATIVE_STATUS_SYS_001.json"
    equivalence_template_path = root / "altium" / "equivalence" / "manifest.template.json"
    outjob_contract_path = root / "altium" / "ALTIUM_OUTJOB_CONTRACT_SYS_001.csv"
    release_checklist_path = root / "altium" / "ALTIUM_RELEASE_CHECKLIST_SYS_001.csv"
    board_planning_path = root / "altium" / "ALTIUM_BOARD_PLANNING_SYS_001.csv"
    dfm_profile_path = root / "altium" / "ALTIUM_DFM_PROFILE_SYS_001.csv"
    implementation_path = root / "altium" / "ALTIUM_IMPLEMENTATION_SEQUENCE_SYS_001.csv"
    status_path = root / "altium" / "ALTIUM_STATUS_SYS_001.json"
    source_rules_path = root / "PCB_LAYOUT_CONSTRAINTS_SYS_001.csv"

    for path in (
        authority_path,
        import_path,
        project_path,
        stack_path,
        rules_path,
        net_classes_path,
        placement_path,
        board_mechanical_path,
        placement_coord_path,
        routing_sequence_path,
        prelayout_values_path,
        layout_bom_path,
        full_footprint_path,
        equivalence_checks_path,
        native_status_path,
        equivalence_template_path,
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
        "hierarchy_equivalence",
        "rules_equivalence",
        "stackup_equivalence",
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
    equivalence_ids = _csv_ids(equivalence_checks_path, "check_id")
    layout_bom_refs = _csv_ids(layout_bom_path, "ref")
    full_footprint_refs = _csv_ids(full_footprint_path, "ref")
    prelayout_rule_ids = _csv_ids(prelayout_values_path, "rule_id")
    if len(net_class_ids) < 8:
        errors.append("net_class_count")
    if len(placement_ids) < 7:
        errors.append("placement_zone_count")
    if len(equivalence_ids) != 10:
        errors.append("equivalence_check_count")
    if layout_bom_refs != full_footprint_refs:
        errors.append(
            "layout_bom_footprint_ref_set"
        )
    if len(prelayout_rule_ids) < 18:
        errors.append("prelayout_rule_count")

    with board_mechanical_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        mechanical_rows = list(csv.DictReader(handle))
    outline = [
        row
        for row in mechanical_rows
        if str(row.get("kind", "")).strip() == "BOARD"
        and str(row.get("id", "")).strip() == "OUTLINE"
    ]
    if len(outline) != 1:
        errors.append("mechanical_outline")
    else:
        if str(outline[0].get("status", "")).strip() != "EVT_PROVISIONAL":
            warnings.append("mechanical_outline_status")

    native_status_doc = json.loads(
        native_status_path.read_text(encoding="utf-8")
    )
    if native_status_doc.get("primary_cad") != "Altium Designer":
        errors.append("native_status_primary_cad")
    if native_status_doc.get("review_a_status") != "PASS":
        errors.append("native_status_review_a")
    if (
        native_status_doc.get("native_import_status")
        != "WAITING_NATIVE_ALTIUM_IMPORT"
    ):
        warnings.append("native_import_status_changed")
    if (
        native_status_doc.get("layout_authority")
        != "NOT_AUTHORIZED"
    ):
        errors.append("layout_authority_before_equivalence")

    equivalence_template = json.loads(
        equivalence_template_path.read_text(encoding="utf-8")
    )
    if (
        equivalence_template.get("schema")
        != "ALTIUM-EQUIVALENCE-MANIFEST-001"
    ):
        errors.append("equivalence_template_schema")

    outjob_ids = _csv_ids(outjob_contract_path, "output_id")
    release_ids = _csv_ids(release_checklist_path, "check_id")
    planning_ids = _csv_ids(board_planning_path, "plan_id")
    dfm_ids = _csv_ids(dfm_profile_path, "dfm_id")
    implementation_ids = _csv_ids(implementation_path, "step_id")

    if len(outjob_ids) < 14:
        errors.append("outjob_contract_count")
    if len(release_ids) < 18:
        errors.append("release_checklist_count")
    if len(planning_ids) < 8:
        errors.append("board_planning_count")
    if len(dfm_ids) < 10:
        errors.append("dfm_profile_count")
    if len(implementation_ids) < 14:
        errors.append("implementation_step_count")

    status_data = json.loads(status_path.read_text(encoding="utf-8"))
    if status_data.get("schema") != "ALTIUM-PCB-IMPLEMENTATION-STATUS-001":
        errors.append("altium_status_schema")
    if status_data.get("current_phase") != "IMPORT_PREPARED":
        errors.append("altium_status_phase")
    if status_data.get("altium", {}).get("production_release_authorized") is not False:
        errors.append("premature_production_release")

    with outjob_contract_path.open("r", encoding="utf-8", newline="") as handle:
        out_rows = list(csv.DictReader(handle))
    required_outputs = {
        str(row.get("output_id", "")).strip()
        for row in out_rows
        if str(row.get("required", "")).strip() == "YES"
    }
    if len(required_outputs) < 13:
        errors.append("required_output_count")

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
        "outjob_contract_count": len(outjob_ids),
        "required_output_count": len(required_outputs),
        "release_checklist_count": len(release_ids),
        "board_planning_count": len(planning_ids),
        "dfm_profile_count": len(dfm_ids),
        "implementation_step_count": len(implementation_ids),
        "altium_phase": status_data.get("current_phase"),
        "equivalence_check_count": len(equivalence_ids),
        "layout_bom_ref_count": len(layout_bom_refs),
        "full_footprint_ref_count": len(full_footprint_refs),
        "prelayout_rule_count": len(prelayout_rule_ids),
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
