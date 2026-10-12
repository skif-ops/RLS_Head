from tools.carrier_package_contract import validate_package_contract


def test_authoritative_package_contract_passes():
    result = validate_package_contract("hardware/system_carrier")
    assert result["schema"] == "SYSTEM-CARRIER-PACKAGE-CONTRACT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["contract_count"] >= 11
