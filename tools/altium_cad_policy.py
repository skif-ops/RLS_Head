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


def _phase_coherence(
    root: Path,
    authority: dict,
    status_data: dict,
) -> tuple[list[str], bool, bool]:
    errors: list[str] = []

    native_schdoc_path = (
        root / "altium" / "native" / "EVT_SYS_CARRIER.SchDoc"
    )
    native_pcbdoc_path = (
        root / "altium" / "native" / "EVT_SYS_CARRIER.PcbDoc"
    )
    native_schdoc = native_schdoc_path.is_file()
    native_pcbdoc = native_pcbdoc_path.is_file()

    if native_schdoc != native_pcbdoc:
        errors.append("native_document_pair")

    current_phase = str(status_data.get("current_phase", ""))
    altium_status = status_data.get("altium", {})
    if not isinstance(altium_status, dict):
        errors.append("altium_status_payload")
        altium_status = {}

    routing_status = status_data.get("routing_readiness", {})
    if not isinstance(routing_status, dict):
        errors.append("altium_routing_payload")
        routing_status = {}

    implementation_production = (
        altium_status.get("production_release_authorized") is True
    )
    authority_production = (
        authority.get("production_release_authorized") is True
    )
    if implementation_production != authority_production:
        errors.append("production_authority_mismatch")

    routing_authority = authority.get("routing_readiness_gate", {})
    if not isinstance(routing_authority, dict):
        errors.append("authority_routing_payload")
        routing_authority = {}

    if not native_schdoc and not native_pcbdoc:
        if current_phase != "IMPORT_PREPARED":
            errors.append("altium_status_phase")
        if implementation_production or authority_production:
            errors.append("premature_production_release")
        if authority.get("native_document_status") != "PENDING_ALTIUM_IMPORT":
            errors.append("authority_native_document_status")
        if (
            authority.get("pcb_layout_authority")
            != "ALTIUM_AFTER_EQUIVALENCE_GATE"
        ):
            errors.append("authority_layout_authority")
        if (
            routing_authority.get("current_expected_status")
            != "READY_FOR_NATIVE_IMPORT"
        ):
            errors.append("authority_routing_status")
        if routing_status.get("routing_authorized") is not False:
            errors.append("altium_routing_authorized")
        if (
            routing_status.get("expected_status")
            != "READY_FOR_NATIVE_IMPORT"
        ):
            errors.append("altium_routing_status")

    elif native_schdoc and native_pcbdoc:
        for field in ("native_schdoc", "native_pcbdoc"):
            if altium_status.get(field) is not True:
                errors.append(f"altium_status_{field}")

        if current_phase == "EQUIVALENCE_STALE":
            if altium_status.get("equivalence_gate") is not False:
                errors.append("altium_status_equivalence_gate")
            if implementation_production or authority_production:
                errors.append("stale_production_authority")
            if (
                authority.get("native_document_status")
                != "NATIVE_EQUIVALENCE_STALE"
            ):
                errors.append("authority_native_document_status")
            if authority.get("pcb_layout_authority") != "NOT_AUTHORIZED":
                errors.append("authority_layout_authority")
            if (
                authority.get("pcb_design_phase")
                != "ALTIUM_REEQUIVALENCE_REQUIRED"
            ):
                errors.append("authority_design_phase")
            if (
                routing_authority.get("current_expected_status")
                != "STALE_EQUIVALENCE"
            ):
                errors.append("authority_routing_status")
            if routing_status.get("routing_authorized") is not False:
                errors.append("altium_routing_authorized")
            if (
                routing_status.get("expected_status")
                != "STALE_EQUIVALENCE"
            ):
                errors.append("altium_routing_status")

        elif current_phase in {
            "READY_FOR_ROUTING",
            "PRODUCTION_RELEASED",
        }:
            if altium_status.get("equivalence_gate") is not True:
                errors.append("altium_status_equivalence_gate")
            if (
                authority.get("native_document_status")
                != "NATIVE_EQUIVALENCE_PASS"
            ):
                errors.append("authority_native_document_status")
            if (
                authority.get("pcb_layout_authority")
                != "ALTIUM_AUTHORIZED"
            ):
                errors.append("authority_layout_authority")
            if (
                routing_authority.get("current_expected_status")
                != "READY_FOR_ROUTING"
            ):
                errors.append("authority_routing_status")
            if routing_status.get("routing_authorized") is not True:
                errors.append("altium_routing_authorized")
            if (
                routing_status.get("expected_status")
                != "READY_FOR_ROUTING"
            ):
                errors.append("altium_routing_status")

            if current_phase == "PRODUCTION_RELEASED":
                if not (
                    implementation_production
                    and authority_production
                ):
                    errors.append("production_authority_missing")
                if (
                    authority.get("pcb_design_phase")
                    != "PRODUCTION_RELEASED"
                ):
                    errors.append("authority_design_phase")
                for field in ("placement_started", "routing_started"):
                    if altium_status.get(field) is not True:
                        errors.append(f"altium_status_{field}")
            else:
                if implementation_production or authority_production:
                    errors.append("premature_production_release")
                if (
                    authority.get("pcb_design_phase")
                    == "PRODUCTION_RELEASED"
                ):
                    errors.append("authority_design_phase")
        else:
            errors.append("altium_status_phase")

    return errors, native_schdoc, native_pcbdoc


def _native_status_coherence(
    native_status_doc: dict,
    status_data: dict,
) -> list[str]:
    errors: list[str] = []

    errors.extend(
        _native_status_coherence(
            native_status_doc,
            status_data,
        )
    )

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
    impedance_ids = _csv_ids(impedance_start_path, "model_id")
    power_width_ids = _csv_ids(power_width_path, "model_id")
    diff_pair_ids = _csv_ids(diff_pair_path, "pair_name")
    rule_query_ids = _csv_ids(rule_query_path, "rule_name")
    room_ids = _csv_ids(rooms_path, "room_id")

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
    if impedance_ids != {"IMP-001", "IMP-002"}:
        errors.append("impedance_model_set")
    if power_width_ids != {"PWR-001", "PWR-002", "PWR-003", "PWR-004"}:
        errors.append("power_width_model_set")
    if diff_pair_ids != {"DP_ETH_TX", "DP_ETH_RX", "DP_CAN"}:
        errors.append("diff_pair_set")
    if len(rule_query_ids) != 10:
        errors.append("rule_query_count")
    if len(room_ids) != 7:
        errors.append("room_count")

    phase_errors, native_schdoc, native_pcbdoc = _phase_coherence(
        root,
        authority,
        status_data,
    )
    errors.extend(phase_errors)

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
    expected_native_status = (
        "NATIVE_EQUIVALENCE_PASS"
        if native_schdoc and native_pcbdoc
        else "PENDING_ALTIUM_IMPORT"
    )
    if native_status != expected_native_status:
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
        "impedance_model_count": len(impedance_ids),
        "power_width_model_count": len(power_width_ids),
        "diff_pair_count": len(diff_pair_ids),
        "rule_query_count": len(rule_query_ids),
        "room_count": len(room_ids),
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
