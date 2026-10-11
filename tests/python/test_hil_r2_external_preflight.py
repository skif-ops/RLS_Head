from pathlib import Path

from tools.hil_r2_external_preflight import (
    evaluate_preflight,
)


def config():
    return {
        "min_radar_imu_samples": 100,
        "min_pps_samples": 30,
        "radar_imu_max_abs_us": 250.0,
        "radar_imu_rms_us": 200.0,
        "pps_max_abs_us": 100.0,
        "pps_rms_us": 75.0,
        "holdover_max_abs_us": 600.0,
        "max_missed_events": 0,
        "max_monotonic_failures": 0,
    }


def write_csv(path: Path, body: str = ""):
    path.write_text(
        "kind,value_us,count\n" + body,
        encoding="utf-8",
    )


def test_empty_template_ready_for_collection_with_warning(tmp_path):
    path = tmp_path / "timing_capture.csv"
    write_csv(path)

    result = evaluate_preflight(
        timing_csv=path,
        gate_config=config(),
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert result["errors"] == []
    assert "timing_csv_has_no_samples" in result["warnings"]


def test_valid_sample_rows_ready(tmp_path):
    path = tmp_path / "timing_capture.csv"
    write_csv(
        path,
        "radar_imu,10.0,1\npps,5.0,1\n",
    )

    result = evaluate_preflight(
        timing_csv=path,
        gate_config=config(),
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert result["errors"] == []


def test_wrong_header_blocks(tmp_path):
    path = tmp_path / "timing_capture.csv"
    path.write_text(
        "bad,header\n",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        timing_csv=path,
        gate_config=config(),
    )

    assert result["status"] == "BLOCKED"
    assert "timing_csv_header" in result["errors"]


def test_missing_config_blocks(tmp_path):
    path = tmp_path / "timing_capture.csv"
    write_csv(path)

    cfg = config()
    del cfg["pps_rms_us"]

    result = evaluate_preflight(
        timing_csv=path,
        gate_config=cfg,
    )

    assert result["status"] == "BLOCKED"
    assert (
        "missing_config:pps_rms_us"
        in result["errors"]
    )


def test_bad_value_blocks(tmp_path):
    path = tmp_path / "timing_capture.csv"
    write_csv(
        path,
        "radar_imu,not-a-number,1\n",
    )

    result = evaluate_preflight(
        timing_csv=path,
        gate_config=config(),
    )

    assert result["status"] == "BLOCKED"
    assert "invalid_value_us:2" in result["errors"]


def test_missing_csv_blocks(tmp_path):
    result = evaluate_preflight(
        timing_csv=tmp_path / "missing.csv",
        gate_config=config(),
    )

    assert result["status"] == "BLOCKED"
    assert "timing_csv_missing" in result["errors"]
