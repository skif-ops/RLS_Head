import csv
from pathlib import Path

from tools.altium_native_hierarchy_validate import validate


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_hierarchy_validator_passes_matching_native_export(tmp_path):
    system = tmp_path / "hardware/system_carrier"
    system.mkdir(parents=True)
    contract = system / "HIERARCHY_INTERFACE_SYS_001.csv"
    _write(
        contract,
        [
            "sheet",
            "net_name",
            "pin_type",
            "anchor_ref",
            "anchor_pin",
            "criticality",
            "notes",
        ],
        [
            {
                "sheet": "MCU_CORE",
                "net_name": "GNSS_PPS",
                "pin_type": "input",
                "anchor_ref": "U1",
                "anchor_pin": "40",
                "criticality": "P0",
                "notes": "",
            }
        ],
    )
    export = tmp_path / "hierarchy_export.csv"
    _write(
        export,
        ["sheet", "net_name", "pin_type", "anchor_ref", "anchor_pin"],
        [
            {
                "sheet": "MCU_CORE",
                "net_name": "GNSS_PPS",
                "pin_type": "IN",
                "anchor_ref": "U1",
                "anchor_pin": "40",
            }
        ],
    )

    pad = tmp_path / "pad_net_inventory.csv"
    _write(
        pad,
        ["designator", "pad_name", "net_name"],
        [
            {
                "designator": "U1",
                "pad_name": "40",
                "net_name": "GNSS_PPS",
            }
        ],
    )

    result = validate(
        system_root=system,
        hierarchy_export=export,
        pad_net_inventory=pad,
    )

    assert result["status"] == "PASS"
    assert result["verified_checks"]["hierarchy_equivalence"] == "PASS"


def test_hierarchy_validator_detects_direction_mismatch(tmp_path):
    system = tmp_path / "hardware/system_carrier"
    system.mkdir(parents=True)
    contract = system / "HIERARCHY_INTERFACE_SYS_001.csv"
    _write(
        contract,
        [
            "sheet",
            "net_name",
            "pin_type",
            "anchor_ref",
            "anchor_pin",
            "criticality",
            "notes",
        ],
        [
            {
                "sheet": "POWER_INPUT",
                "net_name": "3V3",
                "pin_type": "output",
                "anchor_ref": "L1",
                "anchor_pin": "2",
                "criticality": "P0",
                "notes": "",
            }
        ],
    )
    export = tmp_path / "hierarchy_export.csv"
    _write(
        export,
        ["sheet", "net_name", "pin_type", "anchor_ref", "anchor_pin"],
        [
            {
                "sheet": "POWER_INPUT",
                "net_name": "3V3",
                "pin_type": "input",
                "anchor_ref": "L1",
                "anchor_pin": "2",
            }
        ],
    )

    pad = tmp_path / "pad_net_inventory.csv"
    _write(
        pad,
        ["designator", "pad_name", "net_name"],
        [
            {
                "designator": "L1",
                "pad_name": "2",
                "net_name": "3V3",
            }
        ],
    )

    result = validate(
        system_root=system,
        hierarchy_export=export,
        pad_net_inventory=pad,
    )

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("pin_type_mismatch:")
        for item in result["errors"]
    )



def test_hierarchy_validator_detects_anchor_net_mismatch(tmp_path):
    system = tmp_path / "hardware/system_carrier"
    system.mkdir(parents=True)
    contract = system / "HIERARCHY_INTERFACE_SYS_001.csv"
    _write(
        contract,
        [
            "sheet",
            "net_name",
            "pin_type",
            "anchor_ref",
            "anchor_pin",
            "criticality",
            "notes",
        ],
        [
            {
                "sheet": "MCU_CORE",
                "net_name": "GNSS_PPS",
                "pin_type": "input",
                "anchor_ref": "U1",
                "anchor_pin": "40",
                "criticality": "P0",
                "notes": "",
            }
        ],
    )
    export = tmp_path / "hierarchy_export.csv"
    _write(
        export,
        ["sheet", "net_name", "pin_type"],
        [
            {
                "sheet": "MCU_CORE",
                "net_name": "GNSS_PPS",
                "pin_type": "input",
            }
        ],
    )
    pad = tmp_path / "pad_net_inventory.csv"
    _write(
        pad,
        ["designator", "pad_name", "net_name"],
        [
            {
                "designator": "U1",
                "pad_name": "40",
                "net_name": "WRONG_NET",
            }
        ],
    )

    result = validate(
        system_root=system,
        hierarchy_export=export,
        pad_net_inventory=pad,
    )

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("anchor_net_mismatch:")
        for item in result["errors"]
    )
