import csv
from pathlib import Path

from tools.altium_native_footprint_validate import validate


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware/system_carrier"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_native_footprint_validator_passes_authoritative_fixture(tmp_path):
    rows = _rows(SYSTEM / "FOOTPRINT_ASSIGNMENT_SYS_002.csv")
    path = tmp_path / "component_inventory.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["designator", "pattern", "x_mil", "y_mil"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "designator": row["ref"],
                "pattern": row["footprint_id"].split(":")[-1],
                "x_mil": "0",
                "y_mil": "0",
            })

    result = validate(system_root=SYSTEM, component_inventory=path)

    assert result["status"] == "PASS"
    assert result["verified_checks"]["footprint_equivalence"] == "PASS"
    assert len(result["input_sha256"]["component_inventory"]) == 64


def test_native_footprint_validator_detects_pattern_mismatch(tmp_path):
    rows = _rows(SYSTEM / "FOOTPRINT_ASSIGNMENT_SYS_002.csv")
    path = tmp_path / "component_inventory.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["designator", "pattern", "x_mil", "y_mil"])
        writer.writeheader()
        for i, row in enumerate(rows):
            writer.writerow({
                "designator": row["ref"],
                "pattern": "WRONG" if i == 0 else row["footprint_id"].split(":")[-1],
                "x_mil": "0",
                "y_mil": "0",
            })

    result = validate(system_root=SYSTEM, component_inventory=path)

    assert result["status"] == "FAIL"
    assert any(item.startswith("footprint_mismatch:") for item in result["errors"])
