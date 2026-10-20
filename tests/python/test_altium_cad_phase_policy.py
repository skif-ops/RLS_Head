from pathlib import Path

from tools.altium_cad_policy import _phase_coherence


def test_phase_coherence_accepts_pre_import_state(tmp_path: Path):
    authority = {
        "native_document_status": "PENDING_ALTIUM_IMPORT",
        "pcb_layout_authority": "ALTIUM_AFTER_EQUIVALENCE_GATE",
        "production_release_authorized": False,
        "routing_readiness_gate": {
            "current_expected_status": "READY_FOR_NATIVE_IMPORT",
        },
    }
    status = {
        "current_phase": "IMPORT_PREPARED",
        "altium": {
            "production_release_authorized": False,
        },
        "routing_readiness": {
            "expected_status": "READY_FOR_NATIVE_IMPORT",
            "routing_authorized": False,
        },
    }

    errors, native_schdoc, native_pcbdoc = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert errors == []
    assert native_schdoc is False
    assert native_pcbdoc is False


def test_phase_coherence_accepts_post_equivalence_state(tmp_path: Path):
    native = tmp_path / "altium/native"
    native.mkdir(parents=True)
    (native / "EVT_SYS_CARRIER.SchDoc").write_bytes(b"SCH")
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"PCB")

    authority = {
        "native_document_status": "NATIVE_EQUIVALENCE_PASS",
        "pcb_layout_authority": "ALTIUM_AUTHORIZED",
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

    errors, native_schdoc, native_pcbdoc = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert errors == []
    assert native_schdoc is True
    assert native_pcbdoc is True


def test_phase_coherence_rejects_native_pair_with_pre_import_status(
    tmp_path: Path,
):
    native = tmp_path / "altium/native"
    native.mkdir(parents=True)
    (native / "EVT_SYS_CARRIER.SchDoc").write_bytes(b"SCH")
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"PCB")

    authority = {
        "native_document_status": "PENDING_ALTIUM_IMPORT",
        "pcb_layout_authority": "ALTIUM_AFTER_EQUIVALENCE_GATE",
        "production_release_authorized": False,
        "routing_readiness_gate": {
            "current_expected_status": "READY_FOR_NATIVE_IMPORT",
        },
    }
    status = {
        "current_phase": "IMPORT_PREPARED",
        "altium": {
            "native_schdoc": False,
            "native_pcbdoc": False,
            "equivalence_gate": False,
            "production_release_authorized": False,
        },
        "routing_readiness": {
            "expected_status": "READY_FOR_NATIVE_IMPORT",
            "routing_authorized": False,
        },
    }

    errors, _, _ = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert "altium_status_phase" in errors
    assert "altium_status_native_schdoc" in errors
    assert "altium_status_native_pcbdoc" in errors
    assert "authority_native_document_status" in errors
    assert "authority_layout_authority" in errors
    assert "authority_routing_status" in errors



def test_phase_coherence_accepts_production_released_state(tmp_path: Path):
    native = tmp_path / "altium/native"
    native.mkdir(parents=True)
    (native / "EVT_SYS_CARRIER.SchDoc").write_bytes(b"SCH")
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"PCB")

    authority = {
        "native_document_status": "NATIVE_EQUIVALENCE_PASS",
        "pcb_layout_authority": "ALTIUM_AUTHORIZED",
        "pcb_design_phase": "PRODUCTION_RELEASED",
        "production_release_authorized": True,
        "routing_readiness_gate": {
            "current_expected_status": "READY_FOR_ROUTING",
        },
    }
    status = {
        "current_phase": "PRODUCTION_RELEASED",
        "altium": {
            "native_schdoc": True,
            "native_pcbdoc": True,
            "equivalence_gate": True,
            "placement_started": True,
            "routing_started": True,
            "production_release_authorized": True,
        },
        "routing_readiness": {
            "expected_status": "READY_FOR_ROUTING",
            "routing_authorized": True,
        },
    }

    errors, native_schdoc, native_pcbdoc = _phase_coherence(
        tmp_path,
        authority,
        status,
    )

    assert errors == []
    assert native_schdoc is True
    assert native_pcbdoc is True
