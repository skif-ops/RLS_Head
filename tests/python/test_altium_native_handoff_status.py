import json
from pathlib import Path

from tools.altium_equivalence_gate import REQUIRED_CHECKS
from tools.altium_native_handoff_status import REQUIRED, evaluate


def _write_all_evidence(tmp_path: Path, *, check_value: str = "PASS") -> None:
    for artifact_id, relative in REQUIRED.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if artifact_id == "manifest":
            path.write_text(
                json.dumps(
                    {
                        "checks": {
                            name: check_value
                            for name in REQUIRED_CHECKS
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            path.write_bytes(b"TEST")


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
    assert result["native_file_preflight_ready"] is False
    assert result["import_provenance_ready"] is False
    assert result["semantic_checks_ready"] is False
    assert result["routing_authorized"] is False
    assert result["production_authorized"] is False


def test_native_handoff_detects_complete_evidence_and_checks(tmp_path):
    _write_all_evidence(tmp_path)

    result = evaluate(tmp_path)

    assert result["status"] == "READY_TO_RUN_EQUIVALENCE_GATE"
    assert result["native_files_ready"] is True
    assert result["native_file_preflight_ready"] is True
    assert result["import_provenance_ready"] is True
    assert result["native_audit_ready"] is True
    assert result["script_runtime_ready"] is True
    assert result["equivalence_evidence_complete"] is True
    assert result["semantic_checks_ready"] is True
    assert result["pending_equivalence_checks"] == []


def test_native_handoff_waits_for_native_file_preflight(tmp_path):
    for artifact_id in ("project", "schematic", "pcb"):
        path = tmp_path / REQUIRED[artifact_id]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"TEST")

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_NATIVE_FILE_PREFLIGHT"
    assert result["native_files_ready"] is True
    assert result["native_file_preflight_ready"] is False
    assert result["next_action"] == "RUN_NATIVE_ALTIUM_FILE_PREFLIGHT"


def test_native_handoff_waits_for_import_provenance_after_preflight(tmp_path):
    for artifact_id in (
        "project",
        "schematic",
        "pcb",
        "native_file_preflight",
    ):
        path = tmp_path / REQUIRED[artifact_id]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"TEST")

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_IMPORT_PROVENANCE"
    assert result["native_files_ready"] is True
    assert result["native_file_preflight_ready"] is True
    assert result["import_provenance_ready"] is False
    assert result["native_audit_ready"] is False
    assert result["next_action"] == "CAPTURE_IMPORT_PACKAGE_LOG_AND_RECEIPT"


def test_native_handoff_waits_for_semantic_checks(tmp_path):
    _write_all_evidence(tmp_path, check_value="PENDING")

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_EQUIVALENCE_CHECKS"
    assert result["equivalence_evidence_complete"] is True
    assert result["semantic_checks_ready"] is False
    assert set(result["pending_equivalence_checks"]) == REQUIRED_CHECKS
    assert result["next_action"] == "COMPLETE_REMAINING_EQUIVALENCE_CHECKS"


def test_native_handoff_rejects_invalid_manifest(tmp_path):
    _write_all_evidence(tmp_path)
    manifest = tmp_path / REQUIRED["manifest"]
    manifest.write_text("{not-json", encoding="utf-8")

    result = evaluate(tmp_path)

    assert result["status"] == "INVALID_EQUIVALENCE_MANIFEST"
    assert result["semantic_checks_ready"] is False
    assert result["manifest_errors"]
    assert result["next_action"] == "FIX_EQUIVALENCE_MANIFEST"



def test_native_handoff_waits_for_script_runtime_receipt(tmp_path):
    # All required artifacts except the two explicit runtime-evidence files.
    for artifact_id, relative in REQUIRED.items():
        if artifact_id in {
            "script_runtime_receipt",
            "script_runtime_result",
        }:
            continue
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if artifact_id == "manifest":
            path.write_text(
                json.dumps(
                    {
                        "checks": {
                            name: "PASS"
                            for name in REQUIRED_CHECKS
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            path.write_bytes(b"TEST")

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_SCRIPT_RUNTIME_RECEIPT"
    assert result["native_audit_ready"] is True
    assert result["script_runtime_ready"] is False
    assert result["routing_authorized"] is False
    assert (
        result["next_action"]
        == "RECORD_ALTIUM_SCRIPT_RUNTIME_RECEIPT"
    )
