from pathlib import Path

from tools.carrier_design_inputs import (
    validate_bom,
    validate_clock_tree,
    validate_design_inputs,
    validate_netlist,
    validate_pinmap,
    validate_power_tree,
    validate_radar_interface,
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
    assert result["radar_interface"]["status"] == "PASS"


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
    source = (ROOT / "BOM_SYS_CARRIER_003.csv").read_text(
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


def test_clock_tree_requires_gnss_pps(tmp_path):
    source = (ROOT / "CLOCK_TREE_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if not line.startswith("GNSS_PPS,")
    ]

    path = tmp_path / "clock.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_clock_tree(path)

    assert result["status"] == "FAIL"
    assert "missing_clock:GNSS_PPS" in result["findings"]


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
        item.startswith("missing_transition:VIN_RAW->VIN_PROTECTED")
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


def test_bom_requires_selected_gnss_and_radar_connectors(tmp_path):
    source = (ROOT / "BOM_SYS_CARRIER_003.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if "SM06B-GHS-TB(LF)(SN)" not in line
    ]

    path = tmp_path / "bom.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_bom(path)

    assert result["status"] == "FAIL"
    assert "SM06B-GHS-TB(LF)(SN)" in result["missing_mpns"]
    assert "J8:SM06B-GHS-TB(LF)(SN)" in result["missing_refs"]


def test_power_tree_requires_radar_branch(tmp_path):
    source = (ROOT / "POWER_TREE_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if ",RADAR_12V," not in line
    ]

    path = tmp_path / "power.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_power_tree(path)

    assert result["status"] == "FAIL"
    assert (
        "missing_transition:VIN_PROTECTED->RADAR_12V"
        in result["findings"]
    )


def test_netlist_requires_radar_can_bus(tmp_path):
    source = (ROOT / "NETLIST_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    lines = [
        line
        for line in source.splitlines()
        if not line.startswith("RADAR_CANH,")
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
    assert "missing_net:RADAR_CANH" in result["findings"]


def test_radar_interface_requires_ref_and_can(tmp_path):
    source = (
        ROOT / "RADAR_INTERFACE_SYS_001.csv"
    ).read_text(encoding="utf-8")

    lines = [
        line
        for line in source.splitlines()
        if not line.startswith("RADAR_REF,")
    ]

    path = tmp_path / "radar_interface.csv"
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    result = validate_radar_interface(path)

    assert result["status"] == "FAIL"
    assert (
        "missing_signal:RADAR_REF"
        in result["findings"]
    )


def test_bom_requires_fixed_3v3_regulator(tmp_path):
    source = (ROOT / "BOM_SYS_CARRIER_003.csv").read_text(
        encoding="utf-8"
    )
    path = tmp_path / "bom.csv"
    path.write_text(
        source.replace("TPS62132RGTR", "TPS62130ARGTR"),
        encoding="utf-8",
    )
    result = validate_bom(path)
    assert result["status"] == "FAIL"
    assert "TPS62132RGTR" in result["missing_mpns"]


def test_bom_requires_external_gnss_esd(tmp_path):
    source = (ROOT / "BOM_SYS_CARRIER_003.csv").read_text(
        encoding="utf-8"
    )
    lines = [
        line
        for line in source.splitlines()
        if not line.startswith("D8,")
    ]
    path = tmp_path / "bom.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = validate_bom(path)
    assert result["status"] == "FAIL"
    assert "D8:TPD4E05U06DQAR" in result["missing_refs"]


def test_bom_requires_fixed_5v_external_gnss_regulator(tmp_path):
    source = (ROOT / "BOM_SYS_CARRIER_003.csv").read_text(
        encoding="utf-8"
    )
    path = tmp_path / "bom.csv"
    path.write_text(
        source.replace("TPS62133RGTR", "TPS62130ARGTR"),
        encoding="utf-8",
    )
    result = validate_bom(path)
    assert result["status"] == "FAIL"
    assert "TPS62133RGTR" in result["missing_mpns"]
    assert "U9:TPS62133RGTR" in result["missing_refs"]
