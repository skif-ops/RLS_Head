from pathlib import Path

from tools.validate_tps259470_footprint import validate


def test_tps259470_rpw0010a_local_footprint_matches_contract():
    path = Path(
        "hardware/system_carrier/footprints/"
        "SystemCarrier_Local.pretty/"
        "TPS259470A_RPW0010A_VQFN-HR-10_2x2mm_P0.475mm.kicad_mod"
    )

    result = validate(path)

    assert result["schema"] == "SYSTEM-CARRIER-TPS259470-FOOTPRINT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["electrical_pad_numbers"] == list(range(1, 11))
    assert result["custom_corner_pads"] == [1, 4, 7, 10]
    assert result["simple_pads"] == [2, 3, 5, 6, 8, 9]
