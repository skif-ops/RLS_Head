import hashlib
import json
from pathlib import Path

from tools.physical_antenna_measurement import (
    evaluate_measurement,
    load_config,
    load_json,
)


CSV = Path(
    "tests/fixtures/physical_antenna_measurement_ci.csv"
)
MANIFEST = Path(
    "tests/fixtures/physical_antenna_measurement_manifest_ci.json"
)
CONFIG = Path(
    "config/physical_antenna_measurement_evt.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_measurement_test_ready():
    result = evaluate_measurement(
        manifest=load_json(MANIFEST),
        config=load_config(CONFIG),
        repository_root=".",
    )

    assert result["schema"] == "ANT-MEASUREMENT-001"
    assert result["status"] == "TEST_READY"
    assert result["measurement_status"] == "PASS"
    assert result["synthetic_fixture"] is True
    assert result["row_count"] == 9
    assert result["track_usable_point_count"] >= 1
    assert result["high_acc_usable_point_count"] >= 1
    assert result["errors"] == []


def test_real_evidence_level_pass(tmp_path):
    csv_path = tmp_path / "measured.csv"
    csv_path.write_bytes(CSV.read_bytes())

    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "schema": "ANT-MEASUREMENT-MANIFEST-001",
        "measurement_id": "ANT-MEAS-CI-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_EM",
        "instrument_id": "TEST-INSTRUMENT",
        "calibration_id": "TEST-CAL",
        "measurement_csv": {
            "path": csv_path.name,
            "sha256": sha256(csv_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    result = evaluate_measurement(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "PASS"
    assert result["measurement_status"] == "PASS"
    assert result["evidence_level"] == "MEASURED_EM"


def test_hash_mismatch_invalid(tmp_path):
    csv_path = tmp_path / "measured.csv"
    csv_path.write_bytes(CSV.read_bytes())

    manifest = {
        "schema": "ANT-MEASUREMENT-MANIFEST-001",
        "measurement_id": "ANT-MEAS-CI-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_EM",
        "measurement_csv": {
            "path": csv_path.name,
            "sha256": "0" * 64,
        },
    }

    result = evaluate_measurement(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "INVALID"
    assert "measurement_csv_hash_mismatch" in result["errors"]


def test_uncertainty_fail(tmp_path):
    text = CSV.read_text(encoding="utf-8")
    text = text.replace(
        "12.0,0.5,0.20",
        "12.0,1.5,0.20",
        1,
    )

    csv_path = tmp_path / "measured.csv"
    csv_path.write_text(
        text,
        encoding="utf-8",
    )

    manifest = {
        "schema": "ANT-MEASUREMENT-MANIFEST-001",
        "measurement_id": "ANT-MEAS-CI-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_EM",
        "measurement_csv": {
            "path": csv_path.name,
            "sha256": sha256(csv_path),
        },
    }

    result = evaluate_measurement(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert "gain_uncertainty" in result["reason_codes"]


def test_missing_frequency_incomplete(tmp_path):
    lines = [
        line
        for line in CSV.read_text(
            encoding="utf-8"
        ).splitlines()
        if "81000000000" not in line
    ]

    csv_path = tmp_path / "measured.csv"
    csv_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "ANT-MEASUREMENT-MANIFEST-001",
        "measurement_id": "ANT-MEAS-CI-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_EM",
        "measurement_csv": {
            "path": csv_path.name,
            "sha256": sha256(csv_path),
        },
    }

    result = evaluate_measurement(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "INCOMPLETE"
    assert "missing_frequencies" in result["reason_codes"]
