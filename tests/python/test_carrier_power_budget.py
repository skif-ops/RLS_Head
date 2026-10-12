from tools.carrier_power_budget import evaluate_power_budget


def test_authoritative_power_budget_has_no_overallocation():
    result = evaluate_power_budget(
        "hardware/system_carrier/POWER_BUDGET_SYS_001.csv"
    )

    assert result["schema"] == "SYSTEM-CARRIER-POWER-BUDGET-001"
    assert result["status"] in {"PASS", "WARNING"}
    assert result["errors"] == []

    rail_3v3 = result["rails"]["3V3"]
    assert rail_3v3["allocated_nonreserve"] < rail_3v3["capacity"]
    assert rail_3v3["margin_nonreserve_pct"] > 50.0

    radar = result["rails"]["RADAR_12V"]
    assert radar["allocated_total"] <= radar["capacity"]
    assert radar["margin_total_pct"] < 10.0
    assert "low_total_headroom:RADAR_12V" in result["warnings"]
