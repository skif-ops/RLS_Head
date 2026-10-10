import json
from pathlib import Path

from tools.m300_external_preflight import evaluate_preflight


def valid_manifest():
    return {
        "schema": "EVM-RUN-MANIFEST-001",
        "run_id": "EVM-M300-001",
        "mode": "QUALIFY",
        "profile_id": "TRACK",
        "profile_config_sha256": "a" * 64,
        "source_commit": "b" * 40,
        "target_id": "RCS-0P01",
        "range_nominal_m": 300.0,
        "rcs_m2": 0.01,
        "start_time_us": 1000000,
        "end_time_us": 2000000,
        "truth_status": "VALID",
        "time_alignment_valid": True,
        "config_locked": True,
        "evidence_level": "MEASURED_EVM",
        "synthetic_fixture": False,
        "raw_capture_enabled": False,
        "environment": {
            "temperature_c": 20.0,
            "precipitation_state": "NONE",
        },
        "files": [],
    }


def write_csv(path: Path, rows: str = ""):
    path.write_text(
        "range_m,detected,track_valid,fresh,detector_margin_db\n"
        + rows,
        encoding="utf-8",
    )


def test_valid_preflight_ready(tmp_path):
    csv_path = tmp_path / "range_samples.csv"
    write_csv(csv_path)

    result = evaluate_preflight(
        run_manifest=valid_manifest(),
        range_csv=csv_path,
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert result["errors"] == []
    assert "range_csv_has_no_samples" in result["warnings"]


def test_template_placeholders_block(tmp_path):
    csv_path = tmp_path / "range_samples.csv"
    write_csv(csv_path)

    manifest = valid_manifest()
    manifest["run_id"] = "<FILL>"

    result = evaluate_preflight(
        run_manifest=manifest,
        range_csv=csv_path,
    )

    assert result["status"] == "BLOCKED"
    assert "missing_or_placeholder:run_id" in result["errors"]


def test_wrong_range_and_rcs_block(tmp_path):
    csv_path = tmp_path / "range_samples.csv"
    write_csv(csv_path)

    manifest = valid_manifest()
    manifest["range_nominal_m"] = 250.0
    manifest["rcs_m2"] = 0.1

    result = evaluate_preflight(
        run_manifest=manifest,
        range_csv=csv_path,
    )

    assert "range_not_300m" in result["errors"]
    assert "rcs_not_0p01m2" in result["errors"]


def test_synthetic_or_unlocked_config_block(tmp_path):
    csv_path = tmp_path / "range_samples.csv"
    write_csv(csv_path)

    manifest = valid_manifest()
    manifest["synthetic_fixture"] = True
    manifest["config_locked"] = False

    result = evaluate_preflight(
        run_manifest=manifest,
        range_csv=csv_path,
    )

    assert "synthetic_fixture_not_false" in result["errors"]
    assert "config_not_locked" in result["errors"]


def test_wrong_csv_header_blocks(tmp_path):
    csv_path = tmp_path / "range_samples.csv"
    csv_path.write_text("bad,header\n", encoding="utf-8")

    result = evaluate_preflight(
        run_manifest=valid_manifest(),
        range_csv=csv_path,
    )

    assert "range_csv_header" in result["errors"]


def test_missing_csv_blocks(tmp_path):
    result = evaluate_preflight(
        run_manifest=valid_manifest(),
        range_csv=tmp_path / "missing.csv",
    )

    assert "range_csv_missing" in result["errors"]
