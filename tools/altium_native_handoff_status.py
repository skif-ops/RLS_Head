from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_gate import REQUIRED_CHECKS


SCHEMA = "ALTIUM-NATIVE-HANDOFF-STATUS-001"

REQUIRED = {
    "project": "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb",
    "schematic": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc",
    "pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
    "native_file_preflight": "hardware/system_carrier/altium/equivalence/native_file_preflight.json",
    "import_native_file_preflight": "hardware/system_carrier/altium/equivalence/import_native_file_preflight.json",
    "import_package_manifest": "hardware/system_carrier/altium/equivalence/import_package_manifest.json",
    "import_receipt": "hardware/system_carrier/altium/equivalence/import_receipt.json",
    "import_log": "hardware/system_carrier/altium/equivalence/import_log.txt",
    "compile_report_raw": "hardware/system_carrier/altium/equivalence/compile_report_raw.txt",
    "compile_report": "hardware/system_carrier/altium/equivalence/compile_report.json",
    "bom_export": "hardware/system_carrier/altium/equivalence/bom_export.csv",
    "bom_validation_result": "hardware/system_carrier/altium/equivalence/bom_validation_result.json",
    "connector_validation_result": "hardware/system_carrier/altium/equivalence/connector_validation_result.json",
    "kicad_netlist_baseline": "hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv",
    "netlist_validation_result": "hardware/system_carrier/altium/equivalence/netlist_validation_result.json",
    "netlist_export": "hardware/system_carrier/altium/equivalence/netlist_export.csv",
    "footprint_report": "hardware/system_carrier/altium/equivalence/footprint_report.json",
    "component_inventory": "hardware/system_carrier/altium/equivalence/component_inventory.csv",
    "net_inventory": "hardware/system_carrier/altium/equivalence/net_inventory.csv",
    "rule_inventory": "hardware/system_carrier/altium/equivalence/rule_inventory.csv",
    "pad_net_inventory": "hardware/system_carrier/altium/equivalence/pad_net_inventory.csv",
    "layer_stack_inventory": "hardware/system_carrier/altium/equivalence/layer_stack_inventory.csv",
    "native_audit_result": "hardware/system_carrier/altium/equivalence/native_audit_result.json",
    "hierarchy_export": "hardware/system_carrier/altium/equivalence/hierarchy_export.csv",
    "hierarchy_validation_result": "hardware/system_carrier/altium/equivalence/hierarchy_validation_result.json",
    "script_runtime_receipt": "hardware/system_carrier/altium/equivalence/script_runtime_receipt.json",
    "script_runtime_result": "hardware/system_carrier/altium/equivalence/script_runtime_result.json",
    "no_mmwave_review": "hardware/system_carrier/altium/equivalence/no_mmwave_review.json",
    "no_mmwave_review_result": "hardware/system_carrier/altium/equivalence/no_mmwave_review_result.json",
    "manifest": "hardware/system_carrier/altium/equivalence/manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(repository_root: str | Path = ".") -> dict:
    root = Path(repository_root)
    evidence: dict[str, dict] = {}
    missing: list[str] = []

    for artifact_id, relative in REQUIRED.items():
        path = root / relative
        present = path.is_file()
        item = {
            "path": relative,
            "present": present,
        }
        if present:
            item["size"] = path.stat().st_size
            item["sha256"] = sha256_file(path)
        else:
            missing.append(artifact_id)
        evidence[artifact_id] = item

    native_ready = (
        evidence["schematic"]["present"]
        and evidence["pcb"]["present"]
    )
    native_file_preflight_ready = (
        evidence["native_file_preflight"]["present"]
    )
    provenance_ready = (
        evidence["import_native_file_preflight"]["present"]
        and evidence["import_package_manifest"]["present"]
        and evidence["import_receipt"]["present"]
        and evidence["import_log"]["present"]
    )
    audit_ready = (
        evidence["component_inventory"]["present"]
        and evidence["net_inventory"]["present"]
        and evidence["rule_inventory"]["present"]
        and evidence["pad_net_inventory"]["present"]
        and evidence["layer_stack_inventory"]["present"]
        and evidence["native_audit_result"]["present"]
    )
    hierarchy_export_ready = evidence[
        "hierarchy_export"
    ]["present"]
    script_runtime_receipt_ready = evidence[
        "script_runtime_receipt"
    ]["present"]
    script_runtime_result_ready = evidence[
        "script_runtime_result"
    ]["present"]
    script_runtime_ready = (
        script_runtime_receipt_ready
        and script_runtime_result_ready
    )
    equivalence_ready = (
        not missing
    )

    manifest_errors: list[str] = []
    manifest_checks: dict[str, str] = {}
    pending_checks: list[str] = sorted(REQUIRED_CHECKS)
    semantic_checks_ready = False

    manifest_path = root / REQUIRED["manifest"]
    if manifest_path.is_file():
        try:
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            manifest_errors.append(f"manifest_parse:{exc}")
        else:
            checks_raw = manifest.get("checks")
            if not isinstance(checks_raw, dict):
                manifest_errors.append("manifest_checks")
            else:
                manifest_checks = {
                    name: str(
                        checks_raw.get(name, "MISSING")
                    ).strip()
                    for name in sorted(REQUIRED_CHECKS)
                }
                pending_checks = [
                    name
                    for name, value in manifest_checks.items()
                    if value != "PASS"
                ]
                semantic_checks_ready = not pending_checks

    if not native_ready:
        status = "WAITING_NATIVE_IMPORT"
        next_action = "CREATE_AND_SAVE_NATIVE_SCHDOC_PCBDOC_IN_ALTIUM"
    elif not native_file_preflight_ready:
        status = "WAITING_NATIVE_FILE_PREFLIGHT"
        next_action = "RUN_NATIVE_ALTIUM_FILE_PREFLIGHT"
    elif not provenance_ready:
        status = "WAITING_IMPORT_PROVENANCE"
        next_action = "CAPTURE_IMPORT_PACKAGE_LOG_AND_RECEIPT"
    elif not audit_ready:
        status = "WAITING_NATIVE_AUDIT"
        next_action = "RUN_EVT_SYS_CARRIER_AUDIT_IN_ALTIUM"
    elif not hierarchy_export_ready:
        status = "WAITING_HIERARCHY_EXPORT"
        next_action = "RUN_EXPORT_NATIVE_HIERARCHY_IN_ALTIUM"
    elif not script_runtime_receipt_ready:
        status = "WAITING_SCRIPT_RUNTIME_RECEIPT"
        next_action = "RECORD_ALTIUM_SCRIPT_RUNTIME_RECEIPT"
    elif not script_runtime_result_ready:
        status = "WAITING_SCRIPT_RUNTIME_VALIDATION"
        next_action = "VALIDATE_ALTIUM_SCRIPT_RUNTIME_RECEIPT"
    elif not equivalence_ready:
        status = "WAITING_EQUIVALENCE_EVIDENCE"
        next_action = "COMPLETE_COMPILE_BOM_NETLIST_FOOTPRINT_AND_MANIFEST_EVIDENCE"
    elif manifest_errors:
        status = "INVALID_EQUIVALENCE_MANIFEST"
        next_action = "FIX_EQUIVALENCE_MANIFEST"
    elif not semantic_checks_ready:
        status = "WAITING_EQUIVALENCE_CHECKS"
        next_action = "COMPLETE_REMAINING_EQUIVALENCE_CHECKS"
    else:
        status = "READY_TO_RUN_EQUIVALENCE_GATE"
        next_action = "RUN_ALTIUM_EQUIVALENCE_GATE"

    return {
        "schema": SCHEMA,
        "status": status,
        "next_action": next_action,
        "native_files_ready": native_ready,
        "native_file_preflight_ready": native_file_preflight_ready,
        "import_provenance_ready": provenance_ready,
        "native_audit_ready": audit_ready,
        "hierarchy_export_ready": hierarchy_export_ready,
        "script_runtime_receipt_ready": (
            script_runtime_receipt_ready
        ),
        "script_runtime_result_ready": (
            script_runtime_result_ready
        ),
        "script_runtime_ready": script_runtime_ready,
        "equivalence_evidence_complete": equivalence_ready,
        "semantic_checks_ready": semantic_checks_ready,
        "pending_equivalence_checks": pending_checks,
        "manifest_checks": manifest_checks,
        "manifest_errors": sorted(manifest_errors),
        "missing_artifacts": sorted(missing),
        "evidence": evidence,
        "routing_authorized": False,
        "production_authorized": False,
        "notes": [
            "This status tool never grants layout or production authority.",
            "Layout authority is granted only by ALTIUM_EQUIVALENCE_GATE PASS.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(args.repository_root)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
