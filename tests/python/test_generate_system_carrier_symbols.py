from pathlib import Path

from tools.generate_system_carrier_symbols import generate


PIN_CONTRACT = "hardware/system_carrier/SYMBOL_PIN_CONTRACT_SYS_001.csv"
FOOTPRINT_PLAN = "hardware/system_carrier/FOOTPRINT_PLAN_SYS_001.csv"


def test_generates_expected_local_symbols(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        output=output,
    )

    assert result["schema"] == "SYSTEM-CARRIER-LOCAL-SYMBOL-LIBRARY-001"
    assert result["status"] == "GENERATED"
    assert result["symbol_count"] == 4
    assert output.is_file()

    names = {
        symbol["name"]
        for symbol in result["symbols"]
    }
    assert names == {
        "ICM-42688-P",
        "TCAN3404DRBRQ1",
        "TPS62132RGTR",
        "TPS259470ARPWR",
    }


def test_shared_tps259470_symbol_covers_u6_u7(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        output=output,
    )

    symbol = next(
        item
        for item in result["symbols"]
        if item["name"] == "TPS259470ARPWR"
    )

    assert symbol["refs"] == ["U6", "U7"]
    assert symbol["pin_count"] == 10


def test_pin_numbers_and_ep_are_emitted(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        output=output,
    )

    text = output.read_text(encoding="utf-8")

    assert '(symbol "ICM-42688-P"' in text
    assert '(number "14"' in text
    assert '(symbol "TCAN3404DRBRQ1"' in text
    assert '(number "EP"' in text
    assert '(symbol "TPS62132RGTR"' in text


def test_locked_footprints_are_embedded_only_when_available(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        output=output,
    )

    by_name = {
        item["name"]: item
        for item in result["symbols"]
    }

    assert by_name["TCAN3404DRBRQ1"]["footprint"] == (
        "Package_SON:Texas_DRB0008A"
    )
    assert by_name["TPS62132RGTR"]["footprint"] == (
        "Package_DFN_QFN:"
        "VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm"
    )
    assert by_name["ICM-42688-P"]["footprint"] == ""
    assert by_name["TPS259470ARPWR"]["footprint"] == ""
