import csv
from pathlib import Path

from tools.altium_native_bom_validate import validate


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware/system_carrier"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_native_bom_validator_passes_authoritative_fixture(tmp_path):
    rows = _rows(SYSTEM / "BOM_SYS_CARRIER_LAYOUT_004.csv")
    path = tmp_path / "bom_export.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Designator", "Manufacturer Part Number"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "Designator": row["ref"],
                "Manufacturer Part Number": row["value_or_mpn"],
            })

    result = validate(system_root=SYSTEM, bom_export=path)

    assert result["status"] == "PASS"
    assert result["verified_checks"]["bom_designator_mpn_equivalence"] == "PASS"
    assert len(result["input_sha256"]["bom_export"]) == 64


def test_native_bom_validator_detects_mpn_mismatch(tmp_path):
    rows = _rows(SYSTEM / "BOM_SYS_CARRIER_LAYOUT_004.csv")
    path = tmp_path / "bom_export.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["designator", "mpn"])
        writer.writeheader()
        for i, row in enumerate(rows):
            writer.writerow({
                "designator": row["ref"],
                "mpn": "WRONG" if i == 0 else row["value_or_mpn"],
            })

    result = validate(system_root=SYSTEM, bom_export=path)

    assert result["status"] == "FAIL"
    assert any(item.startswith("mpn_mismatch:") for item in result["errors"])
