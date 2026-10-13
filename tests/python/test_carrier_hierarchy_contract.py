from pathlib import Path

from tools.carrier_hierarchy_contract import (
    validate_contract,
)


CONTRACT = Path(
    "hardware/system_carrier/"
    "HIERARCHY_INTERFACE_SYS_001.csv"
)


def test_authoritative_hierarchy_contract_passes():
    result = validate_contract(CONTRACT)

    assert (
        result["schema"]
        == "SYSTEM-CARRIER-HIERARCHY-CONTRACT-001"
    )
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["sheet_count"] == 7
    assert result["net_count"] >= 20


def test_hierarchy_contract_rejects_input_only_net(
    tmp_path,
):
    source = CONTRACT.read_text(
        encoding="utf-8"
    )
    path = tmp_path / "contract.csv"
    path.write_text(
        source
        + (
            "MCU_CORE,INPUT_ONLY_TEST,input,"
            "U1,40,P2,test\n"
            "IMU,INPUT_ONLY_TEST,input,U2,12,P2,test\n"
        ),
        encoding="utf-8",
    )

    result = validate_contract(path)

    assert result["status"] == "FAIL"
    assert (
        "input_only_net:INPUT_ONLY_TEST"
        in result["errors"]
    )
