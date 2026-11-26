from pathlib import Path

from tools.carrier_power_24v_gate import validate


SYSTEM = Path("hardware/system_carrier")


def test_power_24v_contract_passes() -> None:
    result = validate(SYSTEM)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["calculations"]["available_output_power_at_18v_w"] >= 60.0
    assert 0.2 <= result["calculations"]["inductor_ripple_fraction"] <= 0.4
    assert result["authority"]["production_authority"] == "NOT_AUTHORIZED"


def test_power_24v_contract_rejects_direct_downstream_24v(tmp_path: Path) -> None:
    target = tmp_path / "system"
    target.mkdir()
    for name in (
        "POWER_INPUT_24V_CONTRACT_SYS_001.json",
        "POWER_TREE_SYS_001.csv",
        "BOM_SYS_CARRIER_LAYOUT_004.csv",
    ):
        (target / name).write_bytes((SYSTEM / name).read_bytes())

    tree = target / "POWER_TREE_SYS_001.csv"
    tree.write_text(
        tree.read_text(encoding="utf-8").replace(
            "V12_SYS,3V3,TPS62132RGTR",
            "VIN_PROTECTED_24V,3V3,TPS62132RGTR",
        ),
        encoding="utf-8",
    )

    result = validate(target)

    assert result["status"] == "FAIL"
    assert "direct_24v_downstream:TPS62132RGTR" in result["errors"]
