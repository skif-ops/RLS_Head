import math

from tools.rad_lb006_revb import build_rad_lb006_revb


def reva():
    return {
        "schema": "RAD-LB-006-REVA",
        "status": "PROJECTED",
        "cells": [
            {
                "range_m": 300.0,
                "rcs_m2": 0.01,
                "m_anchor_db": 2.0,
                "m_rcs_db": 0.0,
                "l_range_empirical_db": 0.0,
                "l_range_r4_db": 0.0,
                "m_total_empirical_db": 2.0,
                "m_total_r4_db": 2.0,
            },
            {
                "range_m": 600.0,
                "rcs_m2": 0.10,
                "m_anchor_db": 2.0,
                "m_rcs_db": 10.0,
                "l_range_empirical_db": 12.04119983,
                "l_range_r4_db": 12.04119983,
                "m_total_empirical_db": -0.04119983,
                "m_total_r4_db": -0.04119983,
            },
        ],
    }


def antenna_rows():
    return [
        {
            "case_id": "NOMINAL",
            "frequency_hz": "78500000000",
            "az_deg": "0",
            "el_deg": "0",
            "gain_tx_delta_db": "1.0",
            "gain_rx_delta_db": "1.0",
            "sigma_az_deg": "0.17",
            "sigma_el_deg": "0.17",
            "ambiguity_flag": "0",
            "track_usable": "1",
            "high_acc_usable": "1",
        },
        {
            "case_id": "NOMINAL",
            "frequency_hz": "78500000000",
            "az_deg": "30",
            "el_deg": "0",
            "gain_tx_delta_db": "-1.5",
            "gain_rx_delta_db": "-1.5",
            "sigma_az_deg": "0.30",
            "sigma_el_deg": "0.25",
            "ambiguity_flag": "0",
            "track_usable": "1",
            "high_acc_usable": "0",
        },
        {
            "case_id": "NOMINAL",
            "frequency_hz": "78500000000",
            "az_deg": "45",
            "el_deg": "0",
            "gain_tx_delta_db": "-6.0",
            "gain_rx_delta_db": "-6.0",
            "sigma_az_deg": "1.0",
            "sigma_el_deg": "0.8",
            "ambiguity_flag": "1",
            "track_usable": "0",
            "high_acc_usable": "0",
        },
    ]


def find_cell(result, range_m, rcs_m2, az_deg):
    return next(
        cell for cell in result["cells"]
        if cell["range_m"] == range_m
        and cell["rcs_m2"] == rcs_m2
        and cell["az_deg"] == az_deg
    )


def test_revb_adds_two_way_antenna_margin():
    result = build_rad_lb006_revb(
        reva(),
        antenna_rows(),
        case_id="NOMINAL",
        frequency_hz=78_500_000_000.0,
    )

    assert result["schema"] == "RAD-LB-006-REVB"
    assert result["status"] == "PROJECTED"
    assert len(result["cells"]) == 6

    cell = find_cell(result, 300.0, 0.01, 0.0)

    assert math.isclose(cell["m_ant_db"], 2.0, abs_tol=1e-12)
    assert math.isclose(cell["m_total_r4_db"], 4.0, abs_tol=1e-12)
    assert cell["projected_track_r4"] is True


def test_revb_600m_upper_rcs_closes_with_plus2db_antenna():
    result = build_rad_lb006_revb(
        reva(),
        antenna_rows(),
        case_id="NOMINAL",
        frequency_hz=78_500_000_000.0,
    )

    cell = find_cell(result, 600.0, 0.10, 0.0)

    assert math.isclose(
        cell["m_total_r4_db"],
        1.95880017,
        abs_tol=1e-6,
    )
    assert cell["projected_track_r4"] is True


def test_ambiguity_overrides_positive_margin():
    result = build_rad_lb006_revb(
        reva(),
        antenna_rows(),
        case_id="NOMINAL",
        frequency_hz=78_500_000_000.0,
    )

    cell = find_cell(result, 300.0, 0.01, 45.0)

    assert cell["ambiguity_flag"] is True
    assert cell["track_usable"] is False
    assert cell["projected_track_r4"] is False


def test_high_acc_preserved_separately():
    result = build_rad_lb006_revb(
        reva(),
        antenna_rows(),
        case_id="NOMINAL",
        frequency_hz=78_500_000_000.0,
    )

    boresight = find_cell(result, 300.0, 0.01, 0.0)
    mid = find_cell(result, 300.0, 0.01, 30.0)

    assert boresight["high_acc_usable"] is True
    assert mid["track_usable"] is True
    assert mid["high_acc_usable"] is False
