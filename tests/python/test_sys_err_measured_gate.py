import copy
import hashlib
import json
from pathlib import Path

from tools.sys_err_measured_gate import (
    evaluate_gate,
    load_config,
    load_json,
)

MANIFEST = Path("tests/fixtures/sys_err_measured_manifest_ci.json")
CONFIG = Path("config/sys_err_measured_evt.json")
TIMING = Path("tests/fixtures/sys_err_measured_timing_ci.json")
CELLS = Path("tests/fixtures/sys_err_measured_cells_ci.csv")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_fixture_test_ready():
    result = evaluate_gate(
        manifest=load_json(MANIFEST),
        config=load_config(CONFIG),
        repository_root=".",
    )
    assert result["schema"] == "SYS-ERR-GATE-001"
    assert result["status"] == "TEST_READY"
    assert result["gate_status"] == "PASS"
    assert result["synthetic_fixture"] is True
    assert result["reason_codes"] == []
    assert len(result["cells"]) == 3
    assert len(result["mandatory_cells"]) == 1
    assert result["mandatory_cells"][0]["range_m"] == 300.0
    assert result["mandatory_cells"][0]["position_rms_m"] < 2.10


def test_real_measured_bench_pass(tmp_path):
    timing_path = tmp_path / "timing.json"
    cells_path = tmp_path / "cells.csv"
    timing_path.write_bytes(TIMING.read_bytes())
    cells_path.write_bytes(CELLS.read_bytes())

    manifest = {
        "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_BENCH",
        "timing_evidence": {
            "path": timing_path.name,
            "sha256": sha256(timing_path),
        },
        "cells_csv": {
            "path": cells_path.name,
            "sha256": sha256(cells_path),
        },
    }

    result = evaluate_gate(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "PASS"
    assert result["gate_status"] == "PASS"
    assert result["evidence_level"] == "MEASURED_BENCH"
    assert result["synthetic_fixture"] is False


def test_timing_rms_failure(tmp_path):
    timing = load_json(TIMING)
    timing["radar_imu"]["rms_us"] = 250.0

    timing_path = tmp_path / "timing.json"
    timing_path.write_text(json.dumps(timing), encoding="utf-8")

    cells_path = tmp_path / "cells.csv"
    cells_path.write_bytes(CELLS.read_bytes())

    manifest = {
        "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_BENCH",
        "timing_evidence": {
            "path": timing_path.name,
            "sha256": sha256(timing_path),
        },
        "cells_csv": {
            "path": cells_path.name,
            "sha256": sha256(cells_path),
        },
    }

    result = evaluate_gate(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert "timestamp_rms" in result["reason_codes"]


def test_mandatory_300m_spatial_failure(tmp_path):
    timing_path = tmp_path / "timing.json"
    timing_path.write_bytes(TIMING.read_bytes())

    text = CELLS.read_text(encoding="utf-8").replace(
        "R300,300,0.30,0.10,0.10,0.05,0.03,90",
        "R300,300,0.30,0.50,0.50,0.25,0.10,180",
    )

    cells_path = tmp_path / "cells.csv"
    cells_path.write_text(text, encoding="utf-8")

    manifest = {
        "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_BENCH",
        "timing_evidence": {
            "path": timing_path.name,
            "sha256": sha256(timing_path),
        },
        "cells_csv": {
            "path": cells_path.name,
            "sha256": sha256(cells_path),
        },
    }

    result = evaluate_gate(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert "mandatory_position_rms" in result["reason_codes"]
    assert result["mandatory_cells"][0]["position_rms_m"] > 2.10


def test_hash_mismatch_invalid(tmp_path):
    timing_path = tmp_path / "timing.json"
    timing_path.write_bytes(TIMING.read_bytes())

    cells_path = tmp_path / "cells.csv"
    cells_path.write_bytes(CELLS.read_bytes())

    manifest = {
        "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture": False,
        "evidence_level": "MEASURED_BENCH",
        "timing_evidence": {
            "path": timing_path.name,
            "sha256": "0" * 64,
        },
        "cells_csv": {
            "path": cells_path.name,
            "sha256": sha256(cells_path),
        },
    }

    result = evaluate_gate(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "INVALID"
    assert "timing:hash_mismatch" in result["errors"]


def test_non_measured_evidence_holds(tmp_path):
    timing_path = tmp_path / "timing.json"
    timing_path.write_bytes(TIMING.read_bytes())

    cells_path = tmp_path / "cells.csv"
    cells_path.write_bytes(CELLS.read_bytes())

    manifest = {
        "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture": False,
        "evidence_level": "SOFTWARE_CI",
        "timing_evidence": {
            "path": timing_path.name,
            "sha256": sha256(timing_path),
        },
        "cells_csv": {
            "path": cells_path.name,
            "sha256": sha256(cells_path),
        },
    }

    result = evaluate_gate(
        manifest=manifest,
        config=load_config(CONFIG),
        repository_root=tmp_path,
    )

    assert result["status"] == "HOLD"
    assert result["gate_status"] == "PASS"
