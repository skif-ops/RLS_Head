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
        "integrity": {
            "schematic": {
                "path": ci_gate.SCHDOC_REL.as_posix(),
                "sha256_actual": _sha(schdoc),
                "hash_ok": True,
            },
            "pcb": {
                "path": ci_gate.PCBDOC_REL.as_posix(),
                "sha256_actual": _sha(pcbdoc),
                "hash_ok": True,
            },
        },
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
    assert result["layout_evolved_since_equivalence"] is False
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False




def test_native_ci_gate_allows_pcb_layout_evolution_after_equivalence(
    tmp_path,
    monkeypatch,
):
    gate_result, _, pcbdoc = _post_equivalence_fixture(
        tmp_path,
        monkeypatch,
    )
    approved_pcb_hash = gate_result["integrity"]["pcb"]["sha256_actual"]
    pcbdoc.write_bytes(b"ROUTED_PCBDOC_AFTER_EQUIVALENCE")

    def should_not_replay_prerouting_equivalence(*args, **kwargs):
        raise AssertionError(
            "full pre-routing equivalence gate must not replay after PCB routing"
        )

    monkeypatch.setattr(
        ci_gate,
        "validate_equivalence",
        should_not_replay_prerouting_equivalence,
    )

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["equivalence_status"] == "PASS"
    assert result["layout_evolved_since_equivalence"] is True
    assert result["approved_prerouting_pcb_sha256"] == approved_pcb_hash
    assert result["current_pcb_sha256"] != approved_pcb_hash
    assert "pcb_layout_evolved_since_equivalence" in result["warnings"]
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False


def test_native_ci_gate_rejects_schematic_change_after_equivalence(
    tmp_path,
    monkeypatch,
):
    gate_result, _, _ = _post_equivalence_fixture(
        tmp_path,
        monkeypatch,
    )
    approved_schematic_hash = gate_result["integrity"]["schematic"][
        "sha256_actual"
    ]
    schdoc = tmp_path / ci_gate.SCHDOC_REL
    schdoc.write_bytes(b"CHANGED_SCHDOC_AFTER_EQUIVALENCE")

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["approved_schematic_sha256"] == approved_schematic_hash
    assert result["current_schematic_sha256"] != approved_schematic_hash
    assert "equivalence_schematic_hash_mismatch" in result["errors"]
    assert result["routing_authorized"] is False

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



def test_native_ci_gate_passes_post_production_state(
    tmp_path,
    monkeypatch,
):
    production_result = {
        "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
        "status": "PASS",
        "layout_authority": "AUTHORIZED",
        "production_authority": "AUTHORIZED",
        "errors": [],
        "reason_codes": [],
    }

    gate_result, _, pcbdoc = _post_equivalence_fixture(
        tmp_path,
        monkeypatch,
    )
    approved_pcb_hash = gate_result["integrity"]["pcb"]["sha256_actual"]
    pcbdoc.write_bytes(b"FINAL_ROUTED_PCBDOC")

    release_manifest = tmp_path / ci_gate.RELEASE_MANIFEST_REL
    production_path = tmp_path / ci_gate.PRODUCTION_RESULT_REL
    _write_json(
        release_manifest,
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
            "artifacts": [],
        },
    )
    _write_json(production_path, production_result)

    native_status_path = tmp_path / ci_gate.NATIVE_STATUS_REL
    native_status = json.loads(
        native_status_path.read_text(encoding="utf-8")
    )
    native_status["production_authority"] = "AUTHORIZED"
    native_status["native_pcb_sha256"] = _sha(pcbdoc)
    native_status["production_release_result_sha256"] = _sha(
        production_path
    )
    _write_json(native_status_path, native_status)

    authority_path = tmp_path / ci_gate.CAD_AUTHORITY_REL
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )
    authority["production_release_authorized"] = True
    authority["pcb_design_phase"] = "PRODUCTION_RELEASED"
    authority["native_pcb_sha256"] = _sha(pcbdoc)
    authority["production_release_result_sha256"] = _sha(
        production_path
    )
    _write_json(authority_path, authority)

    implementation_path = tmp_path / ci_gate.IMPLEMENTATION_STATUS_REL
    implementation = json.loads(
        implementation_path.read_text(encoding="utf-8")
    )
    implementation["current_phase"] = "PRODUCTION_RELEASED"
    implementation["altium"]["production_release_authorized"] = True
    implementation["altium"]["native_pcb_sha256"] = _sha(pcbdoc)
    implementation["altium"]["placement_started"] = True
    implementation["altium"]["routing_started"] = True
    _write_json(implementation_path, implementation)

    monkeypatch.setattr(
        ci_gate,
        "validate_production_release",
        lambda *args, **kwargs: production_result,
    )

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["phase"] == "POST_PRODUCTION"
    assert result["production_result_present"] is True
    assert result["layout_evolved_since_equivalence"] is True
    assert result["approved_prerouting_pcb_sha256"] == approved_pcb_hash
    assert result["current_pcb_sha256"] != approved_pcb_hash
    assert result["production_release_status"] == "PASS"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is True


