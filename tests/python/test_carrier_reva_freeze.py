from tools.carrier_reva_freeze import validate_freeze


def test_authoritative_carrier_freeze_passes():
    result = validate_freeze("hardware/system_carrier")
    assert result["schema"] == "SYSTEM-CARRIER-REVA-FREEZE-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
