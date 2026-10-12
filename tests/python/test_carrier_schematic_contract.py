from pathlib import Path

from tools.carrier_schematic_contract import (
    validate_blocks,
    validate_components,
    validate_connectors,
    validate_contract,
    validate_power_budget,
)


ROOT = Path("hardware/system_carrier")


def test_authoritative_schematic_contract_ready():
    result = validate_contract(ROOT)

    assert result["schema"] == "CARRIER-SCHEMATIC-CONTRACT-001"
    assert result["status"] == "SCHEMATIC_CAPTURE_READY"
    assert result["failed_sections"] == []
    assert result["blocks"]["status"] == "PASS"
    assert result["components"]["status"] == "PASS"
    assert result["connectors"]["status"] == "PASS"
    assert result["power_budget"]["status"] == "PASS"


def test_missing_sheet_fails(tmp_path):
    source = (ROOT / "SCHEMATIC_BLOCKS_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    lines = [
        line for line in source.splitlines()
        if not line.startswith("50,")
    ]
    path = tmp_path / "blocks.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_blocks(path)
    assert result["status"] == "FAIL"
    assert "missing_block:50" in result["findings"]


def test_wrong_vcap_value_fails(tmp_path):
    source = (ROOT / "SCHEMATIC_COMPONENTS_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    path = tmp_path / "components.csv"
    path.write_text(
        source.replace(
            "2.2uF X7R ESR_lt_100mR",
            "100nF X7R",
        ),
        encoding="utf-8",
    )

    result = validate_components(path)
    assert result["status"] == "FAIL"
    assert any(
        item.startswith("component_value:C_VCAP1;C_VCAP2")
        for item in result["findings"]
    )


def test_missing_radar_ref_connector_fails(tmp_path):
    source = (ROOT / "CONNECTOR_PINOUT_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    lines = [
        line for line in source.splitlines()
        if ",RADAR_REF," not in line
    ]
    path = tmp_path / "connectors.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_connectors(path)
    assert result["status"] == "FAIL"
    assert (
        "missing_connector_signal:J_RADAR_IO:RADAR_REF"
        in result["findings"]
    )


def test_over_budget_3v3_fails(tmp_path):
    source = (ROOT / "POWER_BUDGET_SYS_001.csv").read_text(
        encoding="utf-8"
    )
    path = tmp_path / "budget.csv"
    path.write_text(
        source.replace(
            "3V3,U5 TPS62132,3.0,reserve,1.50",
            "3V3,U5 TPS62132,3.0,reserve,2.50",
        ),
        encoding="utf-8",
    )

    result = validate_power_budget(path)
    assert result["status"] == "FAIL"
    assert any(
        item.startswith("over_budget:3V3:")
        for item in result["findings"]
    )