def test_native_ci_gate_rejects_stale_production_result_hash(
    tmp_path,
    monkeypatch,
):
    production_result = {
        "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
        "status": "PASS",
        "layout_authority": "AUTHORIZED",
        "production_authority": "AUTHORIZED",
        "errors": [],
        "reason_codes": [],
    }

    _post_equivalence_fixture(tmp_path, monkeypatch)
    _write_json(
        tmp_path / ci_gate.RELEASE_MANIFEST_REL,
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
            "artifacts": [],
        },
    )
    production_path = tmp_path / ci_gate.PRODUCTION_RESULT_REL
    _write_json(production_path, production_result)

    native_status_path = tmp_path / ci_gate.NATIVE_STATUS_REL
    native_status = json.loads(
        native_status_path.read_text(encoding="utf-8")
    )
    native_status["production_authority"] = "AUTHORIZED"
    native_status["production_release_result_sha256"] = "0" * 64
    _write_json(native_status_path, native_status)

    authority_path = tmp_path / ci_gate.CAD_AUTHORITY_REL
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )
    authority["production_release_authorized"] = True
    authority["pcb_design_phase"] = "PRODUCTION_RELEASED"
    authority["production_release_result_sha256"] = _sha(production_path)
    _write_json(authority_path, authority)

    implementation_path = tmp_path / ci_gate.IMPLEMENTATION_STATUS_REL
    implementation = json.loads(
        implementation_path.read_text(encoding="utf-8")
    )
    implementation["current_phase"] = "PRODUCTION_RELEASED"
    implementation["altium"]["production_release_authorized"] = True
    implementation["altium"]["placement_started"] = True
    implementation["altium"]["routing_started"] = True
    _write_json(implementation_path, implementation)

    monkeypatch.setattr(
        ci_gate,
        "validate_production_release",
        lambda *args, **kwargs: production_result,
    )

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert (
        "native_status_hash:production_release_result_sha256"
        in result["errors"]
    )



def test_native_ci_gate_does_not_treat_failed_release_result_as_production(
    tmp_path,
    monkeypatch,
):
    _post_equivalence_fixture(tmp_path, monkeypatch)

    production_path = tmp_path / ci_gate.PRODUCTION_RESULT_REL
    _write_json(
        production_path,
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "FAIL",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "errors": [],
            "reason_codes": ["DFM_P0_OPEN_ITEMS"],
        },
    )

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["production_result_present"] is True
    assert result["production_authorized"] is False
    assert "committed_production_not_pass" in result["errors"]
    assert "committed_production_authority" in result["errors"]



def test_native_ci_gate_treats_revoked_pass_release_as_historical(
    tmp_path,
    monkeypatch,
):
    _post_equivalence_fixture(tmp_path, monkeypatch)

    production_path = tmp_path / ci_gate.PRODUCTION_RESULT_REL
    _write_json(
        production_path,
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "errors": [],
            "reason_codes": [],
        },
    )

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["production_result_present"] is True
    assert result["production_result_pass"] is True
    assert result["production_result_active"] is False
    assert result["production_authority_surfaces"] == {
        "native_status": False,
        "implementation_status": False,
        "cad_authority": False,
    }
    assert "historical_production_result_inactive" in result["warnings"]
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False


def test_native_ci_gate_rejects_partial_production_authority_consensus(
    tmp_path,
    monkeypatch,
):
    _post_equivalence_fixture(tmp_path, monkeypatch)

    production_path = tmp_path / ci_gate.PRODUCTION_RESULT_REL
    _write_json(
        production_path,
        {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "errors": [],
            "reason_codes": [],
        },
    )

    native_status_path = tmp_path / ci_gate.NATIVE_STATUS_REL
    native_status = json.loads(
        native_status_path.read_text(encoding="utf-8")
    )
    native_status["production_authority"] = "AUTHORIZED"
    _write_json(native_status_path, native_status)

    result = ci_gate.evaluate(repository_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["phase"] == "POST_EQUIVALENCE"
    assert result["production_result_pass"] is True
    assert result["production_result_active"] is False
    assert "production_authority_surface_consensus" in result["errors"]
    assert result["production_authorized"] is False
