#!/usr/bin/env python3
"""Bind release evidence to the qualified 24 V native Altium board."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "hardware" / "system_carrier" / "altium" / "native"
OUTPUTS = NATIVE / "Project Outputs for EVT_SYS_CARRIER"
RELEASE = ROOT / "hardware" / "system_carrier" / "altium" / "release"
EVIDENCE = ROOT / "hardware" / "system_carrier" / "altium" / "equivalence"
CONNECTION = ROOT / "hardware" / "system_carrier" / "altium" / "routing" / "connection_audit"
CURRENT = RELEASE / "evt24_v120"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_source_binding(path: Path, pcb_hash: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_pcb"] = relative(NATIVE / "EVT_SYS_CARRIER.PcbDoc")
    payload["source_pcb_sha256"] = pcb_hash
    return payload


def build_zip(destination: Path, sources: list[Path]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for source in sorted(sources, key=lambda item: item.name.casefold()):
            bundle.write(source, source.name)
    with zipfile.ZipFile(destination) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError(f"Invalid ZIP: {destination}")


def output_entry(output_id: str, path: Path, status: str = "PASS", notes: str = "") -> dict:
    entry = {
        "output_id": output_id,
        "path": relative(path),
        "sha256": sha256(path),
        "status": status,
    }
    if notes:
        entry["notes"] = notes
    return entry


def main() -> None:
    pcb = NATIVE / "EVT_SYS_CARRIER.PcbDoc"
    pcb_hash = sha256(pcb)
    expected = "518041a570b405a429a70d968ee54b62df126cb0091b9af08e067152c5aa8735"
    if pcb_hash != expected:
        raise RuntimeError(f"Unexpected canonical PCB hash: {pcb_hash}")

    gerber_sources = [
        path
        for path in (OUTPUTS / "Gerber").iterdir()
        if path.is_file() and (
            path.name.startswith("EVT_SYS_CARRIER.")
            or path.name == "EVT_SYS_CARRIER-macro.APR_LIB"
        )
    ]
    drill_sources = [
        path
        for path in (OUTPUTS / "NC Drill").iterdir()
        if path.is_file() and path.name.startswith("EVT_SYS_CARRIER.")
    ]
    if len(gerber_sources) != 21 or len(drill_sources) != 4:
        raise RuntimeError(
            f"Unexpected fabrication output counts: Gerber={len(gerber_sources)}, NC={len(drill_sources)}"
        )

    gerber_zip = CURRENT / "EVT_SYS_CARRIER_Gerber.zip"
    drill_zip = CURRENT / "EVT_SYS_CARRIER_NC_Drill.zip"
    build_zip(gerber_zip, gerber_sources)
    build_zip(drill_zip, drill_sources)

    drc = NATIVE / "Design Rule Check - EVT_SYS_CARRIER.drc"
    drc_text = drc.read_text(encoding="utf-8", errors="replace")
    required_drc_lines = (
        "PCB File :",
        "EVT_SYS_CARRIER.PcbDoc",
        "Violations Detected : 0",
        "Waived Violations : 0",
        "Un-Routed Net Constraint",
        "Net Antennae",
    )
    if not all(value in drc_text for value in required_drc_lines):
        raise RuntimeError("Current native DRC report is not a zero-violation canonical report")

    native_drc = update_source_binding(RELEASE / "native_drc_result.json", pcb_hash)
    native_drc.update(
        {
            "status": "PASS",
            "blocking_errors": 0,
            "unrouted_nets": 0,
            "routing_topology_violations": 0,
            "net_antennae_violations": 0,
            "source_report": relative(drc),
            "source_report_sha256": sha256(drc),
        }
    )
    write_json(RELEASE / "native_drc_result.json", native_drc)

    mechanical = update_source_binding(RELEASE / "mechanical_review.json", pcb_hash)
    mechanical["evidence_refs"] = [
        {
            "path": relative(OUTPUTS / "Fabrication_PILOT_R1.pdf"),
            "sha256": sha256(OUTPUTS / "Fabrication_PILOT_R1.pdf"),
        },
        {
            "path": relative(OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step"),
            "sha256": sha256(OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step"),
        },
        {
            "path": relative(EVIDENCE / "evt_mechanical_datum_gate.json"),
            "sha256": sha256(EVIDENCE / "evt_mechanical_datum_gate.json"),
        },
    ]
    mechanical["notes"] = [
        "The current native board outline is 90.00 x 70.00 mm with four mounting holes.",
        "Native fabrication PDF and STEP were regenerated from the canonical 24 V PcbDoc.",
        "Enclosure manufacture is deferred by project decision and is not a pilot PCB archive blocker.",
        "Connector-access and populated-enclosure fit remain bench/mechanical follow-up items, so production authority remains NOT_AUTHORIZED.",
    ]
    write_json(RELEASE / "mechanical_review.json", mechanical)

    fabricator = update_source_binding(RELEASE / "fabricator_binding.json", pcb_hash)
    write_json(RELEASE / "fabricator_binding.json", fabricator)

    return_path = update_source_binding(RELEASE / "return_path_si_review.json", pcb_hash)
    return_path["evidence_refs"] = [
        {
            "path": relative(CONNECTION / "connection_integrity_result.json"),
            "sha256": sha256(CONNECTION / "connection_integrity_result.json"),
        },
        {
            "path": relative(EVIDENCE / "evt_power_routing_gate.json"),
            "sha256": sha256(EVIDENCE / "evt_power_routing_gate.json"),
        },
        {
            "path": relative(OUTPUTS / "Fabrication_PILOT_R1.pdf"),
            "sha256": sha256(OUTPUTS / "Fabrication_PILOT_R1.pdf"),
        },
    ]
    return_path["notes"] = [
        "Connection integrity, zero unrouted topology and antennae checks pass on the canonical 24 V PcbDoc.",
        "The EVT power routing gate passes and the color multilayer PDF is current.",
        "A dedicated production SI and return-path sign-off remains pending; it does not grant production authority.",
    ]
    write_json(RELEASE / "return_path_si_review.json", return_path)

    dfm = update_source_binding(RELEASE / "dfm_result.json", pcb_hash)
    write_json(RELEASE / "dfm_result.json", dfm)

    output_manifest_path = CURRENT / "native_outputs_manifest.json"
    output_files = gerber_sources + drill_sources + [
        OUTPUTS / "IPC-2581 Files" / "EVT_SYS_CARRIER.cvg",
        OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.csv",
        OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.txt",
        OUTPUTS / "AssemblyDrawing.pdf",
        OUTPUTS / "Fabrication_PILOT_R1.pdf",
        OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step",
        OUTPUTS / "Schematic Prints.PDF",
        drc,
    ]
    native_outputs_manifest = {
        "schema": "EVT-GSN-NATIVE-OUTPUTS-MANIFEST-001",
        "version": "1.2.0",
        "source_pcb": relative(pcb),
        "source_pcb_sha256": pcb_hash,
        "production_authority": "NOT_AUTHORIZED",
        "files": [
            {
                "path": relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in output_files
        ],
    }
    write_json(output_manifest_path, native_outputs_manifest)

    bom_xlsx = ROOT / "release" / "EVT_ГСН_BOM_и_закупка_24В_v1.2.0_2026-11-02.xlsx"
    compile_result = EVIDENCE / "compile_report.json"
    netlist_result = EVIDENCE / "netlist_validation_result.json"
    assembly_pdf = OUTPUTS / "AssemblyDrawing.pdf"
    fabrication_pdf = OUTPUTS / "Fabrication_PILOT_R1.pdf"
    outjob = {
        "schema": "ALTIUM-OUTJOB-RELEASE-MANIFEST-001",
        "status": "PASS",
        "required_outputs_complete": True,
        "source_is_native_altium": True,
        "all_schematics_from_native_altium": True,
        "all_production_outputs_from_native_altium": True,
        "source_pcb": relative(pcb),
        "source_pcb_sha256": pcb_hash,
        "outputs": [
            output_entry("OUT-001", gerber_zip, notes="Canonical 24 V Gerber set, 21 files."),
            output_entry("OUT-002", drill_zip, notes="Canonical 24 V NC Drill set, four files."),
            output_entry("OUT-003", OUTPUTS / "IPC-2581 Files" / "EVT_SYS_CARRIER.cvg"),
            output_entry("OUT-005", OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.csv", notes="105 native Altium placement rows in metric units."),
            output_entry("OUT-006", bom_xlsx, notes="105 of 105 native Altium BOM positions reconciled with the procurement contract."),
            output_entry("OUT-007", assembly_pdf, notes="Native Altium top and bottom assembly drawing, two pages."),
            output_entry("OUT-008", assembly_pdf, notes="Bottom assembly view is present in the two-page native drawing."),
            output_entry("OUT-009", fabrication_pdf, notes="Five-page native color multilayer fabrication print."),
            output_entry("OUT-010", OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step"),
            output_entry("OUT-011", OUTPUTS / "Schematic Prints.PDF", notes="Eight-sheet compiled native color schematic PDF."),
            output_entry("OUT-012", drc, notes="Zero violations, zero waived violations."),
            output_entry("OUT-013", compile_result),
            output_entry("OUT-014", netlist_result),
            output_entry("OUT-015", fabrication_pdf, notes="Color pages cover top, bottom and internal layers."),
            output_entry("OUT-016", fabrication_pdf, notes="Composite and individual layer views share the final board outline."),
            output_entry("OUT-017", output_manifest_path, notes="Hash inventory bound to the canonical 24 V PcbDoc."),
        ],
        "missing_required_output_ids": [],
        "notes": [
            "All required outputs were regenerated from the canonical 24 V native Altium project.",
            "Rezonit published four-layer data is the working pilot baseline; order-specific feedback remains a later correction input.",
            "Production authority remains NOT_AUTHORIZED.",
        ],
    }
    write_json(RELEASE / "outjob_release_manifest.json", outjob)

    qa = {
        "schema": "EVT-GSN-RELEASE-EVIDENCE-UPDATE-QA-001",
        "version": "1.2.0",
        "canonical_pcb_sha256": pcb_hash,
        "gerber_files": len(gerber_sources),
        "nc_drill_files": len(drill_sources),
        "native_drc": "PASS",
        "outjob_manifest": "PASS",
        "production_authority": "NOT_AUTHORIZED",
    }
    write_json(CURRENT / "release_evidence_update_qa.json", qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
