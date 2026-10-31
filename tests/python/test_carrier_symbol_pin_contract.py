from tools.carrier_symbol_pin_contract import (
    validate_symbol_pin_contract,
)


def test_authoritative_symbol_pin_contract_passes():
    result = validate_symbol_pin_contract(
        "hardware/system_carrier"
    )

    assert result["schema"] == "SYSTEM-CARRIER-SYMBOL-PIN-CONTRACT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["refs"] == [
        "U2", "U4", "U5", "U6", "U7", "U9"
    ]
