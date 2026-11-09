import hashlib
import json
from pathlib import Path

from tools.altium_script_runtime_receipt import (
    CANONICAL,
    OUTPUTS,
    validate,
)


def _write(root: Path, relative: str, data: bytes) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> Path:
    input_hashes = {
        artifact_id: _write(
            tmp_path,
            relative,
            f"INPUT:{artifact_id}".encode(),
        )
        for artifact_id, relative in CANONICAL.items()
    }
    output_hashes = {
        artifact_id: _write(
            tmp_path,
            relative,
            f"OUTPUT:{artifact_id}".encode(),
        )
        for artifact_id, relative in OUTPUTS.items()
    }

    receipt = {
        "schema": "ALTIUM-SCRIPT-RUNTIME-RECEIPT-001",
        "status": "PASS",
        "board_id": "EVT-SYS-CARRIER",
        "altium_version": "26.0.1",
        "operator": "Synthetic CI",
        "procedures": {
            "ExportNativeAudit": {
                "status": "PASS",
                "runtime_errors": 0,
                "runtime_warnings": 0,
            },
            "ExportNativeHierarchy": {
                "status": "PASS",
                "runtime_errors": 0,
                "runtime_warnings": 0,
            },
        },
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
    }
    path = tmp_path / "runtime_receipt.json"
    path.write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_runtime_receipt_passes_exact_bound_evidence(tmp_path):
    receipt = _fixture(tmp_path)

    result = validate(
        receipt_json=receipt,
        repository_root=tmp_path,
    )

    assert result["schema"] == "ALTIUM-SCRIPT-RUNTIME-RESULT-001"
    assert result["status"] == "PASS"
    assert result["runtime_validated"] is True
    assert result["errors"] == []
    assert result["reason_codes"] == []
    assert len(result["receipt_sha256"]) == 64


def test_runtime_receipt_detects_changed_export(tmp_path):
    receipt = _fixture(tmp_path)
    changed = tmp_path / OUTPUTS["pad_net_inventory"]
    changed.write_bytes(b"CHANGED_AFTER_RUNTIME_RECEIPT")

    result = validate(
        receipt_json=receipt,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert result["runtime_validated"] is False
    assert "hash_mismatch:pad_net_inventory" in result["errors"]


def test_runtime_receipt_canonicalizes_script_project_line_endings(tmp_path):
    receipt = _fixture(tmp_path)
    script_project = tmp_path / CANONICAL["script_project"]
    script_project.write_bytes(b"line one\r\nline two\r\n")
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["input_sha256"]["script_project"] = hashlib.sha256(
        b"line one\r\nline two\r\n"
    ).hexdigest()
    receipt.write_text(json.dumps(data), encoding="utf-8")

    crlf_result = validate(
        receipt_json=receipt,
        repository_root=tmp_path,
    )
    script_project.write_bytes(b"line one\nline two\n")
    lf_result = validate(
        receipt_json=receipt,
        repository_root=tmp_path,
    )

    assert crlf_result["status"] == "PASS"
    assert lf_result["status"] == "PASS"


def test_runtime_receipt_requires_both_procedures_pass(tmp_path):
    receipt = _fixture(tmp_path)
    data = json.loads(receipt.read_text())
    data["procedures"]["ExportNativeHierarchy"]["status"] = "FAIL"
    receipt.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate(
        receipt_json=receipt,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert (
        "PROCEDURE_NOT_PASS:ExportNativeHierarchy"
        in result["reason_codes"]
    )
