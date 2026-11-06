from tools.carrier_footprint_readiness import evaluate


def test_authoritative_footprint_plan_is_frozen():
    result = evaluate(
        "hardware/system_carrier/FOOTPRINT_PLAN_SYS_001.csv"
    )

    assert result["schema"] == "SYSTEM-CARRIER-FOOTPRINT-READINESS-001"
    assert result["status"] == "FOOTPRINT_FREEZE_READY"
    assert result["errors"] == []

    assert "U1" in result["locked_refs"]
    assert "U4" in result["locked_refs"]
    assert "D4" in result["locked_refs"]

    assert "U2" in result["locked_refs"]
    assert "U2" not in result["unresolved_refs"]
    assert "U6" in result["locked_refs"]
    assert "U7" in result["locked_refs"]
    assert result["unresolved_refs"] == []
    assert "U9" in result["locked_refs"]
    assert "U9" not in result["unresolved_refs"]
    assert "J8" in result["locked_refs"]
    assert "J6" in result["locked_refs"]

def test_gnss_esd_footprint_is_locked():
    result = evaluate(
        "hardware/system_carrier/FOOTPRINT_PLAN_SYS_001.csv"
    )
    assert "D8" in result["locked_refs"]
    assert "D8" not in result["unresolved_refs"]
