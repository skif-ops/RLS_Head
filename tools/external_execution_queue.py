from __future__ import annotations

import argparse
import json
from pathlib import Path


RESULT_SCHEMA = "EXTERNAL-EXECUTION-QUEUE-001"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _unlock_count(items: list[dict], candidate_id: str) -> int:
    count = 0
    for row in items:
        if row.get("readiness") != "BLOCKED_DEPENDENCY":
            continue
        deps = row.get("dependencies_open", [])
        if candidate_id in deps:
            count += 1
    return count


def build_queue(readiness: dict) -> dict:
    if readiness.get("schema") != "MEASUREMENT-READINESS-001":
        raise ValueError("unexpected readiness schema")
    if readiness.get("status") != "READY":
        raise ValueError("measurement readiness is not READY")

    items = readiness.get("items")
    if not isinstance(items, list):
        raise ValueError("readiness items must be a list")

    ready_rows = [
        row
        for row in items
        if isinstance(row, dict)
        and row.get("readiness") == "READY_FOR_EXTERNAL_EXECUTION"
    ]

    queue = []
    for row in ready_rows:
        item_id = str(row.get("item_id", ""))
        if not item_id:
            raise ValueError("ready row missing item_id")
        queue.append(
            {
                "item_id": item_id,
                "next_action": row.get("next_action"),
                "measurement_pack_kind": row.get(
                    "measurement_pack_kind"
                ),
                "requires_measured_evidence": bool(
                    row.get("requires_measured_evidence", False)
                ),
                "directly_unlocks": _unlock_count(
                    items, item_id
                ),
            }
        )

    queue.sort(
        key=lambda row: (
            -int(row["directly_unlocks"]),
            str(row["item_id"]),
        )
    )

    return {
        "schema": RESULT_SCHEMA,
        "status": "READY",
        "source_schema": readiness.get("schema"),
        "queue": queue,
        "notes": [
            (
                "Ordering is deterministic: items that directly unblock "
                "more currently blocked evidence come first; ties use item_id."
            ),
            (
                "This queue does not create evidence, authorize production, "
                "or alter any project evidence status."
            ),
            (
                "Execution remains external; completed artifacts must still "
                "pass their dedicated validators and promotion guards."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic external evidence execution queue"
    )
    parser.add_argument("readiness")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = build_queue(load_json(args.readiness))
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
