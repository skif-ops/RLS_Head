import hashlib
import json
from pathlib import Path

from tools.altium_import_source_binding import validate


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_fixture(root: Path, *, current: bytes = b"BOUND\n") -> Path:
    repo_path = (
        root
        / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.write_bytes(current)

    package_bytes = b"BOUND\n"
    manifest = {
        "schema": "ALTIUM-IMPORT-PACKAGE-001",
        "status": "READY_FOR_ALTIUM_IMPORT",
        "source_commit": "1" * 40,
        "current_source_binding_required": True,
        "file_count": 1,
        "files": [
            {
                "path": "contracts/BOM_SYS_CARRIER_LAYOUT_004.csv",
                "size": len(package_bytes),
                "sha256": _sha(package_bytes),
            }
        ],
        "source_binding_count": 1,
        "source_bindings": [
            {
                "package_path": (
                    "contracts/BOM_SYS_CARRIER_LAYOUT_004.csv"
                ),
                "repository_path": (
                    "hardware/system_carrier/"
                    "BOM_SYS_CARRIER_LAYOUT_004.csv"
                ),
            }
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def test_import_source_binding_passes_current_checkout(tmp_path):
    manifest = _write_fixture(tmp_path)

    result = validate(
        package_manifest=manifest,
        repository_root=tmp_path,
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["checked_count"] == 1
    assert result["expected_count"] == 1
    assert result["bindings"][0]["match"] is True


def test_import_source_binding_rejects_stale_checkout(tmp_path):
    manifest = _write_fixture(tmp_path, current=b"CHANGED\n")

    result = validate(
        package_manifest=manifest,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert (
        "source_binding_hash:"
        "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
        in result["errors"]
    )


def test_import_source_binding_rejects_missing_bound_file(tmp_path):
    manifest = _write_fixture(tmp_path)
    (
        tmp_path
        / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
    ).unlink()

    result = validate(
        package_manifest=manifest,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("source_binding_missing_repository_file:")
        for item in result["errors"]
    )
