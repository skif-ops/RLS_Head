from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-HANDOFF-STATUS-001"

REQUIRED = {
    "project": "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb",
    "schematic": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc",
    "pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
    "import_package_manifest": "hardware/system_carrier/altium/equivalence/import_package_manifest.json",
    "import_receipt": "hardware/system_carrier/altium/equivalence/import_receipt.json",
    "import_log": "hardware/system_carrier/altium/equivalence/import_log.txt",
    "compile_report": "hardware/system_carrier/altium/equivalence/compile_report.json",
    "bom_export": "hardware/system_carrier/altium/equivalence/bom_export.csv",
    "netlist_export": "hardware/system_carrier/altium/equivalence/netlist_export.csv",
    "footprint_report": "hardware/system_carrier/altium/equivalence/footprint_report.json",
    "component_inventory": "hardware/system_carrier/altium/equivalence/component_inventory.csv",
    "net_inventory": "hardware/system_carrier/altium/equivalence/net_inventory.csv",
    "rule_inventory": "hardware/system_carrier/altium/equivalence/rule_inventory.csv",
    "native_audit_result": "hardware/system_carrier/altium/equivalence/native_audit_result.json",
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
    audit_ready = (
        evidence["component_inventory"]["present"]
        and evidence["net_inventory"]["present"]
        and evidence["rule_inventory"]["present"]
        and evidence["native_audit_result"]["present"]
    )
    equivalence_ready = (
        not missing
    )

    if not native_ready:
        status = "WAITING_NATIVE_IMPORT"
        next_action = "CREATE_AND_SAVE_NATIVE_SCHDOC_PCBDOC_IN_ALTIUM"
    elif not audit_ready:
        status = "WAITING_NATIVE_AUDIT"
        next_action = "RUN_EVT_SYS_CARRIER_AUDIT_IN_ALTIUM"
    elif not equivalence_ready:
        status = "WAITING_EQUIVALENCE_EVIDENCE"
        next_action = "COMPLETE_COMPILE_BOM_NETLIST_FOOTPRINT_AND_MANIFEST_EVIDENCE"
    else:
        status = "READY_TO_RUN_EQUIVALENCE_GATE"
        next_action = "RUN_ALTIUM_EQUIVALENCE_GATE"

    return {
        "schema": SCHEMA,
        "status": status,
        "next_action": next_action,
        "native_files_ready": native_ready,
        "native_audit_ready": audit_ready,
        "equivalence_evidence_complete": equivalence_ready,
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
