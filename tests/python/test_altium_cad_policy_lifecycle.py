from pathlib import Path

from tools.altium_cad_policy import (
    _native_status_coherence,
    _phase_coherence,
)


def _native_pair(root: Path) -> None:
    native = root / "altium" / "native"
    native.mkdir(parents=True, exist_ok=True)
    (native / "EVT_SYS_CARRIER.SchDoc").write_bytes(b"SCH")
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"PCB")


def test_native_status_coherence_accepts_all_supported_phases():
    cases = [
        (
            "IMPORT_PREPARED",
            {
                "native_import_status": "WAITING_NATIVE_ALTIUM_IMPORT",
                "equivalence_gate_status": "NOT_RUN",
                "layout_authority": "NOT_AUTHORIZED",
                "production_authority": "NOT_AUTHORIZED",
            },
        ),
        (
            "READY_FOR_ROUTING",
            {
                "native_import_status": "NATIVE_FILES_READY",
                "equivalence_gate_status": "PASS",
                "layout_authority": "AUTHORIZED",
                "production_authority": "NOT_AUTHORIZED",
            },
        ),
        (
            "PRODUCTION_RELEASED",
            {
                "native_import_status": "NATIVE_FILES_READY",
                "equivalence_gate_status": "PASS",
                "layout_authority": "AUTHORIZED",
                "production_authority": "AUTHORIZED",
            },
        ),
        (
            "EQUIVALENCE_STALE",
            {
                "native_import_status": "NATIVE_FILES_READY",
                "equivalence_gate_status": "STALE",
                "layout_authority": "NOT_AUTHORIZED",
                "production_authority": "NOT_AUTHORIZED",
            },
        ),
    ]

    for phase, native_status in cases:
        assert _native_status_coherence(
            native_status,
            {"current_phase": phase},
        ) == []


def test_native_status_coherence_rejects_authority_in_stale_phase():
    errors = _native_status_coherence(
        {
            "native_import_status": "NATIVE_FILES_READY",
            "equivalence_gate_status": "STALE",
            "layout_authority": "AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
        },
        {"current_phase": "EQUIVALENCE_STALE"},
    )

    assert "native_layout_authority" in errors


def test_phase_coherence_accepts_safe_reequivalence_required(tmp_path):
    _native_pair(tmp_path)

    authority = {
        "native_document_status": "NATIVE_EQUIVALENCE_STALE",
        "pcb_layout_authority": "NOT_AUTHORIZED",
        "pcb_design_phase": "ALTIUM_REEQUIVALENCE_REQUIRED",
        "production_release_authorized": False,
        "routing_readiness_gate": {
            "current_expected_status": "STALE_EQUIVALENCE",
        },
    }
    status = {
        "current_phase": "EQUIVALENCE_STALE",
        "altium": {
            "native_schdoc": True,
            "native_pcbdoc": True,
            "equivalence_gate": False,
            "production_release_authorized": False,
        },
        "routing_readiness": {
            "expected_status": "STALE_EQUIVALENCE",
            "routing_authorized": False,
        },
    }

    errors, sch, pcb = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert errors == []
    assert sch is True
    assert pcb is True


def test_phase_coherence_accepts_ready_for_routing(tmp_path):
    _native_pair(tmp_path)

    authority = {
        "native_document_status": "NATIVE_EQUIVALENCE_PASS",
        "pcb_layout_authority": "ALTIUM_AUTHORIZED",
        "pcb_design_phase": "ALTIUM_NATIVE_ROUTING",
        "production_release_authorized": False,
        "routing_readiness_gate": {
            "current_expected_status": "READY_FOR_ROUTING",
        },
    }
    status = {
        "current_phase": "READY_FOR_ROUTING",
        "altium": {
            "native_schdoc": True,
            "native_pcbdoc": True,
            "equivalence_gate": True,
            "production_release_authorized": False,
        },
        "routing_readiness": {
            "expected_status": "READY_FOR_ROUTING",
            "routing_authorized": True,
        },
    }

    errors, sch, pcb = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert errors == []
    assert sch is True
    assert pcb is True
