import math

from tools.reference_range import (
    ReferenceRangeConfig,
    build_reference_range_result,
)


RANGES = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0)


def make_rows(samples_per_range=20, perturb=None):
    rows = []

    for range_m in RANGES:
        base_signal = 100.0 - 40.0 * math.log10(range_m)

        for index in range(samples_per_range):
            delta = 0.0 if perturb is None else perturb(range_m, index)
            rows.append(
                {
                    "run_id": f"REF-R{int(range_m):03d}",
                    "range_m": str(range_m),
                    "signal_db": str(base_signal + delta),
                    "detector_margin_db": str(20.0 - 40.0 * math.log10(range_m / 50.0)),
                    "detected": "1",
                    "track_valid": "1",
                }
            )

    return rows


def test_reference_range_r4_ready():
    result = build_reference_range_result(make_rows())

    assert result["schema"] == "REFERENCE-RANGE-RESULT-001"
    assert result["status"] == "DATA_READY"
    assert result["reason_codes"] == []
    assert len(result["points"]) == 6

    assert math.isclose(result["fit"]["n_hat"], 4.0, abs_tol=1e-10)
    assert result["fit"]["rms_residual_db"] < 1e-10
    assert result["r4_rms_residual_db"] < 1e-10


def test_reference_range_underfilled():
    result = build_reference_range_result(
        make_rows(samples_per_range=5),
        ReferenceRangeConfig(min_samples_per_range=20),
    )

    assert result["status"] == "INCOMPLETE"
    assert "insufficient_samples" in result["reason_codes"]
    assert result["underfilled_ranges_m"] == list(RANGES)


def test_reference_range_missing_point():
    rows = [
        row for row in make_rows()
        if float(row["range_m"]) != 250.0
    ]

    result = build_reference_range_result(rows)

    assert result["status"] == "INCOMPLETE"
    assert "missing_ranges" in result["reason_codes"]
    assert result["missing_ranges_m"] == [250.0]


def test_reference_range_fit_poor():
    def perturb(range_m, _):
        return 8.0 if range_m == 200.0 else 0.0

    result = build_reference_range_result(
        make_rows(perturb=perturb),
        ReferenceRangeConfig(max_fit_rms_db=1.0),
    )

    assert result["status"] == "FIT_POOR"
    assert "fit_residual" in result["reason_codes"]


def test_reference_range_run_ids_preserved():
    result = build_reference_range_result(make_rows())

    assert result["run_ids"] == [
        "REF-R050",
        "REF-R100",
        "REF-R150",
        "REF-R200",
        "REF-R250",
        "REF-R300",
    ]
