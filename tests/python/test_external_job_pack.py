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
    assert manifest["priority"] == 1
    assert manifest["pack_kind"] == "m300"
    assert manifest["result_schema"] == "M300-REPORT-001"

    assert (tmp_path / "job_manifest.json").is_file()
    assert (tmp_path / "execution_recipe.json").is_file()
    assert (tmp_path / "EXECUTION_CHECKLIST.txt").is_file()
    assert (
        tmp_path / "measurement_pack" / "range_samples.csv"
    ).is_file()
    assert (
        tmp_path / "measurement_pack" / "run_manifest.json"
    ).is_file()


def test_job_pack_validates_as_template_ready(tmp_path):
    build_job_pack(queue_fixture(), tmp_path)
    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert result["item_id"] == "M300_MEASURED"


def test_priority_two_selects_hil(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )

    assert manifest["item_id"] == "HIL_R2_BENCH_MEASURED"
    assert manifest["pack_kind"] == "hil_r2_bench"


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
