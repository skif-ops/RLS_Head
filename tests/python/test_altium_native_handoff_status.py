from pathlib import Path

from tools.altium_native_handoff_status import evaluate


def test_native_handoff_initially_waits_for_native_import(tmp_path):
    project = (
        tmp_path
        / "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb"
    )
    project.parent.mkdir(parents=True)
    project.write_text("[Design]\nVersion=1.0\n", encoding="utf-8")

    result = evaluate(tmp_path)

    assert result["schema"] == "ALTIUM-NATIVE-HANDOFF-STATUS-001"
    assert result["status"] == "WAITING_NATIVE_IMPORT"
    assert result["native_files_ready"] is False
    assert result["import_provenance_ready"] is False
    assert result["routing_authorized"] is False
    assert result["production_authorized"] is False


def test_native_handoff_detects_complete_evidence(tmp_path):
    from tools.altium_native_handoff_status import REQUIRED

    for relative in REQUIRED.values():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"TEST")

    result = evaluate(tmp_path)

    assert result["status"] == "READY_TO_RUN_EQUIVALENCE_GATE"
    assert result["native_files_ready"] is True
    assert result["import_provenance_ready"] is True
    assert result["native_audit_ready"] is True
    assert result["equivalence_evidence_complete"] is True



def test_native_handoff_waits_for_import_provenance_after_native_files(tmp_path):
    from tools.altium_native_handoff_status import REQUIRED

    for artifact_id in ("project", "schematic", "pcb"):
        path = tmp_path / REQUIRED[artifact_id]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"TEST")

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_IMPORT_PROVENANCE"
    assert result["native_files_ready"] is True
    assert result["import_provenance_ready"] is False
    assert result["native_audit_ready"] is False
    assert result["next_action"] == "CAPTURE_IMPORT_PACKAGE_LOG_AND_RECEIPT"
