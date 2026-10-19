import csv
from pathlib import Path

from tools.altium_native_hierarchy_validate import (
    DIRECTION_MAP,
    ROOT_SCHEMATIC,
    SHEET_TO_FILE,
    validate,
)


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware" / "system_carrier"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path) -> None:
    contract = _rows(SYSTEM / "HIERARCHY_INTERFACE_SYS_001.csv")

    ports = []
    entries = []
    for row in contract:
        child = SHEET_TO_FILE[row["sheet"]]
        io_type = DIRECTION_MAP[row["pin_type"]]
        ports.append(
            {
                "document_file": child,
                "port_name": row["net_name"],
                "io_type": io_type,
            }
        )
        entries.append(
            {
                "parent_document_file": ROOT_SCHEMATIC,
                "child_document_file": child,
                "entry_name": row["net_name"],
                "io_type": io_type,
            }
        )

    _write_csv(
        tmp_path / "hierarchy_port_inventory.csv",
        ["document_file", "port_name", "io_type"],
        ports,
    )
    _write_csv(
        tmp_path / "hierarchy_sheet_entry_inventory.csv",
        [
            "parent_document_file",
            "child_document_file",
            "entry_name",
            "io_type",
        ],
        entries,
    )


def test_native_hierarchy_validator_passes_contract_fixture(tmp_path):
    _fixture(tmp_path)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "PASS"
    assert result["verified_checks"]["hierarchy_equivalence"] == "PASS"
    assert result["expected_child_sheet_count"] == 7
    assert result["native_port_count"] == result["contract_port_count"]
    assert len(result["input_sha256"]["hierarchy_contract"]) == 64


def test_native_hierarchy_validator_detects_wrong_child_link(tmp_path):
    _fixture(tmp_path)

    path = tmp_path / "hierarchy_sheet_entry_inventory.csv"
    rows = _rows(path)
    rows[0]["child_document_file"] = "70_DEBUG_BOOT.SchDoc"
    _write_csv(
        path,
        [
            "parent_document_file",
            "child_document_file",
            "entry_name",
            "io_type",
        ],
        rows,
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("missing_native_sheet_entries:")
        for item in result["errors"]
    )


def test_native_hierarchy_validator_detects_direction_mismatch(tmp_path):
    _fixture(tmp_path)

    path = tmp_path / "hierarchy_port_inventory.csv"
    rows = _rows(path)
    rows[0]["io_type"] = (
        "output"
        if rows[0]["io_type"] != "output"
        else "input"
    )
    _write_csv(
        path,
        ["document_file", "port_name", "io_type"],
        rows,
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("missing_native_ports:")
        for item in result["errors"]
    )
