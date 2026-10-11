import json
from pathlib import Path

from tools.external_job_pack import (
    build_job_pack,
    validate_job_pack,
)


def queue_fixture():
    return {
        "schema": "EXTERNAL-EXECUTION-QUEUE-001",
        "status": "READY",
        "queue": [
            {
                "item_id": "M300_MEASURED",
                "next_action": "COLLECT_EVM_M300",
                "measurement_pack_kind": "m300",
                "requires_measured_evidence": True,
                "directly_unlocks": 2,
            },
            {
                "item_id": "HIL_R2_BENCH_MEASURED",
                "next_action": "COLLECT_HIL_R2_BENCH",
                "measurement_pack_kind": "hil_r2_bench",
                "requires_measured_evidence": True,
                "directly_unlocks": 1,
            },
        ],
    }


def test_build_priority_one_m300_job_pack(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
    )

    assert manifest["item_id"] == "M300_MEASURED"
    assert manifest["preflight"]["expected_ready_status"] == "READY_FOR_COLLECTION"
    assert (tmp_path / "preflight_config.json").is_file()


def test_m300_template_validates_but_preflight_is_blocked(tmp_path):
    build_job_pack(queue_fixture(), tmp_path)
    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "BLOCKED"


def test_filled_m300_pack_reaches_ready_for_collection(tmp_path):
    build_job_pack(queue_fixture(), tmp_path)

    run_path = (
        tmp_path / "measurement_pack" / "run_manifest.json"
    )
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run.update(
        {
            "run_id": "EVM-M300-001",
            "profile_id": "TRACK",
            "profile_config_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "target_id": "RCS-0P01",
            "start_time_us": 1000000,
            "end_time_us": 2000000,
            "truth_status": "VALID",
            "time_alignment_valid": True,
            "config_locked": True,
            "evidence_level": "MEASURED_EVM",
            "synthetic_fixture": False,
            "environment": {
                "temperature_c": 20.0,
                "precipitation_state": "NONE",
            },
            "files": [],
        }
    )
    run_path.write_text(
        json.dumps(run) + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)
    assert result["preflight_status"] == "READY_FOR_COLLECTION"


def test_priority_two_selects_hil_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )

    assert manifest["item_id"] == "HIL_R2_BENCH_MEASURED"
    assert manifest["pack_kind"] == "hil_r2_bench"
    assert manifest["preflight"]["schema"] == "HIL-R2-JOB-PACK-PREFLIGHT-001"
    assert (tmp_path / "hil_r2_gate_config.json").is_file()
    assert (tmp_path / "preflight_config.json").is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert "timing_csv_has_no_samples" in result["preflight_warnings"]


def test_hil_gate_config_is_self_contained(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )

    gate = json.loads(
        (tmp_path / "hil_r2_gate_config.json").read_text(
            encoding="utf-8"
        )
    )

    assert gate["min_radar_imu_samples"] == 100
    assert gate["min_pps_samples"] == 30
    assert gate["max_missed_events"] == 0


def test_invalid_priority_rejected(tmp_path):
    try:
        build_job_pack(
            queue_fixture(),
            tmp_path,
            priority=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError expected")


def test_missing_manifest_is_invalid(tmp_path):
    result = validate_job_pack(tmp_path)
    assert result["status"] == "INVALID"
    assert "missing_job_manifest" in result["errors"]
