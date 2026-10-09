from tools.external_execution_recipe import build_recipes


def queue_fixture():
    return {
        "schema": "EXTERNAL-EXECUTION-QUEUE-001",
        "status": "READY",
        "queue": [
            {
                "item_id": "HIL_R2_BENCH_MEASURED",
                "next_action": "COLLECT_HIL_R2_BENCH",
                "directly_unlocks": 1,
            },
            {
                "item_id": "M300_MEASURED",
                "next_action": "COLLECT_EVM_M300",
                "directly_unlocks": 1,
            },
        ],
    }


def test_builds_ordered_recipes():
    result = build_recipes(queue_fixture())
    assert result["status"] == "READY"
    assert [r["priority"] for r in result["recipes"]] == [1, 2]
    assert result["recipes"][0]["item_id"] == "HIL_R2_BENCH_MEASURED"
    assert result["recipes"][0]["result_schema"] == "HIL-R2-BENCH-EVIDENCE-001"


def test_m300_recipe_has_expected_result_schema():
    result = build_recipes(queue_fixture())
    row = next(r for r in result["recipes"] if r["item_id"] == "M300_MEASURED")
    assert row["result_schema"] == "M300-REPORT-001"
    assert row["pack_kind"] == "m300"


def test_unknown_item_is_partial():
    queue = queue_fixture()
    queue["queue"].append(
        {
            "item_id": "UNKNOWN_ITEM",
            "next_action": "DO_SOMETHING",
            "directly_unlocks": 0,
        }
    )
    result = build_recipes(queue)
    assert result["status"] == "PARTIAL"
    row = result["recipes"][-1]
    assert row["status"] == "UNSUPPORTED"


def test_wrong_schema_rejected():
    queue = queue_fixture()
    queue["schema"] = "WRONG"
    try:
        build_recipes(queue)
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError expected")
