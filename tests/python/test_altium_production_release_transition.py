import hashlib
import json
from pathlib import Path

import tools.altium_production_release_transition as transition


def _write(path: Path, data: bytes = b"TEST") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _path(root: Path, key: str) -> Path:
    return root / transition.PATHS[key]


def test_production_transition_waits_for_equivalence(tmp_path):
    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "WAITING_EQUIVALENCE_PASS"
    assert result["production_authorized"] is False
    assert result["next_action"] == "COMPLETE_NATIVE_EQUIVALENCE"


def test_production_transition_pass_syncs_authority(
    tmp_path,
    monkeypatch,
):
    _write(_path(tmp_path, "native_schematic"), b"APPROVED_NATIVE_SCH")
    _write(_path(tmp_path, "native_pcb"), b"FINAL_NATIVE_PCB")
    _write_json(
        _path(tmp_path, "manifest"),
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
            "artifacts": [],
        },
    )
    _write_json(
        _path(tmp_path, "native_status"),
        {
            "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
        },
    )
    _write_json(
        _path(tmp_path, "implementation_status"),
        {
            "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
            "current_phase": "READY_FOR_ROUTING",
            "altium": {
                "native_schdoc": True,
                "native_pcbdoc": True,
                "equivalence_gate": True,
                "placement_started": False,
                "routing_started": False,
                "production_release_authorized": False,
            },
            "blockers": ["Production release not complete"],
            "routing_readiness": {
                "expected_status": "READY_FOR_ROUTING",
                "routing_authorized": True,
                "required_to_authorize": [],
            },
        },
    )
    _write_json(
        _path(tmp_path, "cad_authority"),
        {
            "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "ALTIUM_NATIVE_ROUTING",
            "production_release_authorized": False,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    monkeypatch.setattr(
        transition,
        "evaluate_release_status",
        lambda root: {
            "schema": "ALTIUM-PRODUCTION-RELEASE-STATUS-001",
            "status": "READY_TO_RUN_PRODUCTION_RELEASE_GATE",
            "next_action": "RUN_ALTIUM_PRODUCTION_RELEASE_GATE",
            "missing_artifacts": [],
            "invalid_artifacts": [],
            "non_pass_artifacts": [],
            "manifest_errors": [],
        },
    )
    schematic_hash = hashlib.sha256(
        _path(tmp_path, "native_schematic").read_bytes()
    ).hexdigest()
    pcb_hash = hashlib.sha256(
        _path(tmp_path, "native_pcb").read_bytes()
    ).hexdigest()
    gate = {
        "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
        "status": "PASS",
        "layout_authority": "AUTHORIZED",
        "production_authority": "AUTHORIZED",
        "native_schematic_sha256": schematic_hash,
        "native_pcb_sha256": pcb_hash,
        "errors": [],
        "reason_codes": [],
    }
    monkeypatch.setattr(
        transition,
        "validate_release_gate",
        lambda *args, **kwargs: gate,
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "PRODUCTION_RELEASED"
    assert result["production_authorized"] is True

    native_status = json.loads(
        _path(tmp_path, "native_status").read_text(encoding="utf-8")
    )
    assert native_status["production_authority"] == "AUTHORIZED"
    assert len(native_status["production_release_result_sha256"]) == 64
    assert native_status["native_schematic_sha256"] == schematic_hash
    assert (
        native_status["production_release_source_schematic_sha256"]
        == schematic_hash
    )
    assert native_status["native_pcb_sha256"] == pcb_hash
    assert native_status["production_release_source_pcb_sha256"] == pcb_hash

    implementation = json.loads(
        _path(tmp_path, "implementation_status").read_text(
            encoding="utf-8"
        )
    )
    assert implementation["current_phase"] == "PRODUCTION_RELEASED"
    assert implementation["next_required_phase"] == "NONE"
    assert implementation["altium"]["placement_started"] is True
    assert implementation["altium"]["routing_started"] is True
    assert implementation["altium"]["production_release_authorized"] is True
    assert implementation["blockers"] == []

    authority = json.loads(
        _path(tmp_path, "cad_authority").read_text(encoding="utf-8")
    )
    assert authority["pcb_design_phase"] == "PRODUCTION_RELEASED"
    assert authority["production_release_authorized"] is True
    assert len(authority["production_release_result_sha256"]) == 64


def test_production_transition_builds_missing_manifest(
    tmp_path,
    monkeypatch,
):
    _write(
        _path(tmp_path, "manifest_template"),
        b'{"schema":"ALTIUM-PRODUCTION-RELEASE-MANIFEST-001"}',
    )

    calls = {"count": 0}

    def fake_status(root):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "status": "WAITING_RELEASE_MANIFEST",
                "next_action": "BUILD_PRODUCTION_RELEASE_MANIFEST",
                "missing_artifacts": ["manifest"],
                "invalid_artifacts": [],
                "non_pass_artifacts": [],
                "manifest_errors": [],
            }
        return {
            "status": "WAITING_EQUIVALENCE_PASS",
            "next_action": "COMPLETE_NATIVE_EQUIVALENCE",
            "missing_artifacts": [],
            "invalid_artifacts": [],
            "non_pass_artifacts": [],
            "manifest_errors": [],
        }

    monkeypatch.setattr(
        transition,
        "evaluate_release_status",
        fake_status,
    )
    monkeypatch.setattr(
        transition,
        "build_manifest",
        lambda **kwargs: {
            "status": "READY",
            "errors": [],
            "manifest": {
                "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
                "artifacts": [],
            },
        },
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert _path(tmp_path, "manifest").is_file()
    assert transition.PATHS["manifest"].as_posix() in (
        result["generated_artifacts"]
    )
    assert result["status"] == "WAITING_EQUIVALENCE_PASS"



def test_production_transition_blocks_if_pcb_changes_after_gate(
    tmp_path,
    monkeypatch,
):
    _write(_path(tmp_path, "native_schematic"), b"APPROVED_NATIVE_SCH")
    _write(_path(tmp_path, "native_pcb"), b"FINAL_NATIVE_PCB")
    _write_json(
        _path(tmp_path, "manifest"),
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
            "artifacts": [],
        },
    )
    for key, payload in (
        (
            "native_status",
            {
                "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
                "production_authority": "NOT_AUTHORIZED",
            },
        ),
        (
            "implementation_status",
            {
                "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
                "current_phase": "READY_FOR_ROUTING",
                "altium": {},
                "routing_readiness": {},
            },
        ),
        (
            "cad_authority",
            {
                "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
                "production_release_authorized": False,
                "routing_readiness_gate": {},
            },
        ),
    ):
        _write_json(_path(tmp_path, key), payload)

    monkeypatch.setattr(
        transition,
        "evaluate_release_status",
        lambda root: {
            "status": "READY_TO_RUN_PRODUCTION_RELEASE_GATE",
            "next_action": "RUN_ALTIUM_PRODUCTION_RELEASE_GATE",
            "missing_artifacts": [],
            "invalid_artifacts": [],
            "non_pass_artifacts": [],
            "manifest_errors": [],
        },
    )

    approved_schematic_hash = hashlib.sha256(
        _path(tmp_path, "native_schematic").read_bytes()
    ).hexdigest()
    approved_hash = hashlib.sha256(
        _path(tmp_path, "native_pcb").read_bytes()
    ).hexdigest()

    def gate_then_change(*args, **kwargs):
        _path(tmp_path, "native_pcb").write_bytes(b"CHANGED_AFTER_GATE")
        return {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "native_schematic_sha256": approved_schematic_hash,
            "native_pcb_sha256": approved_hash,
            "errors": [],
            "reason_codes": [],
        }

    monkeypatch.setattr(
        transition,
        "validate_release_gate",
        gate_then_change,
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "PASS_STATUS_SYNC_FAILED"
    assert result["production_authorized"] is False
    assert any(
        "changed after production gate PASS" in item
        for item in result["errors"]
    )

    native_status = json.loads(
        _path(tmp_path, "native_status").read_text(encoding="utf-8")
    )
    assert native_status["production_authority"] == "NOT_AUTHORIZED"



def test_production_transition_blocks_if_schematic_changes_after_gate(
    tmp_path,
    monkeypatch,
):
    _write(_path(tmp_path, "native_schematic"), b"APPROVED_NATIVE_SCH")
    _write(_path(tmp_path, "native_pcb"), b"FINAL_NATIVE_PCB")
    _write_json(
        _path(tmp_path, "manifest"),
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
            "artifacts": [],
        },
    )
    for key, payload in (
        (
            "native_status",
            {
                "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
                "production_authority": "NOT_AUTHORIZED",
            },
        ),
        (
            "implementation_status",
            {
                "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
                "current_phase": "READY_FOR_ROUTING",
                "altium": {},
                "routing_readiness": {},
            },
        ),
        (
            "cad_authority",
            {
                "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
                "production_release_authorized": False,
                "routing_readiness_gate": {},
            },
        ),
    ):
        _write_json(_path(tmp_path, key), payload)

    monkeypatch.setattr(
        transition,
        "evaluate_release_status",
        lambda root: {
            "status": "READY_TO_RUN_PRODUCTION_RELEASE_GATE",
            "next_action": "RUN_ALTIUM_PRODUCTION_RELEASE_GATE",
            "missing_artifacts": [],
            "invalid_artifacts": [],
            "non_pass_artifacts": [],
            "manifest_errors": [],
        },
    )

    approved_schematic_hash = hashlib.sha256(
        _path(tmp_path, "native_schematic").read_bytes()
    ).hexdigest()
    approved_pcb_hash = hashlib.sha256(
        _path(tmp_path, "native_pcb").read_bytes()
    ).hexdigest()

    def gate_then_change(*args, **kwargs):
        _path(tmp_path, "native_schematic").write_bytes(
            b"CHANGED_AFTER_GATE"
        )
        return {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "native_schematic_sha256": approved_schematic_hash,
            "native_pcb_sha256": approved_pcb_hash,
            "errors": [],
            "reason_codes": [],
        }

    monkeypatch.setattr(
        transition,
        "validate_release_gate",
        gate_then_change,
    )

    result = transition.run_transition(repository_root=tmp_path)

    assert result["status"] == "PASS_STATUS_SYNC_FAILED"
    assert result["production_authorized"] is False
    assert any(
        "SchDoc changed after production gate PASS" in item
        for item in result["errors"]
    )

    native_status = json.loads(
        _path(tmp_path, "native_status").read_text(encoding="utf-8")
    )
    assert native_status["production_authority"] == "NOT_AUTHORIZED"
