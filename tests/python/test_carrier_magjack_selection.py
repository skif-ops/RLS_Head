from tools.carrier_magjack_selection import validate


def test_authoritative_magjack_selection_is_consistent():
    result = validate("hardware/system_carrier")

    assert result["schema"] == "SYSTEM-CARRIER-MAGJACK-SELECTION-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["selected_mpn"] == "SI-60182-F"
    assert result["stock_symbol_id"] == "Connector:RJ45_Bel_SI-60062-F"
    assert (
        result["stock_footprint_id"]
        == "Connector_RJ:RJ45_Bel_SI-60062-F"
    )
