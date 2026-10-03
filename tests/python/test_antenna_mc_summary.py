import math

from tools.antenna_mc_summary import (
    McGateConfig,
    percentile,
    summarize_mc,
)


def make_rows(samples=20, bad_mandatory=False):
    rows = []

    for sample in range(samples):
        rows.append(
            {
                "mc_sample_id": f"S{sample:03d}",
                "frequency_hz": "78500000000",
                "az_deg": "0",
                "el_deg": "0",
                "combined_gain_delta_db": str(2.0 + (sample - samples / 2) * 0.01),
                "sigma_az_deg": "0.17",
                "sigma_el_deg": "0.18",
                "ambiguity_flag": "1" if bad_mandatory and sample < 2 else "0",
                "track_usable": "0" if bad_mandatory and sample < 2 else "1",
                "mandatory_region": "1",
            }
        )

        rows.append(
            {
                "mc_sample_id": f"S{sample:03d}",
                "frequency_hz": "78500000000",
                "az_deg": "30",
                "el_deg": "0",
                "combined_gain_delta_db": str(-3.0 + sample * 0.01),
                "sigma_az_deg": "0.30",
                "sigma_el_deg": "0.25",
                "ambiguity_flag": "0",
                "track_usable": "1",
                "mandatory_region": "0",
            }
        )

    return rows


def test_percentile_linear():
    values = [0.0, 10.0, 20.0]
    assert math.isclose(percentile(values, 0.5), 10.0)
    assert math.isclose(percentile(values, 0.25), 5.0)


def test_mc_summary_pass():
    result = summarize_mc(make_rows())

    assert result["schema"] == "ANT-D1-MC-SUMMARY-001"
    assert result["status"] == "PASS"
    assert result["cell_count"] == 2

    mandatory = next(
        cell for cell in result["cells"]
        if cell["mandatory_region"]
    )

    assert mandatory["sample_count"] == 20
    assert mandatory["track_usable_probability"] == 1.0
    assert mandatory["ambiguity_probability"] == 0.0
    assert mandatory["robust"] is True


def test_mandatory_region_failure():
    result = summarize_mc(
        make_rows(bad_mandatory=True),
        McGateConfig(
            min_samples_per_cell=20,
            min_track_usable_probability=0.95,
            max_ambiguity_probability=0.05,
        ),
    )

    assert result["status"] == "FAIL"
    assert "mandatory_region_not_robust" in result["reason_codes"]


def test_underfilled_is_incomplete():
    result = summarize_mc(
        make_rows(samples=5),
        McGateConfig(min_samples_per_cell=20),
    )

    assert result["status"] == "INCOMPLETE"
    assert "underfilled_cells" in result["reason_codes"]
