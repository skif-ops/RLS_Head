from tools.antenna_map_validate import (
    ValidationConfig,
    validate_rows,
)


def config():
    return ValidationConfig(
        required_cases=("NOMINAL",),
        required_frequencies_hz=(
            76_000_000_000.0,
            78_500_000_000.0,
            81_000_000_000.0,
        ),
        min_points_per_group=3,
        require_boresight=True,
        boresight_tolerance_deg=0.001,
    )


def make_rows():
    rows = []

    for frequency in (
        76_000_000_000,
        78_500_000_000,
        81_000_000_000,
    ):
        for az, gain, sigma, ambiguity, track, high_acc in (
            (0.0, 1.0, 0.17, 0, 1, 1),
            (30.0, -1.5, 0.30, 0, 1, 0),
            (45.0, -6.0, 1.00, 1, 0, 0),
        ):
            rows.append(
                {
                    "case_id": "NOMINAL",
                    "frequency_hz": str(frequency),
                    "az_deg": str(az),
                    "el_deg": "0",
                    "gain_tx_delta_db": str(gain),
                    "gain_rx_delta_db": str(gain),
                    "sigma_az_deg": str(sigma),
                    "sigma_el_deg": str(sigma),
                    "ambiguity_flag": str(ambiguity),
                    "track_usable": str(track),
                    "high_acc_usable": str(high_acc),
                }
            )

    return rows


def test_complete_map_is_ready():
    result = validate_rows(make_rows(), config())

    assert result["schema"] == "ANT-D1-MAP-VALIDATION-001"
    assert result["status"] == "DATA_READY"
    assert result["reason_codes"] == []
    assert result["row_count"] == 9
    assert len(result["groups"]) == 3


def test_missing_frequency_is_incomplete():
    rows = [
        row for row in make_rows()
        if row["frequency_hz"] != "81000000000"
    ]

    result = validate_rows(rows, config())

    assert result["status"] == "INCOMPLETE"
    assert "missing_groups" in result["reason_codes"]


def test_duplicate_point_is_incomplete():
    rows = make_rows()
    rows.append(dict(rows[0]))

    result = validate_rows(rows, config())

    assert result["status"] == "INCOMPLETE"
    assert "duplicate_points" in result["reason_codes"]


def test_ambiguous_track_usable_is_rejected():
    rows = make_rows()
    rows[2]["track_usable"] = "1"

    try:
        validate_rows(rows, config())
    except ValueError as exc:
        assert "ambiguous point" in str(exc)
    else:
        raise AssertionError("invalid ambiguity/track combination accepted")


def test_high_acc_requires_track():
    rows = make_rows()
    rows[1]["track_usable"] = "0"
    rows[1]["high_acc_usable"] = "1"

    try:
        validate_rows(rows, config())
    except ValueError as exc:
        assert "high_acc_usable requires track_usable" in str(exc)
    else:
        raise AssertionError("invalid high-accuracy combination accepted")
