import math

from tools.range_analysis import (
    RangeCriteria,
    build_m300_result,
    fit_range_exponent,
    predicted_range_m,
    required_margin_db,
    wilson_interval,
)


def test_required_margin_known_values():
    assert math.isclose(required_margin_db(300.0, 400.0), 4.99754946, abs_tol=1e-6)
    assert math.isclose(required_margin_db(300.0, 500.0), 8.87394998, abs_tol=1e-6)
    assert math.isclose(required_margin_db(300.0, 600.0), 12.04119983, abs_tol=1e-6)


def test_predicted_range_known_values():
    assert math.isclose(predicted_range_m(300.0, 6.0), 423.7613, abs_tol=1e-3)
    assert math.isclose(predicted_range_m(300.0, 10.0), 533.4838, abs_tol=1e-3)


def test_fit_range_exponent_r4():
    points = []
    for r in (50.0, 100.0, 150.0, 200.0, 250.0, 300.0):
        signal_db = 100.0 - 40.0 * math.log10(r)
        points.append((r, signal_db))

    result = fit_range_exponent(points)

    assert math.isclose(result["n_hat"], 4.0, abs_tol=1e-10)
    assert result["rms_residual_db"] < 1e-10


def test_wilson_interval_contains_fraction():
    low, high = wilson_interval(450, 500)
    assert low < 0.90 < high


def test_m300_track_pass():
    rows = []

    for i in range(500):
        rows.append(
            {
                "range_m": "300",
                "detected": "1" if i < 460 else "0",
                "track_valid": "1" if i < 480 else "0",
                "fresh": "1" if i < 475 else "0",
                "detector_margin_db": "2.0",
            }
        )

    result = build_m300_result(rows, RangeCriteria())

    assert result["schema"] == "M300-REPORT-001"
    assert result["track_status"] == "TRACK_PASS"
    assert result["summary"]["pd"] == 0.92
    assert result["summary"]["track_availability"] == 0.96
    assert result["m300_track_db"] == 2.0


def test_m300_detect_only():
    rows = []

    for i in range(100):
        rows.append(
            {
                "range_m": "300",
                "detected": "1" if i < 95 else "0",
                "track_valid": "1" if i < 80 else "0",
                "fresh": "1" if i < 80 else "0",
                "detector_margin_db": "-1.0",
            }
        )

    result = build_m300_result(rows, RangeCriteria())

    assert result["track_status"] == "DETECT_ONLY"
