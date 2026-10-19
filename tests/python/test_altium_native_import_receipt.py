import json
from pathlib import Path

from tools.altium_native_import_receipt import NATIVE_ARTIFACTS, build_receipt


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
    for artifact_id, relative in NATIVE_ARTIFACTS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("TEST:" + artifact_id).encode())


def test_native_import_receipt_binds_package_and_native_files(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["source_commit"] == "1" * 40
    assert len(result["import_package_manifest"]["sha256"]) == 64
    assert set(result["native_artifacts"]) == set(NATIVE_ARTIFACTS)
    assert {
        key
        for key in result["native_artifacts"]
        if key.startswith("schematic")
    } == {
        "schematic",
        "schematic_power_input",
        "schematic_mcu_core",
        "schematic_time_gnss",
        "schematic_imu",
        "schematic_radar_io_can",
        "schematic_ethernet",
        "schematic_debug_boot",
    }
    assert all(
        len(item["sha256"]) == 64
        for item in result["native_artifacts"].values()
    )
    assert result["layout_authority"] == "NOT_AUTHORIZED"


def test_native_import_receipt_requires_tool_versions(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        altium_version="",
        importer_version="",
    )

    assert result["status"] == "FAIL"
    assert "altium_version" in result["errors"]
    assert "importer_version" in result["errors"]



def test_native_import_receipt_requires_every_child_schematic(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)
    missing = (
        tmp_path
        / NATIVE_ARTIFACTS["schematic_ethernet"]
    )
    missing.unlink()

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert "missing:schematic_ethernet" in result["errors"]
