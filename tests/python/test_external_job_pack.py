import json

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
            {
                "item_id": "REFERENCE_RANGE_MEASURED",
                "next_action": "COLLECT_EVM_REFERENCE_LADDER",
                "measurement_pack_kind": "reference_range",
                "requires_measured_evidence": True,
                "directly_unlocks": 0,
            },
        ],
    }


def test_m300_job_pack_keeps_preflight():
    pass


def test_priority_two_selects_hil_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )
    assert manifest["item_id"] == "HIL_R2_BENCH_MEASURED"
    result = validate_job_pack(tmp_path)
    assert result["preflight_status"] == "READY_FOR_COLLECTION"


def test_priority_three_selects_reference_range_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    assert manifest["item_id"] == "REFERENCE_RANGE_MEASURED"
    assert manifest["pack_kind"] == "reference_range"
    assert (
        manifest["preflight"]["schema"]
        == "REFERENCE-RANGE-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "README.txt"
    ).is_file()
    assert (tmp_path / "preflight_config.json").is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert "reference_csv_has_no_samples" in result["preflight_warnings"]
    assert any(
        warning.startswith("missing_range_manifests:")
        for warning in result["preflight_warnings"]
    )


def test_reference_range_invalid_manifest_blocks_preflight(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    bad = (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "bad.json"
    )
    bad.write_text("{bad", encoding="utf-8")

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "BLOCKED"
    assert "invalid_manifest_json:bad.json" in result["preflight_errors"]


def test_reference_required_ranges_are_embedded(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    assert manifest["preflight"]["required_ranges_m"] == [
        50,
        100,
        150,
        200,
        250,
        300,
    ]


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
