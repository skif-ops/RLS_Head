import hashlib
import json
from pathlib import Path

from tools.altium_authority_reconcile import PATHS, reconcile


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _setup_authorized(root: Path, *, production: bool) -> tuple[str, str]:
    schematic = root / PATHS["schematic"]
    pcb = root / PATHS["pcb"]
    schematic.parent.mkdir(parents=True, exist_ok=True)
    schematic.write_bytes(b"APPROVED_SCHEMATIC")
    pcb.write_bytes(b"FINAL_NATIVE_PCB")
    sch_hash = hashlib.sha256(schematic.read_bytes()).hexdigest()
    pcb_hash = hashlib.sha256(pcb.read_bytes()).hexdigest()

    _write_json(
        root / PATHS["equivalence_result"],
        {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
            "integrity": {
                "schematic": {
                    "sha256_actual": sch_hash,
                }
            },
        },
    )

    if production:
        _write_json(
            root / PATHS["production_result"],
            {
                "schema": "ALTIUM-PRODUCTION-RELEASE-RESULT-001",
                "status": "PASS",
                "layout_authority": "AUTHORIZED",
                "production_authority": "AUTHORIZED",
                "native_pcb_sha256": pcb_hash,
            },
        )

    _write_json(
        root / PATHS["native_status"],
        {
            "schema": "ALTIUM-NATIVE-STATUS-SYS-001",
            "equivalence_gate_status": "PASS",
            "layout_authority": "AUTHORIZED",
            "production_authority": (
                "AUTHORIZED" if production else "NOT_AUTHORIZED"
            ),
        },
    )
    _write_json(
        root / PATHS["implementation_status"],
        {
            "schema": "ALTIUM-PCB-IMPLEMENTATION-STATUS-001",
            "current_phase": (
                "PRODUCTION_RELEASED" if production else "READY_FOR_ROUTING"
            ),
            "altium": {
                "equivalence_gate": True,
                "production_release_authorized": production,
            },
            "routing_readiness": {
                "expected_status": "READY_FOR_ROUTING",
                "routing_authorized": True,
                "required_to_authorize": [],
            },
        },
    )
    _write_json(
        root / PATHS["cad_authority"],
        {
            "schema": "SYSTEM-CARRIER-CAD-AUTHORITY-001",
            "native_document_status": "NATIVE_EQUIVALENCE_PASS",
            "pcb_layout_authority": "ALTIUM_AUTHORIZED",
            "pcb_design_phase": (
                "PRODUCTION_RELEASED"
                if production
                else "ALTIUM_NATIVE_ROUTING"
            ),
            "production_release_authorized": production,
            "routing_readiness_gate": {
                "current_expected_status": "READY_FOR_ROUTING",
            },
        },
    )
    return sch_hash, pcb_hash


def test_reconcile_is_noop_when_authority_is_current(tmp_path):
    _setup_authorized(tmp_path, production=True)

    result = reconcile(repository_root=tmp_path)

    assert result["status"] == "UNCHANGED"
    assert result["actions"] == []
    assert result["layout_authority_effective"] is True
    assert result["production_authority_effective"] is True
    assert result["applied"] is False


def test_reconcile_revokes_layout_and_production_for_stale_schematic(tmp_path):
    _setup_authorized(tmp_path, production=True)
    (tmp_path / PATHS["schematic"]).write_bytes(b"CHANGED_SCHEMATIC")

    result = reconcile(repository_root=tmp_path, apply=True)

    assert result["status"] == "REVOKED"
    assert "REVOKE_LAYOUT_AUTHORITY" in result["actions"]
    assert "REVOKE_PRODUCTION_AUTHORITY" in result["actions"]
    assert result["layout_authority_effective"] is False
    assert result["production_authority_effective"] is False

    native = json.loads(
        (tmp_path / PATHS["native_status"]).read_text()
    )
    assert native["equivalence_gate_status"] == "STALE"
    assert native["layout_authority"] == "NOT_AUTHORIZED"
    assert native["production_authority"] == "NOT_AUTHORIZED"

    implementation = json.loads(
        (tmp_path / PATHS["implementation_status"]).read_text()
    )
    assert implementation["current_phase"] == "EQUIVALENCE_STALE"
    assert implementation["routing_readiness"]["routing_authorized"] is False

    authority = json.loads(
        (tmp_path / PATHS["cad_authority"]).read_text()
    )
    assert authority["pcb_layout_authority"] == "NOT_AUTHORIZED"
    assert authority["production_release_authorized"] is False


def test_reconcile_revokes_only_production_for_stale_pcb(tmp_path):
    _setup_authorized(tmp_path, production=True)
    (tmp_path / PATHS["pcb"]).write_bytes(b"CHANGED_AFTER_RELEASE")

    dry = reconcile(repository_root=tmp_path)

    assert dry["status"] == "REVOCATION_REQUIRED"
    assert dry["actions"] == ["REVOKE_PRODUCTION_AUTHORITY"]
    assert dry["layout_authority_effective"] is True
    assert dry["production_authority_effective"] is False

    result = reconcile(repository_root=tmp_path, apply=True)

    assert result["status"] == "REVOKED"
    native = json.loads(
        (tmp_path / PATHS["native_status"]).read_text()
    )
    assert native["layout_authority"] == "AUTHORIZED"
    assert native["production_authority"] == "NOT_AUTHORIZED"
    assert native["production_release_stale"] is True

    implementation = json.loads(
        (tmp_path / PATHS["implementation_status"]).read_text()
    )
    assert implementation["current_phase"] == "READY_FOR_ROUTING"
    assert implementation["altium"]["equivalence_gate"] is True
    assert implementation["altium"]["production_release_authorized"] is False

    authority = json.loads(
        (tmp_path / PATHS["cad_authority"]).read_text()
    )
    assert authority["pcb_layout_authority"] == "ALTIUM_AUTHORIZED"
    assert authority["production_release_authorized"] is False
    assert authority["pcb_design_phase"] == "ALTIUM_NATIVE_ROUTING"


def test_reconcile_never_grants_authority(tmp_path):
    _setup_authorized(tmp_path, production=False)

    native_path = tmp_path / PATHS["native_status"]
    native = json.loads(native_path.read_text())
    native["layout_authority"] = "NOT_AUTHORIZED"
    _write_json(native_path, native)

    authority_path = tmp_path / PATHS["cad_authority"]
    authority = json.loads(authority_path.read_text())
    authority["pcb_layout_authority"] = "NOT_AUTHORIZED"
    _write_json(authority_path, authority)

    result = reconcile(repository_root=tmp_path, apply=True)

    assert result["status"] == "UNCHANGED"
    assert result["tracked_layout_authority"] is False
    assert result["layout_authority_effective"] is False

    native_after = json.loads(native_path.read_text())
    assert native_after["layout_authority"] == "NOT_AUTHORIZED"
