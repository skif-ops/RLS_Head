from pathlib import Path

from tools.validate_gnss_esd_footprint import validate


def test_gnss_esd_local_footprint_matches_infineon_package():
    path = Path(
        "hardware/system_carrier/footprints/"
        "SystemCarrier_Local.pretty/"
        "ESD0P2RF-02LS_PG-TSSLP-2-1.kicad_mod"
    )

    result = validate(path)

    assert result["schema"] == "SYSTEM-CARRIER-GNSS-ESD-FOOTPRINT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["pad_count"] == 2
    assert result["copper_land_mm"] == [0.32, 0.24]
    assert result["copper_gap_mm"] == 0.14
    assert result["stencil_aperture_mm"] == [0.27, 0.19]
