from pathlib import Path

from tools.carrier_design_inputs import validate_design_inputs


def test_fault_inputs_and_can_mode_are_authoritative():
    root = Path("hardware/system_carrier")

    pinmap = (root / "PINMAP_SYS_001.csv").read_text(encoding="utf-8")
    netlist = (root / "NETLIST_SYS_001.csv").read_text(encoding="utf-8")
    components = (root / "SCHEMATIC_COMPONENTS_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    fwio = (root / "FIRMWARE_IO_CONTRACT_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    assert "SYS_EFUSE_FLT,PE2,1,GPIO,GPIO,IN,P0,SYS_EFUSE_FLT" in pinmap
    assert "RADAR_EFUSE_FLT,PE3,2,GPIO,GPIO,IN,P0,RADAR_EFUSE_FLT" in pinmap
    assert "SYS_EFUSE_FLT,U6_FLT" in netlist
    assert "RADAR_EFUSE_FLT,U7_FLT" in netlist
    assert "R_CAN_STB" in components
    assert "R_CAN_SHDN" in components
    assert "SYS_EFUSE_FLT,GPIO_PE2" in fwio
    assert "RADAR_EFUSE_FLT,GPIO_PE3" in fwio

    result = validate_design_inputs(root)
    assert result["status"] == "DESIGN_INPUT_READY"
