import json
from pathlib import Path

import tools.altium_native_transition as transition
from tools.altium_native_file_preflight import CFB_MAGIC


def _write(path: Path, content: bytes = b"TEST") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _cfb_stub() -> bytes:
    data = bytearray(512)
    data[:8] = CFB_MAGIC
    data[24:26] = (0x003E).to_bytes(2, "little")
    data[26:28] = (3).to_bytes(2, "little")
    data[28:30] = (0xFFFE).to_bytes(2, "little")
    data[30:32] = (9).to_bytes(2, "little")
    data[32:34] = (6).to_bytes(2, "little")
    return bytes(data)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _path(root: Path, key: str) -> Path:
    return root / transition.PATHS[key]


def test_native_transition_waits_for_real_altium_import(tmp_path):
    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "WAITING_NATIVE_IMPORT"
    assert set(result["missing_inputs"]) == {
        "project",
        "schematic",
        "pcb",
    }
    assert result["routing_authorized"] is False


def test_native_transition_stops_at_compile_report_after_provenance(tmp_path):
    for key in ("project", "package_manifest", "import_log"):
        _write(_path(tmp_path, key))
    _write(_path(tmp_path, "schematic"), _cfb_stub())
    _write(_path(tmp_path, "pcb"), _cfb_stub())

    _write_json(
        _path(tmp_path, "import_receipt"),
        {
            "schema": "ALTIUM-NATIVE-IMPORT-RECEIPT-001",
            "status": "PASS",
        },
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "WAITING_COMPILE_REPORT"
    assert result["missing_inputs"] == [
        "compile_report",
        "compile_report_raw",
    ]
    assert result["routing_authorized"] is False


def test_native_transition_full_pass_syncs_routing_authority(
    tmp_path,
    monkeypatch,
):
    for key in (
        "project",
        "package_manifest",
        "import_log",
        "bom_export",
        "component_inventory",
        "net_inventory",
        "rule_inventory",
        "pad_net_inventory",
        "layer_stack_inventory",
        "kicad_netlist_baseline",
        "netlist_export",
        "hierarchy_export",
        "no_mmwave_review",
        "manifest_template",
    ):
        _write(_path(tmp_path, key))
    _write(_path(tmp_path, "schematic"), _cfb_stub())
    _write(_path(tmp_path, "pcb"), _cfb_stub())

    _write_json(
        _path(tmp_path, "import_receipt"),
        {
            "schema": "ALTIUM-NATIVE-IMPORT-RECEIPT-001",
            "status": "PASS",
        },
    )
    _write(_path(tmp_path, "compile_report_raw"), b"RAW_COMPILE_REPORT")
    _write_json(
        _path(tmp_path, "compile_report"),
        {
            "schema": "ALTIUM-COMPILE-REPORT-001",
            "status": "PASS",
            "errors": 0,
            "warnings": 0,
        },
    )
    _write_json(
        _path(tmp_path, "native_status"),
        {
            "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
            "native_import_status": "WAITING_NATIVE_ALTIUM_IMPORT",
            "equivalence_gate_status": "NOT_RUN",
            "layout_authority": "NOT_AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "next_required_outputs": ["native/EVT_SYS_CARRIER.SchDoc"],
        },
    )
    _write_json(
        _path(tmp_path, "cad_authority"),
        {
            "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
            "native_document_status": "PENDING_ALTIUM_IMPORT",
            "pcb_layout_authority": "ALTIUM_AFTER_EQUIVALENCE_GATE",
            "pcb_design_phase": "ALTIUM_BOARD_PLANNING",
            "production_release_authorized": False,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_NATIVE_IMPORT",
            },
            "altium_rule_query_contract": {
                "status": "READY_TO_INSTANTIATE_AFTER_NATIVE_IMPORT",
            },
        },
    )
    _write_json(
        _path(tmp_path, "implementation_status"),
        {
            "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
            "current_phase": "IMPORT_PREPARED",
            "altium": {
                "native_schdoc": False,
                "native_pcbdoc": False,
                "equivalence_gate": False,
                "production_release_authorized": False,
            },
            "blockers": [
                "Native Altium import/save of SchDoc/PcbDoc has not yet been executed in Altium Designer.",
                "Fabricator binding still required before production release.",
            ],
            "routing_readiness": {
                "expected_status": "READY_FOR_NATIVE_IMPORT",
                "routing_authorized": False,
                "required_to_authorize": ["ALTIUM_EQUIVALENCE_GATE PASS"],
            },
        },
    )

    pass_result = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }

    monkeypatch.setattr(
        transition,
        "validate_compile_evidence",
        lambda **kwargs: {
            "schema": "ALTIUM-COMPILE-EVIDENCE-VALIDATION-001",
            "status": "PASS",
            "errors": [],
            "reason_codes": [],
            "compile": {
                "schema": "ALTIUM-COMPILE-REPORT-001",
                "status": "PASS",
                "errors": 0,
                "warnings": 0,
            },
        },
    )

    monkeypatch.setattr(
        transition,
        "validate_audit",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "native_pcb_audit": "PASS",
                "pinmap_equivalence": "PASS",
                "rules_equivalence": "PASS",
                "stackup_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_bom",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "bom_designator_mpn_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_footprint",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "footprint_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_connector",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "connector_pinout_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_netlist",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "netlist_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_hierarchy",
        lambda **kwargs: {
            **pass_result,
            "verified_checks": {
                "hierarchy_equivalence": "PASS",
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_no_mmwave",
        lambda **kwargs: {
            **pass_result,
            "reason_codes": [],
            "verified_checks": {
                "no_76_81GHz_rf_on_system_carrier": "PASS",
            },
        },
    )

    checks = {
        name: "PASS"
        for name in (
            "bom_designator_mpn_equivalence",
            "pinmap_equivalence",
            "connector_pinout_equivalence",
            "netlist_equivalence",
            "footprint_equivalence",
            "hierarchy_equivalence",
            "rules_equivalence",
            "stackup_equivalence",
            "no_76_81GHz_rf_on_system_carrier",
            "native_pcb_audit",
        )
    }
    monkeypatch.setattr(
        transition,
        "build_manifest",
        lambda **kwargs: {
            "status": "READY",
            "errors": [],
            "manifest": {
                "schema": "ALTIUM-EQUIVALENCE-MANIFEST-001",
                "checks": checks,
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "validate_gate",
        lambda *args, **kwargs: {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "errors": [],
            "reason_codes": [],
        },
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "READY_FOR_ROUTING"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False

    native_status = json.loads(
        _path(tmp_path, "native_status").read_text(encoding="utf-8")
    )
    assert native_status["native_import_status"] == "NATIVE_FILES_READY"
    assert native_status["equivalence_gate_status"] == "PASS"
    assert native_status["layout_authority"] == "AUTHORIZED"
    assert len(native_status["native_pcb_sha256"]) == 64
    assert len(native_status["native_schematic_sha256"]) == 64
    assert len(native_status["equivalence_result_sha256"]) == 64

    implementation = json.loads(
        _path(tmp_path, "implementation_status").read_text(
            encoding="utf-8"
        )
    )
    assert implementation["current_phase"] == "READY_FOR_ROUTING"
    assert implementation["altium"]["native_schdoc"] is True
    assert implementation["altium"]["native_pcbdoc"] is True
    assert implementation["altium"]["equivalence_gate"] is True
    assert (
        implementation["routing_readiness"]["expected_status"]
        == "READY_FOR_ROUTING"
    )
    assert implementation["routing_readiness"]["routing_authorized"] is True
    assert all(
        "Native Altium import/save" not in item
        for item in implementation["blockers"]
    )

    authority = json.loads(
        _path(tmp_path, "cad_authority").read_text(encoding="utf-8")
    )
    assert authority["native_document_status"] == "NATIVE_EQUIVALENCE_PASS"
    assert authority["pcb_layout_authority"] == "ALTIUM_AUTHORIZED"
    assert authority["pcb_design_phase"] == "ALTIUM_NATIVE_ROUTING"
    assert (
        authority["routing_readiness_gate"]["current_expected_status"]
        == "READY_FOR_ROUTING"
    )
    assert authority["altium_rule_query_contract"]["status"] == (
        "NATIVE_EQUIVALENCE_PASS"
    )
    assert authority["native_pcb_sha256"] == native_status["native_pcb_sha256"]



def test_native_transition_short_circuits_valid_post_equivalence(
    tmp_path,
    monkeypatch,
):
    for key in ("project", "schematic", "pcb"):
        _write(_path(tmp_path, key), b"NATIVE")

    monkeypatch.setattr(
        transition,
        "validate_native_files",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-FILE-PREFLIGHT-001",
            "status": "PASS",
            "errors": [],
            "artifacts": {
                "schematic": {"path": "x", "sha256": "1" * 64},
                "pcb": {"path": "y", "sha256": "2" * 64},
            },
        },
    )
    monkeypatch.setattr(
        transition,
        "evaluate_native_ci",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-CI-GATE-001",
            "status": "PASS",
            "phase": "POST_EQUIVALENCE",
            "routing_authorized": True,
            "production_authorized": False,
        },
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "READY_FOR_ROUTING"
    assert result["next_action"] == (
        "CONTINUE_NATIVE_ALTIUM_PLACEMENT_AND_ROUTING"
    )
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False
    assert result["generated_artifacts"] == []
    assert "existing_lifecycle" in result["stage_results"]
    assert not _path(tmp_path, "native_file_preflight").exists()


def test_native_transition_short_circuits_valid_post_production(
    tmp_path,
    monkeypatch,
):
    for key in ("project", "schematic", "pcb"):
        _write(_path(tmp_path, key), b"NATIVE")

    monkeypatch.setattr(
        transition,
        "validate_native_files",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-FILE-PREFLIGHT-001",
            "status": "PASS",
            "errors": [],
            "artifacts": {},
        },
    )
    monkeypatch.setattr(
        transition,
        "evaluate_native_ci",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-CI-GATE-001",
            "status": "PASS",
            "phase": "POST_PRODUCTION",
            "routing_authorized": True,
            "production_authorized": True,
        },
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "PRODUCTION_RELEASED"
    assert result["next_action"] == "PRODUCTION_ALREADY_RELEASED"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is True
    assert result["generated_artifacts"] == []
    assert not _path(tmp_path, "native_file_preflight").exists()


def test_native_transition_force_recheck_bypasses_valid_lifecycle_guard(
    tmp_path,
    monkeypatch,
):
    for key in ("project", "schematic", "pcb"):
        _write(_path(tmp_path, key), b"NATIVE")

    monkeypatch.setattr(
        transition,
        "validate_native_files",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-FILE-PREFLIGHT-001",
            "status": "PASS",
            "errors": [],
            "artifacts": {},
        },
    )
    monkeypatch.setattr(
        transition,
        "evaluate_native_ci",
        lambda **kwargs: {
            "schema": "ALTIUM-NATIVE-CI-GATE-001",
            "status": "PASS",
            "phase": "POST_EQUIVALENCE",
            "routing_authorized": True,
            "production_authorized": False,
        },
    )

    result = transition.run_transition(
        repository_root=tmp_path,
        force_recheck=True,
    )

    assert result["status"] == "WAITING_IMPORT_PROVENANCE"
    assert result["routing_authorized"] is False
    assert "package_manifest" in result["missing_inputs"]
    assert "import_log" in result["missing_inputs"]
    assert _path(tmp_path, "native_file_preflight").is_file()
    assert "existing_lifecycle" not in result["stage_results"]
