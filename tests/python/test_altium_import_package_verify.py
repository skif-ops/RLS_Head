import hashlib
import json
from pathlib import Path

from tools.altium_import_package_verify import verify


def _write_package(root: Path) -> None:
    files = {
        "kicad_source/EVT_SYS_CARRIER.kicad_pro": b"PROJECT\n",
        "evidence/kicad_netlist_baseline.csv": (
            b"designator,pin,net_name\nU1,1,3V3\n"
        ),
    }
    records = []
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )

    manifest = {
        "schema": "ALTIUM-IMPORT-PACKAGE-001",
        "status": "READY_FOR_ALTIUM_IMPORT",
        "path_mode": "PACKAGE_ROOT_RELATIVE",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "source_commit": "1" * 40,
        "file_count": len(records),
        "files": records,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_import_package_verify_passes_exact_package(tmp_path):
    _write_package(tmp_path)

    result = verify(package_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["expected_file_count"] == 2
    assert result["verified_file_count"] == 2
    assert len(result["package_manifest"]["sha256"]) == 64


def test_import_package_verify_rejects_changed_file(tmp_path):
    _write_package(tmp_path)
    target = tmp_path / "kicad_source/EVT_SYS_CARRIER.kicad_pro"
    target.write_bytes(b"CHANGED\n")

    result = verify(package_root=tmp_path)

    assert result["status"] == "FAIL"
    assert (
        "sha256_mismatch:kicad_source/EVT_SYS_CARRIER.kicad_pro"
        in result["errors"]
    )


def test_import_package_verify_rejects_path_escape(tmp_path):
    _write_package(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.bin"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = verify(package_root=tmp_path)

    assert result["status"] == "FAIL"
    assert "unsafe_path:../outside.bin" in result["errors"]
