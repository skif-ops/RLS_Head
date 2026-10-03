import math

from tools.rad_lb006 import (
    build_rad_lb006_reva,
    range_loss_db,
    rcs_gain_db,
)


def reference_result():
    return {
        "schema": "REFERENCE-RANGE-RESULT-001",
        "status": "DATA_READY",
        "fit": {
            "n_hat": 4.0,
            "rms_residual_db": 0.0,
        },
        "r4_rms_residual_db": 0.0,
    }


def m300_result(track_status="TRACK_PASS", margin_db=2.0):
    return {
        "schema": "M300-REPORT-001",
        "track_status": track_status,
        "m300_track_db": margin_db,
    }


def find_cell(result, range_m, rcs_m2):
    return next(
        cell
        for cell in result["cells"]
        if cell["range_m"] == range_m and cell["rcs_m2"] == rcs_m2
    )


def test_range_loss_known_values():
    assert math.isclose(range_loss_db(400.0, 300.0, 4.0), 4.99754946, abs_tol=1e-6)
    assert math.isclose(range_loss_db(500.0, 300.0, 4.0), 8.87394998, abs_tol=1e-6)
    assert math.isclose(range_loss_db(600.0, 300.0, 4.0), 12.04119983, abs_tol=1e-6)


def test_rcs_gain_known_values():
    assert math.isclose(rcs_gain_db(0.01), 0.0, abs_tol=1e-12)
    assert math.isclose(rcs_gain_db(0.10), 10.0, abs_tol=1e-12)


def test_reva_projected_status_and_grid():
    result = build_rad_lb006_reva(
        reference_result(),
        m300_result(),
    )

    assert result["schema"] == "RAD-LB-006-REVA"
    assert result["status"] == "PROJECTED"
    assert len(result["cells"]) == 12

    mandatory = find_cell(result, 300.0, 0.01)
    assert math.isclose(mandatory["m_total_empirical_db"], 2.0, abs_tol=1e-12)
    assert mandatory["track_possible_empirical"] is True


def test_600m_upper_rcs_with_plus2db_anchor():
    result = build_rad_lb006_reva(
        reference_result(),
        m300_result(margin_db=2.0),
    )

    cell = find_cell(result, 600.0, 0.10)

    expected = 2.0 + 10.0 - 12.04119983
    assert math.isclose(cell["m_total_r4_db"], expected, abs_tol=1e-6)
    assert cell["track_possible_r4"] is False


def test_anchor_not_verified_is_explicit():
    result = build_rad_lb006_reva(
        reference_result(),
        m300_result(track_status="DETECT_ONLY"),
    )

    assert result["status"] == "ANCHOR_NOT_VERIFIED"
    assert "m300_track" in result["reason_codes"]


def test_reference_not_ready_is_explicit():
    reference = reference_result()
    reference["status"] = "FIT_POOR"

    result = build_rad_lb006_reva(
        reference,
        m300_result(),
    )

    assert result["status"] == "INPUT_NOT_READY"
    assert "reference_range" in result["reason_codes"]
