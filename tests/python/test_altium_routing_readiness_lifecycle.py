import hashlib
import json
from pathlib import Path

import tools.altium_routing_readiness as routing


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_schematic(altium: Path, data: bytes = b"NATIVE_SCH") -> str:
    path = altium / "native" / "EVT_SYS_CARRIER.SchDoc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_authority_result(
    altium: Path,
    *,
    production: bool,
) -> str:
    if production:
        path = altium / "release" / "production_release_result.json"
        payload = {
            "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
        }
    else:
        path = (
            altium
            / "equivalence"
            / "altium_equivalence_result.json"
        )
        payload = {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
        }

    _write_json(path, payload)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_routing_readiness_remains_valid_after_production_release(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    schematic_hash = _write_schematic(altium)
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.parent.mkdir(parents=True, exist_ok=True)
    pcb.write_bytes(b"FINAL_NATIVE_PCB")
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()
    equivalence_result_hash = _write_authority_result(
        altium,
        production=False,
    )
    production_result_hash = _write_authority_result(
        altium,
        production=True,
    )

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "production_release_source_pcb_sha256": pcb_hash,
            "production_release_result_sha256": production_result_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "PRODUCTION_RELEASED",
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": True,
                "native_pcb_sha256": pcb_hash,
                "production_release_source_pcb_sha256": pcb_hash,
            },
            "routing_readiness": {
                "routing_authorized": True,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "PRODUCTION_RELEASED",
            "production_release_authorized": True,
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "production_release_source_pcb_sha256": pcb_hash,
            "production_release_result_sha256": production_result_hash,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "READY_FOR_ROUTING"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is True
    assert result["layout_authority_consensus"] is True
    assert result["production_authority_consensus"] is True
    assert result["authority_consensus_errors"] == []
    assert (
        result["current_equivalence_result_sha256"]
        == equivalence_result_hash
    )
    assert (
        result["current_production_result_sha256"]
        == production_result_hash
    )
    assert result["production_release_stale"] is False
    assert result["expected_release_pcb_sha256"] == pcb_hash
    assert result["current_pcb_sha256"] == pcb_hash
    assert result["next_action"] == "PRODUCTION_RELEASED"
    assert result["errors"] == []



def test_routing_readiness_detects_stale_production_release(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    schematic_hash = _write_schematic(altium)
    approved_pcb_hash = hashlib.sha256(
        b"APPROVED_PRODUCTION_PCB"
    ).hexdigest()
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.parent.mkdir(parents=True, exist_ok=True)
    pcb.write_bytes(b"CHANGED_AFTER_PRODUCTION_RELEASE")
    equivalence_result_hash = _write_authority_result(
        altium,
        production=False,
    )
    production_result_hash = _write_authority_result(
        altium,
        production=True,
    )

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": approved_pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "production_release_source_pcb_sha256": approved_pcb_hash,
            "production_release_result_sha256": production_result_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "PRODUCTION_RELEASED",
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": True,
                "native_pcb_sha256": approved_pcb_hash,
                "production_release_source_pcb_sha256": approved_pcb_hash,
            },
            "routing_readiness": {
                "routing_authorized": True,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "PRODUCTION_RELEASED",
            "production_release_authorized": True,
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": approved_pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "production_release_source_pcb_sha256": approved_pcb_hash,
            "production_release_result_sha256": production_result_hash,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "READY_FOR_ROUTING"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is False
    assert result["production_release_stale"] is True
    assert result["next_action"] == "RERUN_PRODUCTION_RELEASE_GATE"
    assert "production_release_pcb_hash_mismatch" in result["warnings"]



def test_routing_readiness_detects_stale_equivalence_after_schematic_change(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    approved_hash = _write_schematic(altium, b"APPROVED_SCHEMATIC")
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"PRE_ROUTING_PCB")
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()
    equivalence_result_hash = _write_authority_result(
        altium,
        production=False,
    )
    schematic = altium / "native" / "EVT_SYS_CARRIER.SchDoc"
    schematic.write_bytes(b"CHANGED_AFTER_EQUIVALENCE")

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "native_schematic_sha256": approved_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "READY_FOR_ROUTING",
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": False,
                "native_pcb_sha256": pcb_hash,
            },
            "routing_readiness": {
                "routing_authorized": True,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "ALTIUM_NATIVE_ROUTING",
            "production_release_authorized": False,
            "native_schematic_sha256": approved_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "STALE_EQUIVALENCE"
    assert result["routing_authorized"] is False
    assert result["production_authorized"] is False
    assert result["equivalence_stale"] is True
    assert result["expected_schematic_sha256"] == approved_hash
    assert result["current_schematic_sha256"] != approved_hash
    assert result["next_action"] == "RERUN_NATIVE_ALTIUM_EQUIVALENCE_GATE"
    assert "equivalence_schematic_hash_mismatch" in result["warnings"]



def test_routing_readiness_blocks_partial_authority_sync(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    schematic_hash = _write_schematic(altium)
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"PRE_ROUTING_PCB")
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    # Simulate a crash after only ALTIUM_NATIVE_STATUS was written.
    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "IMPORT_PREPARED",
            "altium": {
                "equivalence_gate": False,
                "production_release_authorized": False,
            },
            "routing_readiness": {
                "routing_authorized": False,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "PENDING_ALTIUM_IMPORT",
            "pcb_layout_authority": "ALTIUM_AFTER_EQUIVALENCE_GATE",
            "pcb_design_phase": "ALTIUM_BOARD_PLANNING",
            "production_release_authorized": False,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_NATIVE_IMPORT",
            },
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "BLOCKED"
    assert result["routing_authorized"] is False
    assert result["production_authorized"] is False
    assert result["layout_authority_consensus"] is False
    assert "layout:implementation_status" in result[
        "authority_consensus_errors"
    ]
    assert "layout:cad_authority" in result["authority_consensus_errors"]
    assert any(
        item.startswith("authority_consensus:")
        for item in result["errors"]
    )



def test_routing_readiness_blocks_gate_result_hash_disagreement(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    schematic_hash = _write_schematic(altium)
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"PRE_ROUTING_PCB")
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": "1" * 64,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "READY_FOR_ROUTING",
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": False,
                "native_pcb_sha256": pcb_hash,
            },
            "routing_readiness": {
                "routing_authorized": True,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "ALTIUM_NATIVE_ROUTING",
            "production_release_authorized": False,
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": "2" * 64,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "BLOCKED"
    assert result["routing_authorized"] is False
    assert (
        "hash:equivalence_result_sha256"
        in result["authority_consensus_errors"]
    )



def test_routing_readiness_blocks_tampered_equivalence_result(
    tmp_path,
    monkeypatch,
):
    system = tmp_path / "hardware/system_carrier"
    altium = system / "altium"
    generated = tmp_path / "generated"
    generated.mkdir()

    schematic_hash = _write_schematic(altium)
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"PRE_ROUTING_PCB")
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()
    equivalence_result_hash = _write_authority_result(
        altium,
        production=False,
    )

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_evt_mechanical_datum",
        "validate_rooms",
        "validate_impedance",
        "validate_evt_routing_stack",
        "validate_power_width",
        "validate_rule_scope",
    ):
        monkeypatch.setattr(
            routing,
            name,
            lambda *args, **kwargs: dict(pass_result),
        )
    monkeypatch.setattr(
        routing,
        "validate_prelayout",
        lambda **kwargs: dict(pass_result),
    )

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "READY_FOR_ROUTING",
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": False,
                "native_pcb_sha256": pcb_hash,
            },
            "routing_readiness": {
                "routing_authorized": True,
            },
        },
    )
    _write_json(
        system / "CAD_AUTHORITY_SYS_001.json",
        {
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": "ALTIUM_NATIVE_ROUTING",
            "production_release_authorized": False,
            "native_schematic_sha256": schematic_hash,
            "native_pcb_sha256": pcb_hash,
            "equivalence_result_sha256": equivalence_result_hash,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )

    result_path = (
        altium / "equivalence" / "altium_equivalence_result.json"
    )
    _write_json(
        result_path,
        {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "FAIL",
            "layout_authority": "NOT_AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "BLOCKED"
    assert result["routing_authorized"] is False
    assert "hash:equivalence_result_file" in result[
        "authority_consensus_errors"
    ]
    assert "result:equivalence_semantics" in result[
        "authority_consensus_errors"
    ]
