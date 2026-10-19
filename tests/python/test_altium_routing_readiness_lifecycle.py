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

    pass_result = {
        "schema": "TEST",
        "status": "PASS",
        "errors": [],
        "warnings": [],
    }
    for name in (
        "validate_cad_policy",
        "validate_placement",
        "validate_rooms",
        "validate_impedance",
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
            "production_release_source_pcb_sha256": pcb_hash,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "PRODUCTION_RELEASED",
        },
    )

    result = routing.validate(
        system_root=system,
        generated_dir=generated,
    )

    assert result["status"] == "READY_FOR_ROUTING"
    assert result["routing_authorized"] is True
    assert result["production_authorized"] is True
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
        "validate_rooms",
        "validate_impedance",
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
    pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.parent.mkdir(parents=True, exist_ok=True)
    pcb.write_bytes(b"CHANGED_AFTER_PRODUCTION_RELEASE")

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
            "native_schematic_sha256": schematic_hash,
            "production_release_source_pcb_sha256": "0" * 64,
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "PRODUCTION_RELEASED",
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
        "validate_rooms",
        "validate_impedance",
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
        },
    )
    _write_json(
        altium / "ALTIUM_STATUS_SYS_001.json",
        {
            "current_phase": "READY_FOR_ROUTING",
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
