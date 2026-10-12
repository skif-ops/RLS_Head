from tools.execution_coverage_audit import (
    build_audit,
)
from tools.measurement_readiness import PLAN


def test_all_plan_items_have_execution_coverage(
    tmp_path,
):
    result = build_audit(
        output_root=
            tmp_path / "coverage",
    )

    assert (
        result["schema"]
        == "EXECUTION-COVERAGE-AUDIT-001"
    )
    assert (
        result["status"]
        == "PASS"
    )
    assert (
        result["plan_item_count"]
        == len(PLAN)
    )
    assert (
        result["covered_item_count"]
        == len(PLAN)
    )
    assert (
        result["missing_recipes"]
        == []
    )
    assert (
        result["errors"]
        == []
    )


def test_every_coverage_row_has_job_pack_and_preflight(
    tmp_path,
):
    result = build_audit(
        output_root=
            tmp_path / "coverage",
    )

    assert (
        len(result["rows"])
        == len(PLAN)
    )

    for row in result[
        "rows"
    ]:
        assert (
            row["recipe_status"]
            == "READY"
        )
        assert (
            row["job_pack_status"]
            == "TEMPLATE_READY"
        )
        assert (
            row["preflight_status"]
            is not None
        )


def test_dependency_gated_items_are_covered_not_promoted(
    tmp_path,
):
    result = build_audit(
        output_root=
            tmp_path / "coverage",
    )

    by_id = {
        row["item_id"]:
            row
        for row in result[
            "rows"
        ]
    }

    assert (
        by_id[
            "ANT_D1_SIM_GATE_REAL"
        ][
            "preflight_status"
        ]
        == "WAITING_FOR_UPSTREAM"
    )

    assert (
        by_id[
            "SYS_ERR_MEASURED"
        ][
            "preflight_status"
        ]
        == "WAITING_FOR_HIL_R2"
    )

    assert (
        by_id[
            "PHYSICAL_ANT_MEASUREMENT"
        ][
            "preflight_status"
        ]
        == "BLOCKED"
    )
