from pathlib import Path

from tools.carrier_design_inputs import (
    validate_bom,
    validate_clock_tree,
    validate_design_inputs,
    validate_netlist,
    validate_pinmap,
    validate_power_tree,
)


ROOT = Path("hardware/system_carrier")


def test_authoritative_design_inputs_ready():
    result = validate_design_inputs(ROOT)

    assert result["schema"] == "CARRIER-DESIGN-INPUTS-001"
    assert result["status"] == "DESIGN_INPUT_READY"
    assert result["failed_components"] == []
    assert result["bom"]["status"] == "PASS"
    assert result["pinmap"]["status"] == "PASS"
    assert result["clock_tree"]["status"] == "PASS"
    assert result["power_tree"]["status"] == "PASS"
    assert result["netlist"]["status"] == "PASS"


def test_pinmap_duplicate_pin_fails(tmp_path):
    source = (ROOT / "PINMAP_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    path = tmp_path / "pinmap.csv"
    path.write_text(
        source
        + "EXTRA,PA0,40,GPIO,SYS,IN,P1,EXTRA\n",
        encoding="utf-8",
    )

    result = validate_pinmap(path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("duplicate_mcu_pin:PA0")
        for item in result["findings"]
    )


def test_bom_missing_required_part_fails(tmp_path):
    source = (ROOT / "BOM_SYS_CARRIER_002.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if "ICM-42688-P" not in line
    ]

    path = tmp_path / "bom.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_bom(path)

    assert result["status"] == "FAIL"
    assert "ICM-42688-P" in result["missing_mpns"]


def test_clock_tree_requires_both_eth_targets(tmp_path):
    source = (ROOT / "CLOCK_TREE_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if "LAN8742A_REF_CLK" not in line
    ]

    path = tmp_path / "clock.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_clock_tree(path)

    assert result["status"] == "FAIL"
    assert "eth_50m_target:LAN8742A_REF_CLK" in result["findings"]


def test_power_tree_requires_protection_chain(tmp_path):
    source = (ROOT / "POWER_TREE_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if "TPS259470ARPWR" not in line
    ]

    path = tmp_path / "power.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_power_tree(path)

    assert result["status"] == "FAIL"
    assert "missing_device:TPS259470ARPWR" in result["findings"]
    assert any(
        item.startswith("missing_transition:VIN_TVS")
        for item in result["findings"]
    )


def test_netlist_missing_critical_net_fails(tmp_path):
    source = (ROOT / "NETLIST_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if not line.startswith("RADAR_REF,")
    ]

    path = tmp_path / "netlist.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_netlist(
        path,
        ROOT / "PINMAP_SYS_001.csv",
    )

    assert result["status"] == "FAIL"
    assert "missing_net:RADAR_REF" in result["findings"]
    assert "pinmap_net_missing:RADAR_REF" in result["findings"]
