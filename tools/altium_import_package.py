from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": target.as_posix(),
        "sha256": sha256_file(target),
        "size": target.stat().st_size,
    }


def build(
    *,
    generated_dir: str | Path,
    system_root: str | Path,
    output_dir: str | Path,
    source_commit: str,
) -> dict:
    generated = Path(generated_dir)
    system = Path(system_root)
    output = Path(output_dir)
    repo_root = system.parent.parent

    profile_path = (
        system
        / "altium"
        / "ALTIUM_IMPORT_PROFILE_SYS_001.json"
    )
    authority_path = (
        system
        / "CAD_AUTHORITY_SYS_001.json"
    )

    profile = json.loads(
        profile_path.read_text(encoding="utf-8")
    )
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )

    source = profile["source"]
    required_generated = [
        source["project"],
        source["root_schematic"],
        *source["child_sheets"],
        source["symbol_library"],
        "fp-lib-table",
        "sym-lib-table",
        "footprint_import_staging.json",
    ]

    missing = [
        name
        for name in required_generated
        if not (generated / name).is_file()
    ]
    footprint_dir = (
        generated
        / source["footprint_library"]
    )
    if not footprint_dir.is_dir():
        missing.append(source["footprint_library"])

    if missing:
        raise FileNotFoundError(
            "missing generated Altium import inputs: "
            + ", ".join(sorted(missing))
        )

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    records: list[dict] = []
    source_bindings: list[dict[str, str]] = []

    def register_binding(*, target: Path, source_path: Path) -> None:
        source_bindings.append(
            {
                "package_path": target.relative_to(output).as_posix(),
                "repository_path": source_path.relative_to(repo_root).as_posix(),
            }
        )

    for name in required_generated:
        records.append(
            copy_file(
                generated / name,
                output / "kicad_source" / name,
            )
        )

    footprint_source_root = (
        system
        / "footprints"
        / source["footprint_library"]
    )
    for path in sorted(generated.glob("*.pretty/*.kicad_mod")):
        if not path.is_file():
            continue
        rel = path.relative_to(generated)
        target = output / "kicad_source" / rel
        records.append(copy_file(path, target))
        if path.is_relative_to(footprint_dir):
            footprint_rel = path.relative_to(footprint_dir)
            source_footprint = footprint_source_root / footprint_rel
            if not source_footprint.is_file():
                raise FileNotFoundError(
                    "missing source footprint for import binding: "
                    + source_footprint.as_posix()
                )
            register_binding(target=target, source_path=source_footprint)

    contract_names = [
        "BOM_SYS_CARRIER_003.csv",
        "BOM_SYS_CARRIER_LAYOUT_004.csv",
        "FOOTPRINT_ASSIGNMENT_SYS_002.csv",
        "SYMBOL_PIN_CONTRACT_SYS_001.csv",
        "AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv",
        "PINMAP_SYS_001.csv",
        "CONNECTOR_PINOUT_SYS_001.csv",
        "CONNECTOR_NATIVE_PINMAP_SYS_001.csv",
        "NETLIST_SYS_001.csv",
        "HIERARCHY_INTERFACE_SYS_001.csv",
        "FOOTPRINT_PLAN_SYS_001.csv",
        "PCB_LAYOUT_CONSTRAINTS_SYS_001.csv",
        "CAD_AUTHORITY_SYS_001.json",
    ]

    for name in contract_names:
        source_path = system / name
        target = output / "contracts" / name
        records.append(copy_file(source_path, target))
        register_binding(
            target=target,
            source_path=source_path,
        )

    audit_script_dir = system / "altium" / "scripts"
    active_script_names = [
        "EVT_SYS_CARRIER_ApplyRules.pas",
        "EVT_SYS_CARRIER_Audit.PrjScr",
        "EVT_SYS_CARRIER_Audit.pas",
        "EVT_SYS_CARRIER_Classes.pas",
        "EVT_SYS_CARRIER_ConnectionAudit.PrjScr",
        "EVT_SYS_CARRIER_ConnectionAudit.pas",
        "EVT_SYS_CARRIER_GNDPlane.pas",
        "EVT_SYS_CARRIER_Hierarchy_Audit.pas",
        "EVT_SYS_CARRIER_Mechanical.pas",
        "EVT_SYS_CARRIER_RoutingAudit.PrjScr",
        "EVT_SYS_CARRIER_RoutingAudit.pas",
    ]
    for name in active_script_names:
        script_path = audit_script_dir / name
        if not script_path.is_file():
            raise FileNotFoundError(
                f"missing active Altium script: {script_path.as_posix()}"
            )
        rel = script_path.relative_to(system / "altium")
        target = output / "altium_target" / rel
        records.append(copy_file(script_path, target))
        register_binding(
            target=target,
            source_path=script_path,
        )

    handoff_files = [
        (
            system.parent.parent / "docs" / "ALTIUM_NATIVE_HANDOFF.md",
            output / "handoff" / "ALTIUM_NATIVE_HANDOFF.md",
        ),
        (
            system / "altium" / "equivalence" / "manifest.template.json",
            output / "handoff" / "manifest.template.json",
        ),
        (
            system / "altium" / "equivalence" / "compile_report.template.json",
            output / "handoff" / "compile_report.template.json",
        ),
        (
            system
            / "altium"
            / "equivalence"
            / "script_runtime_receipt.template.json",
            output
            / "handoff"
            / "script_runtime_receipt.template.json",
        ),
    ]
    for source_path, target_path in handoff_files:
        records.append(
            copy_file(
                source_path,
                target_path,
            )
        )

    altium_target_names = [
        "EVT_SYS_CARRIER.PrjPcb",
        "ALTIUM_IMPORT_PROFILE_SYS_001.json",
        "ALTIUM_LAYER_STACK_SYS_001.csv",
        "ALTIUM_RULES_SYS_001.csv",
        "ALTIUM_NET_CLASSES_SYS_001.csv",
        "ALTIUM_PLACEMENT_PLAN_SYS_001.csv",
        "ALTIUM_BOARD_MECHANICAL_SYS_001.csv",
        "ALTIUM_PLACEMENT_COORD_SYS_002.csv",
        "ALTIUM_ROUTING_SEQUENCE_SYS_001.csv",
        "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
        "ALTIUM_EQUIVALENCE_CHECKS_SYS_001.csv",
        "ALTIUM_NATIVE_STATUS_SYS_001.json",
        "ALTIUM_OUTJOB_CONTRACT_SYS_001.csv",
        "ALTIUM_RELEASE_CHECKLIST_SYS_001.csv",
        "ALTIUM_BOARD_PLANNING_SYS_001.csv",
        "ALTIUM_DFM_PROFILE_SYS_001.csv",
        "ALTIUM_EVT_STACKUP_SYS_002.csv",
        "ALTIUM_EVT_ROUTING_STACK_LOCK_SYS_001.json",
        "ALTIUM_IMPEDANCE_START_SYS_001.csv",
        "ALTIUM_POWER_WIDTH_SYS_001.csv",
        "ALTIUM_EVT_POWER_ROUTING_LOCK_SYS_001.json",
        "ALTIUM_DIFF_PAIRS_SYS_001.csv",
        "ALTIUM_RULE_QUERY_SYS_001.csv",
        "ALTIUM_ROOMS_SYS_001.csv",
        "ALTIUM_IMPLEMENTATION_SEQUENCE_SYS_001.csv",
        "ALTIUM_STATUS_SYS_001.json",
        "ALTIUM_SCRIPT_API_COMPAT_SYS_001.json",
        "README.md",
    ]
    for name in altium_target_names:
        source_path = system / "altium" / name
        target = output / "altium_target" / name
        records.append(copy_file(source_path, target))
        if name != "README.md":
            register_binding(
                target=target,
                source_path=source_path,
            )

    generator_sources = [
        repo_root / "tools" / "generate_system_carrier_schematic.py",
        repo_root / "tools" / "generate_system_carrier_symbols.py",
        repo_root / "tools" / "validate_system_carrier_cad_scaffold.py",
        repo_root / "tools" / "kicad_netlist_baseline.py",
        repo_root / ".github" / "workflows" / "hil-r1.yml",
    ]
    for source_path in generator_sources:
        target = (
            output
            / "source_binding"
            / source_path.relative_to(repo_root)
        )
        records.append(copy_file(source_path, target))
        register_binding(
            target=target,
            source_path=source_path,
        )

    evidence_files = [
        "prelayout_validation.json",
        "altium_placement_gate.json",
        "altium_evt_mechanical_datum_gate.json",
        "altium_impedance_gate.json",
        "altium_evt_routing_stack_gate.json",
        "altium_power_width_gate.json",
        "altium_evt_power_routing_gate.json",
        "altium_rule_scope_gate.json",
        "altium_room_gate.json",
        "altium_script_api_compatibility.json",
        "altium_routing_readiness.json",
        "erc.json",
        "erc_triage.json",
        "cad_ci_summary.json",
        "kicad_netlist.xml",
        "kicad_netlist_baseline.csv",
        "kicad_netlist_baseline_result.json",
    ]
    for evidence_name in evidence_files:
        evidence_path = generated / evidence_name
        if not evidence_path.is_file():
            continue
        records.append(
            copy_file(
                evidence_path,
                output / "evidence" / evidence_name,
            )
        )

    package_records: list[dict] = []
    for item in records:
        record = dict(item)
        record["path"] = (
            Path(record["path"])
            .relative_to(output)
            .as_posix()
        )
        package_records.append(record)

    records = sorted(
        package_records,
        key=lambda item: item["path"],
    )

    manifest = {
        "schema": SCHEMA,
        "status": "READY_FOR_ALTIUM_IMPORT",
        "path_mode": "PACKAGE_ROOT_RELATIVE",
        "board_id": authority["board_id"],
        "hardware_revision": authority[
            "hardware_revision"
        ],
        "source_commit": source_commit,
        "source_cad": authority[
            "verification_cad"
        ],
        "target_cad": authority[
            "primary_cad"
        ],
        "preserve_kicad": authority[
            "preserve_kicad"
        ],
        "current_source_binding_required": True,
        "source_binding_count": len(source_bindings),
        "source_bindings": sorted(
            source_bindings,
            key=lambda item: (
                item["repository_path"],
                item["package_path"],
            ),
        ),
        "file_count": len(records),
        "files": records,
        "post_import_checks": profile[
            "post_import_checks"
        ],
        "production_contracts_included": True,
        "placement_gate_included": any(
            item["path"].endswith(
                "evidence/altium_placement_gate.json"
            )
            for item in records
        ),
        "evt_mechanical_datum_gate_included": any(
            item["path"].endswith(
                "evidence/altium_evt_mechanical_datum_gate.json"
            )
            for item in records
        ),
        "impedance_gate_included": any(
            item["path"].endswith(
                "evidence/altium_impedance_gate.json"
            )
            for item in records
        ),
        "evt_routing_stack_gate_included": any(
            item["path"].endswith(
                "evidence/altium_evt_routing_stack_gate.json"
            )
            for item in records
        ),
        "power_width_gate_included": any(
            item["path"].endswith(
                "evidence/altium_power_width_gate.json"
            )
            for item in records
        ),
        "evt_power_routing_gate_included": any(
            item["path"].endswith(
                "evidence/altium_evt_power_routing_gate.json"
            )
            for item in records
        ),
        "rule_scope_gate_included": any(
            item["path"].endswith(
                "evidence/altium_rule_scope_gate.json"
            )
            for item in records
        ),
        "room_gate_included": any(
            item["path"].endswith(
                "evidence/altium_room_gate.json"
            )
            for item in records
        ),
        "routing_readiness_included": any(
            item["path"].endswith(
                "evidence/altium_routing_readiness.json"
            )
            for item in records
        ),
        "script_api_contract_included": any(
            item["path"].endswith(
                "altium_target/ALTIUM_SCRIPT_API_COMPAT_SYS_001.json"
            )
            for item in records
        ),
        "script_api_static_evidence_included": any(
            item["path"].endswith(
                "evidence/altium_script_api_compatibility.json"
            )
            for item in records
        ),
        "script_runtime_validation_required": True,
        "native_audit_script_included": any(
            item["path"].endswith(
                "altium_target/scripts/EVT_SYS_CARRIER_Audit.pas"
            )
            for item in records
        ),
        "native_handoff_runbook_included": any(
            item["path"].endswith(
                "handoff/ALTIUM_NATIVE_HANDOFF.md"
            )
            for item in records
        ),
        "equivalence_manifest_template_included": any(
            item["path"].endswith(
                "handoff/manifest.template.json"
            )
            for item in records
        ),
        "compile_evidence_template_included": any(
            item["path"].endswith(
                "handoff/compile_report.template.json"
            )
            for item in records
        ),
        "script_runtime_receipt_template_included": any(
            item["path"].endswith(
                "handoff/script_runtime_receipt.template.json"
            )
            for item in records
        ),
        "kicad_netlist_baseline_included": any(
            item["path"].endswith(
                "evidence/kicad_netlist_baseline.csv"
            )
            for item in records
        ),
        "notes": [
            (
                "Import kicad_source through Altium Designer "
                "KiCad Importer / Import Wizard."
            ),
            (
                "Do not delete the retained KiCad source after "
                "native Altium conversion."
            ),
            (
                "Native SchDoc/PcbDoc become PCB implementation "
                "authority only after the equivalence gate."
            ),
            (
                "DelphiScript API compatibility is statically checked in CI; "
                "actual exporter execution remains a required Altium Designer "
                "runtime validation."
            ),
        ],
    }

    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    result = build(
        generated_dir=args.generated_dir,
        system_root=args.system_root,
        output_dir=args.output_dir,
        source_commit=args.source_commit,
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
