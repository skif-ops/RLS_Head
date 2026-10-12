import pytest

from tools.external_dispatch_plan import build_dispatch_plan


def matrix_fixture():
    return {
        "schema": "EXTERNAL-EXECUTION-MATRIX-001",
        "status": "READY",
        "rows": [
            {
                "priority": 1,
                "item_id": "M300_MEASURED",
                "directly_unlocks": 2,
                "job_pack_status": "TEMPLATE_READY",
                "preflight_status": "BLOCKED",
                "preflight_errors": ["missing_or_placeholder:run_id"],
                "preflight_warnings": [],
                "job_pack_dir": "01-m300",
            },
            {
                "priority": 2,
                "item_id": "ANT_D1_EM_REAL",
                "directly_unlocks": 1,
                "job_pack_status": "TEMPLATE_READY",
                "preflight_status": "BLOCKED",
                "preflight_errors": ["missing_input_file:model_input"],
                "preflight_warnings": [],
                "job_pack_dir": "02-ant-em",
            },
            {
                "priority": 3,
                "item_id": "HIL_R2_BENCH_MEASURED",
                "directly_unlocks": 1,
                "job_pack_status": "TEMPLATE_READY",
                "preflight_status": "READY_FOR_COLLECTION",
                "preflight_errors": [],
                "preflight_warnings": ["timing_csv_has_no_samples"],
                "job_pack_dir": "03-hil-r2",
            },
            {
                "priority": 4,
                "item_id": "REFERENCE_RANGE_MEASURED",
                "directly_unlocks": 0,
                "job_pack_status": "TEMPLATE_READY",
                "preflight_status": "READY_FOR_COLLECTION",
                "preflight_errors": [],
                "preflight_warnings": ["reference_csv_has_no_samples"],
                "job_pack_dir": "04-reference",
            },
        ],
    }


def test_dispatchable_items_move_ahead_of_blocked_strategic_items():
    result = build_dispatch_plan(matrix_fixture())

    assert result["status"] == "READY"
    assert result["dispatch_now"] == [
        "HIL_R2_BENCH_MEASURED",
        "REFERENCE_RANGE_MEASURED",
    ]
    assert result["next_dispatch_item"] == "HIL_R2_BENCH_MEASURED"

    ids = [
        row["item_id"]
        for row in result["rows"]
    ]
    assert ids[:2] == [
        "HIL_R2_BENCH_MEASURED",
        "REFERENCE_RANGE_MEASURED",
    ]


def test_unlock_value_breaks_ties_inside_same_dispatch_class():
    matrix = matrix_fixture()
    matrix["rows"][3]["directly_unlocks"] = 3

    result = build_dispatch_plan(matrix)

    assert result["dispatch_now"][0] == "REFERENCE_RANGE_MEASURED"


def test_waiting_dependency_precedes_blocked():
    matrix = matrix_fixture()
    matrix["rows"][1]["preflight_status"] = "WAITING_FOR_M300"

    result = build_dispatch_plan(matrix)

    ant = next(
        row
        for row in result["rows"]
        if row["item_id"] == "ANT_D1_EM_REAL"
    )
    m300 = next(
        row
        for row in result["rows"]
        if row["item_id"] == "M300_MEASURED"
    )

    assert ant["dispatch_class"] == "WAITING_DEPENDENCY"
    assert ant["dispatch_priority"] < m300["dispatch_priority"]


def test_summary_counts_classes():
    result = build_dispatch_plan(matrix_fixture())

    assert result["summary"] == {
        "dispatch_now": 2,
        "waiting_dependency": 0,
        "prep_required": 2,
        "unknown": 0,
    }


def test_wrong_schema_rejected():
    matrix = matrix_fixture()
    matrix["schema"] = "WRONG"

    with pytest.raises(ValueError):
        build_dispatch_plan(matrix)
