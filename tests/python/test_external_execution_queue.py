from copy import deepcopy

import pytest

from tools.external_execution_queue import build_queue
from tools.measurement_readiness import build_readiness
from tools.evidence_status import load_json


MANIFEST = "evidence/project_evidence_manifest.json"


def current_readiness():
    return build_readiness(load_json(MANIFEST))


def test_queue_is_ready_and_deterministic():
    result = build_queue(current_readiness())

    assert result["schema"] == "EXTERNAL-EXECUTION-QUEUE-001"
    assert result["status"] == "READY"

    ids = [row["item_id"] for row in result["queue"]]
    assert set(ids) == set(
        current_readiness()["ready_for_external_execution"]
    )

    unlocks = [row["directly_unlocks"] for row in result["queue"]]
    assert unlocks == sorted(unlocks, reverse=True)


def test_current_m300_has_dependency_unlock_value():
    result = build_queue(current_readiness())
    row = next(
        row
        for row in result["queue"]
        if row["item_id"] == "M300_MEASURED"
    )

    assert row["directly_unlocks"] >= 1


def test_ties_are_ordered_by_item_id():
    readiness = current_readiness()
    readiness = deepcopy(readiness)

    for row in readiness["items"]:
        row["dependencies_open"] = []

    result = build_queue(readiness)
    ids = [row["item_id"] for row in result["queue"]]
    assert ids == sorted(ids)


def test_closed_item_is_not_queued():
    readiness = current_readiness()
    readiness = deepcopy(readiness)

    for row in readiness["items"]:
        if row["item_id"] == "M300_MEASURED":
            row["readiness"] = "CLOSED"

    result = build_queue(readiness)
    assert "M300_MEASURED" not in {
        row["item_id"] for row in result["queue"]
    }


def test_invalid_readiness_rejected():
    readiness = current_readiness()
    readiness = deepcopy(readiness)
    readiness["status"] = "INVALID"

    with pytest.raises(ValueError):
        build_queue(readiness)


def test_wrong_schema_rejected():
    readiness = current_readiness()
    readiness = deepcopy(readiness)
    readiness["schema"] = "WRONG"

    with pytest.raises(ValueError):
        build_queue(readiness)
