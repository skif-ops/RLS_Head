from pathlib import Path

from tools.carrier_design_inputs import validate_design_inputs


def test_ethernet_reset_is_locked():
    root = Path("hardware/system_carrier")
    pinmap = (root / "PINMAP_SYS_001.csv").read_text(encoding="utf-8")
    netlist = (root / "NETLIST_SYS_001.csv").read_text(encoding="utf-8")
    components = (root / "SCHEMATIC_COMPONENTS_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    fwio = (root / "FIRMWARE_IO_CONTRACT_SYS_001.csv").read_text(
        encoding="utf-8"
    )

    assert "ETH_NRST,PE4,3,GPIO,GPIO,OUT,P1,ETH_NRST" in pinmap
    assert "ETH_NRST,U1_PE4;U3_nRST;R_ETH_NRST_PD" in netlist
    assert "R_ETH_NRST_PD" in components
    assert "ETH_NRST,GPIO_PE4,push_pull_output" in fwio

    result = validate_design_inputs(root)
    assert result["status"] == "DESIGN_INPUT_READY"
