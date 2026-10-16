from pathlib import Path

from tools.generate_system_carrier_symbols import generate


PIN_CONTRACT = "hardware/system_carrier/SYMBOL_PIN_CONTRACT_SYS_001.csv"
FOOTPRINT_PLAN = "hardware/system_carrier/FOOTPRINT_PLAN_SYS_001.csv"
AUX_PIN_CONTRACT = (
    "hardware/system_carrier/AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv"
)


def test_generates_expected_local_symbols(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        aux_pin_contract=AUX_PIN_CONTRACT,
        output=output,
    )

    assert result["schema"] == "SYSTEM-CARRIER-LOCAL-SYMBOL-LIBRARY-001"
    assert result["status"] == "GENERATED"
    assert result["symbol_count"] == 9
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
        "ECS-2520S33-250-FN-TR",
        "ECS-2520S33-500-FN-TR",
        "ESD2CANFD24DBZRQ1",
        "TPD4E05U06DQAR",
        "POWER_INPUT_2PIN",
    }


def test_shared_tps259470_symbol_covers_u6_u7(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        aux_pin_contract=AUX_PIN_CONTRACT,
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
        aux_pin_contract=AUX_PIN_CONTRACT,
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
        aux_pin_contract=AUX_PIN_CONTRACT,
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
    assert by_name["ICM-42688-P"]["footprint"] == (
        "SystemCarrier_Local:"
        "ICM-42688-P_LGA14_2.5x3mm_P0.5mm"
    )
    assert by_name["TPS259470ARPWR"]["footprint"] == (
        "SystemCarrier_Local:"
        "TPS259470A_RPW0010A_VQFN-HR-10_2x2mm_P0.475mm"
    )


def test_auxiliary_symbol_pin_counts_and_footprints(tmp_path):
    output = tmp_path / "SystemCarrier_Local.kicad_sym"

    result = generate(
        pin_contract=PIN_CONTRACT,
        footprint_plan=FOOTPRINT_PLAN,
        aux_pin_contract=AUX_PIN_CONTRACT,
        output=output,
    )

    by_name = {
        item["name"]: item
        for item in result["symbols"]
    }

    assert by_name["ECS-2520S33-250-FN-TR"]["pin_count"] == 4
    assert by_name["ECS-2520S33-250-FN-TR"]["footprint"] == (
        "Oscillator:"
        "Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm"
    )

    assert by_name["ECS-2520S33-500-FN-TR"]["pin_count"] == 4
    assert by_name["ECS-2520S33-500-FN-TR"]["footprint"] == (
        "Oscillator:"
        "Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm"
    )

    assert by_name["ESD2CANFD24DBZRQ1"]["pin_count"] == 3
    assert by_name["ESD2CANFD24DBZRQ1"]["footprint"] == (
        "Package_TO_SOT_SMD:SOT-23"
    )

    assert by_name["TPD4E05U06DQAR"]["pin_count"] == 10
    assert by_name["TPD4E05U06DQAR"]["footprint"] == (
        "Package_SON:USON-10_2.5x1.0mm_P0.5mm"
    )
