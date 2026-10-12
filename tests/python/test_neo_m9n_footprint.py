from pathlib import Path

from tools.validate_neo_m9n_footprint import validate


def test_neo_m9n_local_footprint_matches_ublox_geometry():
    path = Path(
        "hardware/system_carrier/footprints/"
        "SystemCarrier_Local.pretty/"
        "NEO-M9N_LCC24_12.2x16mm.kicad_mod"
    )

    result = validate(path)

    assert result["schema"] == "SYSTEM-CARRIER-NEO-M9N-FOOTPRINT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["pad_count"] == 24
    assert result["land_size_mm"] == [1.0, 0.8]
    assert result["pitch_mm"] == 1.1
    assert result["center_gap_mm"] == 3.0
