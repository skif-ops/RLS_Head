import hashlib
from pathlib import Path

from tools.altium_script_runtime_receipt import CANONICAL, OUTPUTS
from tools.altium_script_runtime_receipt_prepare import prepare


def _populate(root: Path) -> dict[str, bytes]:
    data: dict[str, bytes] = {}
    for artifact_id, relative in {**CANONICAL, **OUTPUTS}.items():
        content = f"DATA:{artifact_id}".encode()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        data[artifact_id] = content
    return data


def test_prepare_builds_pending_receipt_with_exact_hashes(tmp_path):
    data = _populate(tmp_path)

    result = prepare(
        repository_root=tmp_path,
        altium_version="26.0.1",
        operator="Synthetic Operator",
    )

    assert result["status"] == "READY"
    assert result["errors"] == []
    assert result["attestation_required"] is True

    receipt = result["receipt"]
    assert receipt["status"] == "PENDING"
    assert receipt["attestation_required"] is True
    assert receipt["prepared_by"] == (
        "tools.altium_script_runtime_receipt_prepare"
    )
    assert receipt["procedures"]["ExportNativeAudit"]["status"] == "PENDING"
    assert (
        receipt["procedures"]["ExportNativeHierarchy"]["status"]
        == "PENDING"
    )

    for artifact_id in CANONICAL:
        assert receipt["input_sha256"][artifact_id] == hashlib.sha256(
            data[artifact_id]
        ).hexdigest()
    for artifact_id in OUTPUTS:
        assert receipt["output_sha256"][artifact_id] == hashlib.sha256(
            data[artifact_id]
        ).hexdigest()


def test_prepare_never_auto_attests_pass(tmp_path):
    _populate(tmp_path)

    result = prepare(
        repository_root=tmp_path,
        altium_version="26.0.1",
        operator="Synthetic Operator",
    )

    receipt = result["receipt"]
    assert receipt["status"] != "PASS"
    assert all(
        item["status"] != "PASS"
        for item in receipt["procedures"].values()
    )


def test_prepare_refuses_missing_runtime_output(tmp_path):
    _populate(tmp_path)
    (tmp_path / OUTPUTS["hierarchy_export"]).unlink()

    result = prepare(
        repository_root=tmp_path,
        altium_version="26.0.1",
        operator="Synthetic Operator",
    )

    assert result["status"] == "INCOMPLETE"
    assert "missing:hierarchy_export" in result["errors"]
