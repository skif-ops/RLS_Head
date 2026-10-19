import csv
from pathlib import Path

from tools.altium_native_connector_validate import validate


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware" / "system_carrier"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_inventory(path: Path, *, corrupt: bool = False) -> None:
    rows = _rows(SYSTEM / "CONNECTOR_NATIVE_PINMAP_SYS_001.csv")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["designator", "pad_name", "net_name"],
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            net = row["native_net"]
            if corrupt and index == 0:
                net = "WRONG_NET"
            writer.writerow(
                {
                    "designator": row["physical_ref"],
                    "pad_name": row["physical_pad"],
                    "net_name": net,
                }
            )


def test_native_connector_validator_passes_authoritative_fixture(tmp_path):
    path = tmp_path / "pad_net_inventory.csv"
    _write_inventory(path)

    result = validate(system_root=SYSTEM, pad_net_inventory=path)

    assert result["status"] == "PASS"
    assert result["verified_checks"]["connector_pinout_equivalence"] == "PASS"
    assert result["logical_connector_pin_count"] > 0
    assert result["aggregate_logical_pin_count"] == 1
    assert len(result["input_sha256"]["connector_native_map"]) == 64


def test_native_connector_validator_detects_pad_net_mismatch(tmp_path):
    path = tmp_path / "pad_net_inventory.csv"
    _write_inventory(path, corrupt=True)

    result = validate(system_root=SYSTEM, pad_net_inventory=path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("connector_pad_net_mismatch:")
        for item in result["errors"]
    )
