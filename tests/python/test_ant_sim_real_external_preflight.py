import json
from pathlib import Path

from tools.ant_sim_real_external_preflight import (
    evaluate_preflight,
)
from tools.external_execution_recipe import (
    build_recipes,
)


def write_json(
    path: Path,
    data: dict,
):
    path.write_text(
        json.dumps(data)
        + "\n",
        encoding="utf-8",
    )


def test_missing_inputs_wait_for_upstream(
    tmp_path,
):
    result = evaluate_preflight(
        map_validation=
            tmp_path / "map.json",
        mc_summary=
            tmp_path / "mc.json",
        revb=
            tmp_path / "revb.json",
    )

    assert (
        result["status"]
        == "WAITING_FOR_UPSTREAM"
    )
    assert (
        result["errors"]
        == []
    )


def test_ready_inputs_reach_gate_assembly(
    tmp_path,
):
    map_path = (
        tmp_path / "map.json"
    )
    mc_path = (
        tmp_path / "mc.json"
    )
    revb_path = (
        tmp_path / "revb.json"
    )

    write_json(
        map_path,
        {
            "schema":
                "ANT-D1-MAP-VALIDATION-001",
            "status":
                "DATA_READY",
        },
    )
    write_json(
        mc_path,
        {
            "schema":
                "ANT-D1-MC-SUMMARY-001",
            "status":
                "PASS",
        },
    )
    write_json(
        revb_path,
        {
            "schema":
                "RAD-LB-006-REVB",
            "status":
                "PROJECTED",
        },
    )

    result = evaluate_preflight(
        map_validation=
            map_path,
        mc_summary=
            mc_path,
        revb=
            revb_path,
    )

    assert (
        result["status"]
        == "READY_FOR_GATE_ASSEMBLY"
    )
    assert all(
        result[
            "input_ready"
        ].values()
    )


def test_explicit_mc_fail_blocks(
    tmp_path,
):
    map_path = (
        tmp_path / "map.json"
    )
    mc_path = (
        tmp_path / "mc.json"
    )
    revb_path = (
        tmp_path / "revb.json"
    )

    write_json(
        map_path,
        {
            "schema":
                "ANT-D1-MAP-VALIDATION-001",
            "status":
                "DATA_READY",
        },
    )
    write_json(
        mc_path,
        {
            "schema":
                "ANT-D1-MC-SUMMARY-001",
            "status":
                "FAIL",
        },
    )
    write_json(
        revb_path,
        {
            "schema":
                "RAD-LB-006-REVB",
            "status":
                "PROJECTED",
        },
    )

    result = evaluate_preflight(
        map_validation=
            map_path,
        mc_summary=
            mc_path,
        revb=
            revb_path,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "mc_summary:fail"
        in result["errors"]
    )


def test_wrong_schema_blocks(
    tmp_path,
):
    path = (
        tmp_path / "map.json"
    )
    write_json(
        path,
        {
            "schema":
                "WRONG",
            "status":
                "DATA_READY",
        },
    )

    result = evaluate_preflight(
        map_validation=
            path,
        mc_summary=
            tmp_path / "mc.json",
        revb=
            tmp_path / "revb.json",
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "map_validation:unexpected_schema"
        in result["errors"]
    )


def test_execution_recipe_supports_real_ant_sim():
    queue = {
        "schema":
            "EXTERNAL-EXECUTION-QUEUE-001",
        "status":
            "READY",
        "queue": [
            {
                "item_id":
                    "ANT_D1_SIM_GATE_REAL",
                "next_action":
                    "ASSEMBLE_REAL_ANT_SIM_GATE",
                "directly_unlocks":
                    1,
            }
        ],
    }

    result = build_recipes(
        queue
    )

    assert (
        result["status"]
        == "READY"
    )
    row = result[
        "recipes"
    ][0]
    assert (
        row["result_schema"]
        == "ANT-SIM-GATE-001"
    )
    assert (
        "--validation"
        in row["validator_command"]
    )
