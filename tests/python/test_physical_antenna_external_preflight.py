from pathlib import Path

from tools.physical_antenna_external_preflight import evaluate_preflight


HEADER = (
    "measurement_id,frequency_hz,az_deg,el_deg,realized_gain_db,"
    "gain_uncertainty_db,sigma_az_deg,sigma_el_deg,ambiguity_flag,"
    "track_usable,high_acc_usable,repeat_count\n"
)


def config():
    return {
        "required_frequencies_hz": [
            76000000000,
            78500000000,
            81000000000,
        ],
        "min_points_per_frequency": 3,
        "require_boresight": True,
        "boresight_tolerance_deg": 0.001,
        "max_gain_uncertainty_db": 1.0,
        "min_repeat_count": 3,
        "min_track_usable_points": 1,
        "min_high_acc_usable_points": 1,
    }


def manifest():
    return {
        "schema": "ANT-MEASUREMENT-MANIFEST-001",
        "measurement_id": "ANT-MEAS-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_EM",
        "instrument_id": "INSTRUMENT-001",
        "calibration_id": "CAL-001",
        "measurement_csv": {
            "path": "antenna_measurement.csv",
            "sha256": "<FILL_SHA256>",
        },
    }


def test_empty_measurement_csv_ready_with_warning(tmp_path):
    (tmp_path / "antenna_measurement.csv").write_text(
        HEADER,
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert "measurement_csv:no_samples_yet" in result["warnings"]


def test_missing_instrument_blocks(tmp_path):
    (tmp_path / "antenna_measurement.csv").write_text(
        HEADER,
        encoding="utf-8",
    )
    data = manifest()
    data["instrument_id"] = "<FILL>"

    result = evaluate_preflight(
        manifest=data,
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert result["status"] == "BLOCKED"
    assert "missing_or_placeholder:instrument_id" in result["errors"]


def test_synthetic_blocks(tmp_path):
    (tmp_path / "antenna_measurement.csv").write_text(
        HEADER,
        encoding="utf-8",
    )
    data = manifest()
    data["synthetic_fixture"] = True

    result = evaluate_preflight(
        manifest=data,
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert "synthetic_fixture_not_false" in result["errors"]


def test_bad_header_blocks(tmp_path):
    (tmp_path / "antenna_measurement.csv").write_text(
        "bad,header\n",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert result["status"] == "BLOCKED"
    assert "measurement_csv:header" in result["errors"]


def test_invalid_config_blocks(tmp_path):
    (tmp_path / "antenna_measurement.csv").write_text(
        HEADER,
        encoding="utf-8",
    )
    cfg = config()
    cfg["min_repeat_count"] = 0

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=cfg,
        repository_root=tmp_path,
    )

    assert result["status"] == "BLOCKED"
    assert "invalid_config:min_repeat_count" in result["errors"]
