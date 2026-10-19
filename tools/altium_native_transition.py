from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_compile_evidence import validate as validate_compile_evidence
from tools.altium_equivalence_gate import validate_manifest as validate_gate
from tools.altium_equivalence_manifest import build_manifest
from tools.altium_native_audit_validate import validate as validate_audit
from tools.altium_native_bom_validate import validate as validate_bom
from tools.altium_native_connector_validate import validate as validate_connector
from tools.altium_native_footprint_validate import validate as validate_footprint
from tools.altium_native_file_preflight import validate as validate_native_files
from tools.altium_native_handoff_status import evaluate as evaluate_handoff
from tools.altium_native_ci_gate import evaluate as evaluate_native_ci
from tools.altium_native_hierarchy_validate import validate as validate_hierarchy
from tools.altium_native_import_receipt import build_receipt
from tools.altium_native_netlist_validate import validate as validate_netlist
from tools.altium_no_mmwave_review_validate import validate as validate_no_mmwave


SCHEMA = "ALTIUM-NATIVE-TRANSITION-001"

SYSTEM_REL = Path("hardware/system_carrier")
ALTIUM_REL = SYSTEM_REL / "altium"
NATIVE_REL = ALTIUM_REL / "native"
EQUIV_REL = ALTIUM_REL / "equivalence"

