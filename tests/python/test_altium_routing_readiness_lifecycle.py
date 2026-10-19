import json
from pathlib import Path

import tools.altium_routing_readiness as routing


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def test_routing_readiness_remains_valid_after_production_release(
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

    _write_json(
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json",
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "AUTHORIZED",
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
    assert result["errors"] == []
