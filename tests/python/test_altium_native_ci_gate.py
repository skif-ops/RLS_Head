import hashlib
import json
from pathlib import Path

import tools.altium_native_ci_gate as ci_gate


def _write(path: Path, data: bytes = b"TEST") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_native_ci_gate_passes_pre_import_repository(tmp_path):
    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["phase"] == "PRE_IMPORT"
    assert result["native_schdoc_present"] is False
    assert result["native_pcbdoc_present"] is False
    assert result["handoff_status"] == "WAITING_NATIVE_IMPORT"
    assert result["routing_authorized"] is False
    assert result["production_authorized"] is False


def test_native_ci_gate_rejects_incomplete_native_pair(tmp_path):
    schdoc = tmp_path / ci_gate.SCHDOC_REL
    _write(schdoc, b"SCHDOC")

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["phase"] == "INCOMPLETE_NATIVE_PAIR"
    assert "native_document_pair_incomplete" in result["errors"]


def _post_equivalence_fixture(
    tmp_path: Path,
    monkeypatch,
) -> tuple[dict, Path, Path]:
    schdoc = tmp_path / ci_gate.SCHDOC_REL
    pcbdoc = tmp_path / ci_gate.PCBDOC_REL
    manifest = tmp_path / ci_gate.MANIFEST_REL
    gate_path = tmp_path / ci_gate.GATE_RESULT_REL
    native_status_path = tmp_path / ci_gate.NATIVE_STATUS_REL
    implementation_path = tmp_path / ci_gate.IMPLEMENTATION_STATUS_REL
    authority_path = tmp_path / ci_gate.CAD_AUTHORITY_REL

    _write(schdoc, b"NATIVE_SCHDOC")
    _write(pcbdoc, b"NATIVE_PCBDOC")
    _write_json(
        manifest,
        {
            "schema": "ALTIUM-EQUIVALENCE-MANIFEST-001",
            "checks": {},
        },
    )

    gate_result = {
        "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
        "status": "PASS",
        "layout_authority": "AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "errors": [],
        "reason_codes": [],
    }
    _write_json(gate_path, gate_result)

    _write_json(
        native_status_path,
        {
            "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "native_schematic_sha256": _sha(schdoc),
            "native_pcb_sha256": _sha(pcbdoc),
            "equivalence_result_sha256": _sha(gate_path),
        },
    )
    _write_json(
        authority_path,
        {
            "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "production_release_authorized": False,
            "native_schematic_sha256": _sha(schdoc),
            "native_pcb_sha256": _sha(pcbdoc),
            "equivalence_result_sha256": _sha(gate_path),
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )
    _write_json(
        implementation_path,
        {
            "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
            "current_phase": "READY_FOR_ROUTING",
            "altium": {
                "native_schdoc": True,
                "native_pcbdoc": True,
                "equivalence_gate": True,
                "production_release_authorized": False,
                "native_pcb_sha256": _sha(pcbdoc),
            },
            "routing_readiness": {
                "expected_status": "READY_FOR_ROUTING",
                "routing_authorized": True,
            },
        },
    )

    monkeypatch.setattr(
        ci_gate,
        "evaluate_handoff",
        lambda root: {
            "status": "READY_TO_RUN_EQUIVALENCE_GATE",
        },
    )
    monkeypatch.setattr(
        ci_gate,
        "validate_equivalence",
        lambda *args, **kwargs: gate_result,
    )

    return gate_result, native_status_path, pcbdoc


def test_native_ci_gate_passes_post_equivalence_state(
    tmp_path,
    monkeypatch,
):
    _post_equivalence_fixture(tmp_path, monkeypatch)

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["equivalence_status"] == "PASS"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False


def test_native_ci_gate_rejects_stale_authority_hash(
    tmp_path,
    monkeypatch,
):
    _, native_status_path, _ = _post_equivalence_fixture(
        tmp_path,
        monkeypatch,
    )
    native_status = json.loads(
        native_status_path.read_text(encoding="utf-8")
    )
    native_status["native_pcb_sha256"] = "0" * 64
    _write_json(native_status_path, native_status)

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert "native_status_hash:native_pcb_sha256" in result["errors"]



def test_native_ci_gate_rejects_stale_cad_authority_hash(
    tmp_path,
    monkeypatch,
):
    _post_equivalence_fixture(tmp_path, monkeypatch)
    authority_path = tmp_path / ci_gate.CAD_AUTHORITY_REL
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )
    authority["native_pcb_sha256"] = "0" * 64
    _write_json(authority_path, authority)

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert "cad_authority_hash:native_pcb_sha256" in result["errors"]