PATHS = {
    "project": ALTIUM_REL / "EVT_SYS_CARRIER.PrjPcb",
    "schematic": NATIVE_REL / "EVT_SYS_CARRIER.SchDoc",
    "pcb": NATIVE_REL / "EVT_SYS_CARRIER.PcbDoc",
    "native_file_preflight": EQUIV_REL / "native_file_preflight.json",
    "package_manifest": EQUIV_REL / "import_package_manifest.json",
    "import_log": EQUIV_REL / "import_log.txt",
    "import_receipt": EQUIV_REL / "import_receipt.json",
    "compile_report_raw": EQUIV_REL / "compile_report_raw.txt",
    "compile_report": EQUIV_REL / "compile_report.json",
    "bom_export": EQUIV_REL / "bom_export.csv",
    "bom_result": EQUIV_REL / "bom_validation_result.json",
    "component_inventory": EQUIV_REL / "component_inventory.csv",
    "net_inventory": EQUIV_REL / "net_inventory.csv",
    "rule_inventory": EQUIV_REL / "rule_inventory.csv",
    "pad_net_inventory": EQUIV_REL / "pad_net_inventory.csv",
    "layer_stack_inventory": EQUIV_REL / "layer_stack_inventory.csv",
    "native_audit_result": EQUIV_REL / "native_audit_result.json",
    "footprint_result": EQUIV_REL / "footprint_report.json",
    "connector_result": EQUIV_REL / "connector_validation_result.json",
    "kicad_netlist_baseline": EQUIV_REL / "kicad_netlist_baseline.csv",
    "netlist_export": EQUIV_REL / "netlist_export.csv",
    "netlist_result": EQUIV_REL / "netlist_validation_result.json",
    "hierarchy_export": EQUIV_REL / "hierarchy_export.csv",
    "hierarchy_result": EQUIV_REL / "hierarchy_validation_result.json",
    "no_mmwave_review": EQUIV_REL / "no_mmwave_review.json",
    "no_mmwave_result": EQUIV_REL / "no_mmwave_review_result.json",
    "manifest_template": EQUIV_REL / "manifest.template.json",
    "manifest": EQUIV_REL / "manifest.json",
    "handoff_status": EQUIV_REL / "native_handoff_status.json",
    "gate_result": EQUIV_REL / "altium_equivalence_result.json",
    "native_status": ALTIUM_REL / "ALTIUM_NATIVE_STATUS_SYS_001.json",
    "implementation_status": ALTIUM_REL / "ALTIUM_STATUS_SYS_001.json",
    "cad_authority": SYSTEM_REL / "CAD_AUTHORITY_SYS_001.json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _absolute(root: Path, key: str) -> Path:
    return root / PATHS[key]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _missing(root: Path, keys: tuple[str, ...]) -> list[str]:
    return [
        key
        for key in keys
        if not _absolute(root, key).is_file()
    ]


def _result(
    *,
    status: str,
    next_action: str,
    generated: list[str],
    stage_results: dict[str, dict],
    missing: list[str] | None = None,
    errors: list[str] | None = None,
    routing_authorized: bool = False,
    production_authorized: bool = False,
) -> dict:
    return {
        "schema": SCHEMA,
        "status": status,
        "next_action": next_action,
        "routing_authorized": routing_authorized,
        "production_authorized": production_authorized,
        "generated_artifacts": generated,
        "stage_results": stage_results,
        "missing_inputs": sorted(missing or []),
        "errors": sorted(set(errors or [])),
        "notes": [
            (
                "This orchestrator never creates or fabricates native Altium "
                "SchDoc/PcbDoc files; those must come from Altium Designer."
            ),
            (
                "Human no-mmWave review remains mandatory and is never "
                "auto-approved."
            ),
            (
                "Production authority remains separate and is controlled by "
                "ALTIUM_PRODUCTION_RELEASE_GATE."
            ),
        ],
    }


def _sync_layout_authority_status(
    root: Path,
    gate_result: dict,
) -> None:
    if (
        gate_result.get("status") != "PASS"
        or gate_result.get("layout_authority") != "AUTHORIZED"
    ):
        raise ValueError("cannot synchronize status without equivalence PASS")

    native_status_path = _absolute(root, "native_status")
    implementation_status_path = _absolute(root, "implementation_status")

    authority_path = _absolute(root, "cad_authority")

    native_status = _read_json(native_status_path)
    implementation_status = _read_json(implementation_status_path)
    authority = _read_json(authority_path)

    native_status["native_import_status"] = "NATIVE_FILES_READY"
    native_status["equivalence_gate_status"] = "PASS"
    native_status["layout_authority"] = "AUTHORIZED"
    native_status["production_authority"] = "NOT_AUTHORIZED"
    native_status["next_required_outputs"] = []
    native_status["equivalence_result"] = (
        PATHS["gate_result"].as_posix()
    )
    native_status["equivalence_result_sha256"] = _sha256_file(
        _absolute(root, "gate_result")
    )
    native_status["native_schematic_sha256"] = _sha256_file(
        _absolute(root, "schematic")
    )
    native_status["native_pcb_sha256"] = _sha256_file(
        _absolute(root, "pcb")
    )

    altium = implementation_status.setdefault("altium", {})
    altium["native_schdoc"] = True
    altium["native_pcbdoc"] = True
    altium["equivalence_gate"] = True
    altium["placement_started"] = False
    altium["routing_started"] = False
    altium["production_release_authorized"] = False
    altium["native_pcb_sha256"] = native_status["native_pcb_sha256"]

    implementation_status["current_phase"] = "READY_FOR_ROUTING"
    implementation_status["next_required_phase"] = (
        "NATIVE_ALTIUM_PLACEMENT_AND_ROUTING"
    )

    blockers = implementation_status.get("blockers")
    if isinstance(blockers, list):
        implementation_status["blockers"] = [
            item
            for item in blockers
            if "Native Altium import/save" not in str(item)
        ]

    routing = implementation_status.setdefault(
        "routing_readiness",
        {},
    )
    routing["expected_status"] = "READY_FOR_ROUTING"
    routing["routing_authorized"] = True
    routing["required_to_authorize"] = []

    authority["native_document_status"] = "NATIVE_EQUIVALENCE_PASS"
    authority["pcb_layout_authority"] = "ALTIUM_AUTHORIZED"
    authority["pcb_design_phase"] = "ALTIUM_NATIVE_ROUTING"
    authority["production_release_authorized"] = False
    authority["native_schematic_sha256"] = (
        native_status["native_schematic_sha256"]
    )
    authority["native_pcb_sha256"] = native_status["native_pcb_sha256"]
    authority["equivalence_result_sha256"] = (
        native_status["equivalence_result_sha256"]
    )
    routing_gate = authority.setdefault("routing_readiness_gate", {})
    routing_gate["current_expected_status"] = "READY_FOR_ROUTING"
    rule_contract = authority.setdefault("altium_rule_query_contract", {})
    rule_contract["status"] = "NATIVE_EQUIVALENCE_PASS"

    _write_json(native_status_path, native_status)
    _write_json(implementation_status_path, implementation_status)
    _write_json(authority_path, authority)


def run_transition(
    *,
    repository_root: str | Path = ".",
    altium_version: str = "",
    importer_version: str = "",
    synchronize_status: bool = True,
    force_recheck: bool = False,
) -> dict:
    root = Path(repository_root)
    system = root / SYSTEM_REL
    eq = root / EQUIV_REL
    generated: list[str] = []
    stage_results: dict[str, dict] = {}

    missing_native = _missing(
        root,
        ("project", "schematic", "pcb"),
    )
    if missing_native:
        return _result(
            status="WAITING_NATIVE_IMPORT",
            next_action="CREATE_AND_SAVE_NATIVE_SCHDOC_PCBDOC_IN_ALTIUM",
            generated=generated,
            stage_results=stage_results,
            missing=missing_native,
        )

    native_file_preflight = validate_native_files(
        schematic=_absolute(root, "schematic"),
        pcb=_absolute(root, "pcb"),
    )
    artifacts = native_file_preflight.get("artifacts")
    if isinstance(artifacts, dict):
        if isinstance(artifacts.get("schematic"), dict):
            artifacts["schematic"]["path"] = PATHS["schematic"].as_posix()
        if isinstance(artifacts.get("pcb"), dict):
            artifacts["pcb"]["path"] = PATHS["pcb"].as_posix()

    stage_results["current_native_file_preflight"] = native_file_preflight
    if native_file_preflight.get("status") != "PASS":
        return _result(
            status="BLOCKED_NATIVE_FILE_PREFLIGHT",
            next_action="RECREATE_NATIVE_ALTIUM_DOCUMENTS",
            generated=generated,
            stage_results=stage_results,
            errors=native_file_preflight.get("errors", []),
        )

    if not force_recheck:
        existing_lifecycle = evaluate_native_ci(
            repository_root=root,
        )
        stage_results["existing_lifecycle"] = existing_lifecycle
        if (
            existing_lifecycle.get("status") == "PASS"
            and existing_lifecycle.get("phase") == "POST_EQUIVALENCE"
        ):
            return _result(
                status="READY_FOR_ROUTING",
                next_action="CONTINUE_NATIVE_ALTIUM_PLACEMENT_AND_ROUTING",
                generated=generated,
                stage_results=stage_results,
                routing_authorized=True,
            )
        if (
            existing_lifecycle.get("status") == "PASS"
            and existing_lifecycle.get("phase") == "POST_PRODUCTION"
        ):
            return _result(
                status="PRODUCTION_RELEASED",
                next_action="PRODUCTION_ALREADY_RELEASED",
                generated=generated,
                stage_results=stage_results,
                routing_authorized=True,
                production_authorized=True,
            )

    # From this point onward a real equivalence/re-equivalence is intended.
    # Only now may transition-owned equivalence evidence be regenerated.
    _write_json(
        _absolute(root, "native_file_preflight"),
        native_file_preflight,
    )
    generated.append(PATHS["native_file_preflight"].as_posix())
    stage_results["native_file_preflight"] = native_file_preflight

    missing_provenance = _missing(
        root,
        ("package_manifest", "import_log"),
    )
    if missing_provenance:
        return _result(
            status="WAITING_IMPORT_PROVENANCE",
            next_action="COPY_IMPORT_PACKAGE_MANIFEST_AND_IMPORT_LOG",
            generated=generated,
            stage_results=stage_results,
            missing=missing_provenance,
        )

    receipt_path = _absolute(root, "import_receipt")
    if not receipt_path.is_file():
        if not altium_version.strip() or not importer_version.strip():
            return _result(
                status="WAITING_IMPORT_RECEIPT_METADATA",
                next_action="SUPPLY_ALTIUM_AND_IMPORTER_VERSIONS",
                generated=generated,
                stage_results=stage_results,
                missing=[
                    name
                    for name, value in (
                        ("altium_version", altium_version),
                        ("importer_version", importer_version),
                    )
                    if not value.strip()
                ],
            )

        receipt = build_receipt(
            repository_root=root,
            package_manifest=_absolute(root, "package_manifest"),
            altium_version=altium_version,
            importer_version=importer_version,
        )
        _write_json(receipt_path, receipt)
        generated.append(PATHS["import_receipt"].as_posix())
        stage_results["import_receipt"] = receipt
        if receipt.get("status") != "PASS":
            return _result(
                status="BLOCKED_IMPORT_RECEIPT",
                next_action="FIX_IMPORT_PROVENANCE",
                generated=generated,
                stage_results=stage_results,
                errors=receipt.get("errors", []),
            )
    else:
        try:
            receipt = _read_json(receipt_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return _result(
                status="BLOCKED_IMPORT_RECEIPT",
                next_action="FIX_IMPORT_PROVENANCE",
                generated=generated,
                stage_results=stage_results,
                errors=[f"import_receipt_parse:{exc}"],
            )
        stage_results["import_receipt"] = receipt
        if receipt.get("status") != "PASS":
            return _result(
                status="BLOCKED_IMPORT_RECEIPT",
                next_action="FIX_IMPORT_PROVENANCE",
                generated=generated,
                stage_results=stage_results,
                errors=receipt.get("errors", ["import_receipt_not_pass"]),
            )

    missing_compile = _missing(
        root,
        ("compile_report_raw", "compile_report"),
    )
    if missing_compile:
        return _result(
            status="WAITING_COMPILE_REPORT",
            next_action="EXPORT_AND_BIND_ZERO_ERROR_ZERO_WARNING_ALTIUM_COMPILE_REPORT",
            generated=generated,
            stage_results=stage_results,
            missing=missing_compile,
        )

    compile_validation = validate_compile_evidence(
        compile_report=_absolute(root, "compile_report"),
        repository_root=root,
    )
    stage_results["compile_evidence"] = compile_validation
    if compile_validation.get("status") != "PASS":
        return _result(
            status="BLOCKED_COMPILE_REPORT",
            next_action="FIX_NATIVE_ALTIUM_COMPILE_OR_EVIDENCE_BINDING",
            generated=generated,
            stage_results=stage_results,
            errors=(
                list(compile_validation.get("errors", []))
                + list(compile_validation.get("reason_codes", []))
            ),
        )

    raw_audit_keys = (
        "component_inventory",
        "net_inventory",
        "rule_inventory",
        "pad_net_inventory",
        "layer_stack_inventory",
    )
    missing_audit = _missing(root, raw_audit_keys)
    if missing_audit:
        return _result(
            status="WAITING_NATIVE_AUDIT_EXPORT",
            next_action="RUN_EXPORT_NATIVE_AUDIT_IN_ALTIUM",
            generated=generated,
            stage_results=stage_results,
            missing=missing_audit,
        )

    audit = validate_audit(
        system_root=system,
        audit_dir=eq,
    )
    _write_json(_absolute(root, "native_audit_result"), audit)
    generated.append(PATHS["native_audit_result"].as_posix())
    stage_results["native_audit"] = audit
    if audit.get("status") != "PASS":
        return _result(
            status="BLOCKED_NATIVE_AUDIT",
            next_action="FIX_NATIVE_PCB_AUDIT_FINDINGS",
            generated=generated,
            stage_results=stage_results,
            errors=audit.get("errors", []),
        )

    if not _absolute(root, "bom_export").is_file():
        return _result(
            status="WAITING_BOM_EXPORT",
            next_action="EXPORT_NATIVE_ALTIUM_BOM",
            generated=generated,
            stage_results=stage_results,
            missing=["bom_export"],
        )

    bom = validate_bom(
        system_root=system,
        bom_export=_absolute(root, "bom_export"),
    )
    _write_json(_absolute(root, "bom_result"), bom)
    generated.append(PATHS["bom_result"].as_posix())
    stage_results["bom"] = bom
    if bom.get("status") != "PASS":
        return _result(
            status="BLOCKED_BOM_EQUIVALENCE",
            next_action="FIX_NATIVE_BOM_EQUIVALENCE",
            generated=generated,
            stage_results=stage_results,
            errors=bom.get("errors", []),
        )

    footprint = validate_footprint(
        system_root=system,
        component_inventory=_absolute(
            root,
            "component_inventory",
        ),
    )
    _write_json(_absolute(root, "footprint_result"), footprint)
    generated.append(PATHS["footprint_result"].as_posix())
    stage_results["footprint"] = footprint
    if footprint.get("status") != "PASS":
        return _result(
            status="BLOCKED_FOOTPRINT_EQUIVALENCE",
            next_action="FIX_NATIVE_FOOTPRINT_EQUIVALENCE",
            generated=generated,
            stage_results=stage_results,
            errors=footprint.get("errors", []),
        )

    connector = validate_connector(
        system_root=system,
        pad_net_inventory=_absolute(root, "pad_net_inventory"),
    )
    _write_json(_absolute(root, "connector_result"), connector)
    generated.append(PATHS["connector_result"].as_posix())
    stage_results["connector"] = connector
    if connector.get("status") != "PASS":
        return _result(
            status="BLOCKED_CONNECTOR_EQUIVALENCE",
            next_action="FIX_NATIVE_CONNECTOR_EQUIVALENCE",
            generated=generated,
            stage_results=stage_results,
            errors=connector.get("errors", []),
        )

    if not _absolute(root, "kicad_netlist_baseline").is_file():
        return _result(
            status="WAITING_KICAD_NETLIST_BASELINE",
            next_action="COPY_CI_KICAD_NETLIST_BASELINE",
            generated=generated,
            stage_results=stage_results,
            missing=["kicad_netlist_baseline"],
        )

    if not _absolute(root, "netlist_export").is_file():
        return _result(
            status="WAITING_NETLIST_EXPORT",
            next_action="EXPORT_NATIVE_ALTIUM_NETLIST_FOR_ARCHIVE",
            generated=generated,
            stage_results=stage_results,
            missing=["netlist_export"],
        )

    netlist = validate_netlist(
        baseline_csv=_absolute(root, "kicad_netlist_baseline"),
        pad_net_inventory=_absolute(root, "pad_net_inventory"),
    )
    _write_json(_absolute(root, "netlist_result"), netlist)
    generated.append(PATHS["netlist_result"].as_posix())
    stage_results["netlist"] = netlist
    if netlist.get("status") != "PASS":
        return _result(
            status="BLOCKED_NETLIST_EQUIVALENCE",
            next_action="FIX_NATIVE_CONNECTIVITY_EQUIVALENCE",
            generated=generated,
            stage_results=stage_results,
            errors=netlist.get("errors", []),
        )

    if not _absolute(root, "hierarchy_export").is_file():
        return _result(
            status="WAITING_HIERARCHY_EXPORT",
            next_action="RUN_EXPORT_NATIVE_HIERARCHY_IN_ALTIUM",
            generated=generated,
            stage_results=stage_results,
            missing=["hierarchy_export"],
        )

    hierarchy = validate_hierarchy(
        system_root=system,
        hierarchy_export=_absolute(root, "hierarchy_export"),
        pad_net_inventory=_absolute(root, "pad_net_inventory"),
    )
    _write_json(_absolute(root, "hierarchy_result"), hierarchy)
    generated.append(PATHS["hierarchy_result"].as_posix())
    stage_results["hierarchy"] = hierarchy
    if hierarchy.get("status") != "PASS":
        return _result(
            status="BLOCKED_HIERARCHY_EQUIVALENCE",
            next_action="FIX_NATIVE_HIERARCHY_EQUIVALENCE",
            generated=generated,
            stage_results=stage_results,
            errors=hierarchy.get("errors", []),
        )

    if not _absolute(root, "no_mmwave_review").is_file():
        return _result(
            status="WAITING_NO_MMWAVE_REVIEW",
            next_action="COMPLETE_HUMAN_NO_MMWAVE_REVIEW",
            generated=generated,
            stage_results=stage_results,
            missing=["no_mmwave_review"],
        )

    no_mmwave = validate_no_mmwave(
        review_json=_absolute(root, "no_mmwave_review"),
        pcb_path=_absolute(root, "pcb"),
        component_inventory=_absolute(root, "component_inventory"),
        net_inventory=_absolute(root, "net_inventory"),
    )
    _write_json(_absolute(root, "no_mmwave_result"), no_mmwave)
    generated.append(PATHS["no_mmwave_result"].as_posix())
    stage_results["no_mmwave"] = no_mmwave
    if no_mmwave.get("status") != "PASS":
        return _result(
            status="BLOCKED_NO_MMWAVE_REVIEW",
            next_action="FIX_OR_COMPLETE_NO_MMWAVE_REVIEW",
            generated=generated,
            stage_results=stage_results,
            errors=(
                list(no_mmwave.get("errors", []))
                + list(no_mmwave.get("reason_codes", []))
            ),
        )

    manifest_build = build_manifest(
        template_path=_absolute(root, "manifest_template"),
        repository_root=root,
    )
    stage_results["manifest_builder"] = manifest_build
    if manifest_build.get("status") != "READY":
        return _result(
            status="BLOCKED_EQUIVALENCE_MANIFEST",
            next_action="COMPLETE_EQUIVALENCE_EVIDENCE",
            generated=generated,
            stage_results=stage_results,
            errors=manifest_build.get("errors", []),
        )

    _write_json(
        _absolute(root, "manifest"),
        manifest_build["manifest"],
    )
    generated.append(PATHS["manifest"].as_posix())

    handoff = evaluate_handoff(root)
    _write_json(_absolute(root, "handoff_status"), handoff)
    generated.append(PATHS["handoff_status"].as_posix())
    stage_results["handoff"] = handoff
    if handoff.get("status") != "READY_TO_RUN_EQUIVALENCE_GATE":
        return _result(
            status=handoff.get(
                "status",
                "BLOCKED_EQUIVALENCE_HANDOFF",
            ),
            next_action=handoff.get(
                "next_action",
                "FIX_EQUIVALENCE_HANDOFF",
            ),
            generated=generated,
            stage_results=stage_results,
            missing=handoff.get("missing_artifacts", []),
            errors=(
                list(handoff.get("manifest_errors", []))
                + list(handoff.get("pending_equivalence_checks", []))
            ),
        )

    gate = validate_gate(
        _absolute(root, "manifest"),
        repository_root=root,
    )
    _write_json(_absolute(root, "gate_result"), gate)
    generated.append(PATHS["gate_result"].as_posix())
    stage_results["equivalence_gate"] = gate

    if gate.get("status") != "PASS":
        return _result(
            status="BLOCKED_EQUIVALENCE_GATE",
            next_action="FIX_EQUIVALENCE_GATE_FINDINGS",
            generated=generated,
            stage_results=stage_results,
            errors=(
                list(gate.get("errors", []))
                + list(gate.get("reason_codes", []))
            ),
        )

    if synchronize_status:
        try:
            _sync_layout_authority_status(root, gate)
        except (
            FileNotFoundError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            return _result(
                status="PASS_STATUS_SYNC_FAILED",
                next_action="FIX_TRACKED_ALTIUM_STATUS_SYNC",
                generated=generated,
                stage_results=stage_results,
                errors=[f"status_sync:{exc}"],
                routing_authorized=True,
            )
        generated.extend(
            [
                PATHS["native_status"].as_posix(),
                PATHS["implementation_status"].as_posix(),
                PATHS["cad_authority"].as_posix(),
            ]
        )

    return _result(
        status="READY_FOR_ROUTING",
        next_action="BEGIN_NATIVE_ALTIUM_PLACEMENT_AND_ROUTING",
        generated=generated,
        stage_results=stage_results,
        routing_authorized=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--altium-version", default="")
    parser.add_argument("--importer-version", default="")
    parser.add_argument(
        "--no-status-sync",
        action="store_true",
        help="Do not update tracked Altium status JSON after equivalence PASS.",
    )
    parser.add_argument(
        "--force-recheck",
        action="store_true",
        help=(
            "Force a full equivalence/re-equivalence pass even when the "
            "current tracked native lifecycle is already valid."
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "hardware/system_carrier/altium/equivalence/"
            "native_transition_result.json"
        ),
    )
    args = parser.parse_args()

    result = run_transition(
        repository_root=args.repository_root,
        altium_version=args.altium_version,
        importer_version=args.importer_version,
        synchronize_status=not args.no_status_sync,
        force_recheck=args.force_recheck,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(args.repository_root) / output
    _write_json(output, result)

    print(result["status"])
    return (
        0
        if result["status"] in {"READY_FOR_ROUTING", "PRODUCTION_RELEASED"}
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
