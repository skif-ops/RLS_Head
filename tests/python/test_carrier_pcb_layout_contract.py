from tools.carrier_pcb_layout_contract import validate


def test_authoritative_layout_contract_passes():
    result = validate(
        "hardware/system_carrier/PCB_LAYOUT_CONSTRAINTS_SYS_001.csv"
    )

    assert result["schema"] == "SYSTEM-CARRIER-PCB-LAYOUT-CONTRACT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["rule_count"] >= 24
    assert result["p0_count"] >= 12
