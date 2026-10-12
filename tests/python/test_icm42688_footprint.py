from pathlib import Path

from tools.validate_icm42688_footprint import validate


def test_icm42688_local_footprint_is_locked_to_manufacturer_geometry():
    path = Path(
        "hardware/system_carrier/footprints/"
        "SystemCarrier_Local.pretty/"
        "ICM-42688-P_LGA14_2.5x3mm_P0.5mm.kicad_mod"
    )

    result = validate(path)

    assert result["schema"] == "SYSTEM-CARRIER-ICM42688-FOOTPRINT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["pad_count"] == 14
    assert result["land_size_mm"] == [0.475, 0.25]
    assert result["pitch_mm"] == 0.5
