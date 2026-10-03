from copy import deepcopy
from pathlib import Path

from tools.evidence_status import load_json
from tools.measurement_readiness import (
    build_readiness,
)


MANIFEST = Path(
    "evidence/project_evidence_manifest.json"
)


def row_by_id(result, item_id):
    return next(
        row
        for row in result["items"]
        if row["item_id"] == item_id
    )


def test_current_project_readiness():
    result = build_readiness(
        load_json(MANIFEST)
    )

    assert result["schema"] == "MEASUREMENT-READINESS-001"
    assert result["status"] == "READY"

    ready = set(
        result[
            "ready_for_external_execution"
        ]
    )

    assert {
        "REFERENCE_RANGE_MEASURED",
        "M300_MEASURED",
        "ANT_D1_EM_REAL",
        "HIL_R2_BENCH_MEASURED",
        "CARRIER_REVIEW_A",
        "AWR_EVM_PROFILE_MEASURED",
    }.issubset(ready)

    blocked = set(
        result["blocked_items"]
    )

    assert "SYS_ERR_MEASURED" in blocked
    assert "ANT_D1_SIM_GATE_REAL" in blocked
    assert "PHYSICAL_ANT_MEASUREMENT" in blocked


def test_sys_err_waits_for_hil_r2_bench():
    result = build_readiness(
        load_json(MANIFEST)
    )

    row = row_by_id(
        result,
        "SYS_ERR_MEASURED",
    )

    assert (
        row["readiness"]
        == "BLOCKED_DEPENDENCY"
    )
    assert (
        "HIL_R2_BENCH_MEASURED"
        in row["dependencies_open"]
    )
    assert row["measurement_pack_kind"] == "sys_err"


def test_physical_antenna_waits_for_prototype_inputs():
    result = build_readiness(
        load_json(MANIFEST)
    )

    row = row_by_id(
        result,
        "PHYSICAL_ANT_MEASUREMENT",
    )

    assert (
        row["readiness"]
        == "BLOCKED_DEPENDENCY"
    )

    assert set(
        row["dependencies_open"]
    ) == {
        "M300_MEASURED",
        "ANT_D1_SIM_GATE_REAL",
        "SYS_ERR_MEASURED",
    }

    assert (
        row["measurement_pack_kind"]
        == "physical_antenna"
    )


def test_passing_hil_r2_unblocks_sys_err():
    manifest = deepcopy(
        load_json(MANIFEST)
    )

    for item in manifest["items"]:
        if (
            item["id"]
            == "HIL_R2_BENCH_MEASURED"
        ):
            item["status"] = "PASS"
            item["evidence_level"] = (
                "MEASURED_BENCH"
            )

    result = build_readiness(
        manifest
    )

    row = row_by_id(
        result,
        "SYS_ERR_MEASURED",
    )

    assert (
        row["readiness"]
        == "READY_FOR_EXTERNAL_EXECUTION"
    )


def test_closed_item_removed_from_ready_list():
    manifest = deepcopy(
        load_json(MANIFEST)
    )

    for item in manifest["items"]:
        if item["id"] == "M300_MEASURED":
            item["status"] = "PASS"
            item["evidence_level"] = (
                "MEASURED_EVM"
            )

    result = build_readiness(
        manifest
    )

    row = row_by_id(
        result,
        "M300_MEASURED",
    )

    assert row["readiness"] == "CLOSED"
    assert (
        "M300_MEASURED"
        not in result[
            "ready_for_external_execution"
        ]
    )
    assert (
        "M300_MEASURED"
        in result["closed_items"]
    )


def test_missing_tooling_blocks_action():
    manifest = deepcopy(
        load_json(MANIFEST)
    )

    manifest["items"] = [
        item
        for item in manifest["items"]
        if item["id"]
        != "M300_TOOLING"
    ]

    result = build_readiness(
        manifest
    )

    row = row_by_id(
        result,
        "M300_MEASURED",
    )

    assert (
        row["readiness"]
        == "BLOCKED_TOOLING"
    )
    assert (
        "M300_TOOLING"
        in row["tooling_missing"]
    )
