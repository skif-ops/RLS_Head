import hashlib
import json
from pathlib import Path

from tools.altium_native_import_receipt import build_receipt


def _write_package(root: Path) -> Path:
    path = (
        root
        / "hardware/system_carrier/altium/equivalence/"
        "import_package_manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-IMPORT-PACKAGE-001",
                "status": "READY_FOR_ALTIUM_IMPORT",
                "board_id": "EVT-SYS-CARRIER",
                "hardware_revision": "A",
                "source_commit": "1" * 40,
                "source_cad": "KiCad 9 retained verification baseline",
                "target_cad": "Altium Designer",
                "preserve_kicad": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_native(root: Path) -> None:
    files = {
        "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc": b"SCH",
        "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc": b"PCB",
        "hardware/system_carrier/altium/equivalence/import_log.txt": b"IMPORT\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _write_import_preflight(root: Path) -> Path:
    schematic = (
        root
        / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"
    )
    pcb = (
        root
        / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"
    )
    path = (
        root
        / "hardware/system_carrier/altium/equivalence/"
        "import_native_file_preflight.json"
    )
    path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NATIVE-FILE-PREFLIGHT-001",
                "status": "PASS",
                "errors": [],
                "artifacts": {
                    "schematic": {
                        "path": (
                            "hardware/system_carrier/altium/native/"
                            "EVT_SYS_CARRIER.SchDoc"
                        ),
                        "sha256": hashlib.sha256(
                            schematic.read_bytes()
                        ).hexdigest(),
                    },
                    "pcb": {
                        "path": (
                            "hardware/system_carrier/altium/native/"
                            "EVT_SYS_CARRIER.PcbDoc"
                        ),
                        "sha256": hashlib.sha256(
                            pcb.read_bytes()
                        ).hexdigest(),
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_native_import_receipt_binds_package_and_native_files(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        import_preflight=preflight,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["source_commit"] == "1" * 40
    assert result["snapshot_role"] == "POST_IMPORT_NATIVE_SNAPSHOT"
    assert len(result["import_package_manifest"]["sha256"]) == 64
    assert len(result["import_native_file_preflight"]["sha256"]) == 64
    assert set(result["native_artifacts"]) == {
        "schematic",
        "pcb",
        "import_log",
    }
    assert all(
        len(item["sha256"]) == 64
        for item in result["native_artifacts"].values()
    )
    assert result["layout_authority"] == "NOT_AUTHORIZED"


def test_native_import_receipt_requires_tool_versions(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        import_preflight=preflight,
        altium_version="",
        importer_version="",
    )

    assert result["status"] == "FAIL"
    assert "altium_version" in result["errors"]
    assert "importer_version" in result["errors"]



def test_native_import_receipt_rejects_preflight_hash_mismatch(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    pcb = (
        tmp_path
        / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"
    )
    pcb.write_bytes(b"PCB_CHANGED_AFTER_IMPORT_CAPTURE")

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        import_preflight=preflight,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert "import_preflight_hash:pcb" in result["errors"]


def test_native_import_receipt_requires_import_preflight(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        import_preflight=(
            tmp_path
            / "hardware/system_carrier/altium/equivalence/"
            "import_native_file_preflight.json"
        ),
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert "missing_import_native_file_preflight" in result["errors"]
