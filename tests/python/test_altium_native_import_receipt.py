import hashlib
import json
from pathlib import Path

from tools.altium_native_import_receipt import build_receipt


def _write_package(root: Path) -> Path:
    bound_data = b"BOUND\n"
    bound_path = (
        root
        / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    bound_path.parent.mkdir(parents=True, exist_ok=True)
    bound_path.write_bytes(bound_data)

    package_record = {
        "path": "contracts/BOM_SYS_CARRIER_LAYOUT_004.csv",
        "size": len(bound_data),
        "sha256": hashlib.sha256(bound_data).hexdigest(),
    }
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
                "current_source_binding_required": True,
                "source_binding_count": 1,
                "source_bindings": [
                    {
                        "package_path": package_record["path"],
                        "repository_path": (
                            "hardware/system_carrier/"
                            "BOM_SYS_CARRIER_LAYOUT_004.csv"
                        ),
                    }
                ],
                "file_count": 1,
                "files": [package_record],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_package_verification(root: Path, package: Path) -> Path:
    path = (
        root
        / "hardware/system_carrier/altium/equivalence/"
        "import_package_verification.json"
    )
    package_data = json.loads(package.read_text(encoding="utf-8"))
    payload = {
        "schema": "ALTIUM-IMPORT-PACKAGE-VERIFY-001",
        "status": "PASS",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "source_commit": "1" * 40,
        "package_manifest": {
            "path": "manifest.json",
            "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        },
        "expected_file_count": 1,
        "verified_file_count": 1,
        "verified_files": package_data["files"],
        "source_binding_count": 1,
        "errors": [],
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
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
    verification = _write_package_verification(tmp_path, package)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        package_verification=verification,
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
    assert result["import_source_binding"]["status"] == "PASS"
    assert result["import_source_binding"]["checked_count"] == 1
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
    verification = _write_package_verification(tmp_path, package)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        package_verification=verification,
        import_preflight=preflight,
        altium_version="",
        importer_version="",
    )

    assert result["status"] == "FAIL"
    assert "altium_version" in result["errors"]
    assert "importer_version" in result["errors"]



def test_native_import_receipt_rejects_preflight_hash_mismatch(tmp_path):
    package = _write_package(tmp_path)
    verification = _write_package_verification(tmp_path, package)
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
        package_verification=verification,
        import_preflight=preflight,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert "import_preflight_hash:pcb" in result["errors"]


def test_native_import_receipt_requires_import_preflight(tmp_path):
    package = _write_package(tmp_path)
    verification = _write_package_verification(tmp_path, package)
    _write_native(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        package_verification=verification,
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


def test_native_import_receipt_requires_package_verification(tmp_path):
    package = _write_package(tmp_path)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        package_verification=(
            tmp_path
            / "hardware/system_carrier/altium/equivalence/"
            "import_package_verification.json"
        ),
        import_preflight=preflight,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert "missing_import_package_verification" in result["errors"]


def test_native_import_receipt_rejects_stale_bound_source(tmp_path):
    package = _write_package(tmp_path)
    verification = _write_package_verification(tmp_path, package)
    _write_native(tmp_path)
    preflight = _write_import_preflight(tmp_path)

    bound_path = (
        tmp_path
        / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    bound_path.write_bytes(b"CHANGED_AFTER_PACKAGE\n")

    result = build_receipt(
        repository_root=tmp_path,
        package_manifest=package,
        package_verification=verification,
        import_preflight=preflight,
        altium_version="26.0.1",
        importer_version="KiCad Importer 26.0.1",
    )

    assert result["status"] == "FAIL"
    assert result["import_source_binding"]["status"] == "FAIL"
    assert any(
        item.startswith(
            "import_source_binding:source_binding_hash:"
        )
        for item in result["errors"]
    )
