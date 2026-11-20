import csv
from pathlib import Path

from tools.altium_native_netlist_validate import validate


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_native_netlist_validator_ignores_net_name_changes(tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write(
        baseline,
        ["designator", "pin", "net_name"],
        [
            {"designator": "U1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "2", "net_name": "NET_B"},
        ],
    )

    actual = tmp_path / "pad_net_inventory.csv"
    _write(
        actual,
        ["designator", "pad_name", "net_name"],
        [
            {"designator": "U1", "pad_name": "1", "net_name": "Altium_A"},
            {"designator": "R1", "pad_name": "1", "net_name": "Altium_A"},
            {"designator": "R1", "pad_name": "2", "net_name": "Altium_B"},
        ],
    )

    result = validate(
        baseline_csv=baseline,
        pad_net_inventory=actual,
    )

    assert result["status"] == "PASS"
    assert result["verified_checks"]["netlist_equivalence"] == "PASS"


def test_native_netlist_validator_detects_rewired_endpoint(tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write(
        baseline,
        ["designator", "pin", "net_name"],
        [
            {"designator": "U1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "2", "net_name": "NET_B"},
        ],
    )

    actual = tmp_path / "pad_net_inventory.csv"
    _write(
        actual,
        ["designator", "pad_name", "net_name"],
        [
            {"designator": "U1", "pad_name": "1", "net_name": "Altium_A"},
            {"designator": "R1", "pad_name": "1", "net_name": "Altium_B"},
            {"designator": "R1", "pad_name": "2", "net_name": "Altium_B"},
        ],
    )

    result = validate(
        baseline_csv=baseline,
        pad_net_inventory=actual,
    )

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("missing_connectivity_groups:")
        for item in result["errors"]
    )


def test_native_netlist_validator_excludes_only_explicit_unconnected_pins(tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write(
        baseline,
        ["designator", "pin", "net_name"],
        [
            {"designator": "U1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "1", "net_name": "NET_A"},
            {"designator": "U1", "pin": "2", "net_name": "unconnected-(U1-NC-Pad2)"},
        ],
    )
    actual = tmp_path / "pad_net_inventory.csv"
    _write(
        actual,
        ["designator", "pad_name", "net_name"],
        [
            {"designator": "U1", "pad_name": "1", "net_name": "Altium_A"},
            {"designator": "R1", "pad_name": "1", "net_name": "Altium_A"},
        ],
    )
    assert validate(baseline_csv=baseline, pad_net_inventory=actual)["status"] == "PASS"

    _write(
        baseline,
        ["designator", "pin", "net_name"],
        [
            {"designator": "U1", "pin": "1", "net_name": "NET_A"},
            {"designator": "R1", "pin": "1", "net_name": "NET_A"},
            {"designator": "U1", "pin": "2", "net_name": "NAMED_SINGLETON"},
        ],
    )
    assert validate(baseline_csv=baseline, pad_net_inventory=actual)["status"] == "FAIL"
