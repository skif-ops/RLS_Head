from tools.carrier_footprint_readiness import evaluate


def test_authoritative_footprint_plan_is_explicit_but_not_frozen():
    result = evaluate(
        "hardware/system_carrier/FOOTPRINT_PLAN_SYS_001.csv"
    )

    assert result["schema"] == "SYSTEM-CARRIER-FOOTPRINT-READINESS-001"
    assert result["status"] == "FOOTPRINT_PLAN_READY"
    assert result["errors"] == []

    assert "U1" in result["locked_refs"]
    assert "U4" in result["locked_refs"]
    assert "D_CAN" in result["locked_refs"]

    assert "U2" in result["unresolved_refs"]
    assert "U6" in result["unresolved_refs"]
    assert "U8" in result["unresolved_refs"]
