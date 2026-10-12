from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "EXTERNAL-DISPATCH-PLAN-001"

READY_STATES = {
    "READY_FOR_COLLECTION",
    "READY_FOR_SOLVER_EXECUTION",
    "READY_FOR_CAD_REVIEW_EXECUTION",
    "READY_FOR_GATE_ASSEMBLY",
}


def _dispatch_class(preflight_status: object) -> str:
    status = str(preflight_status or "")

    if status in READY_STATES:
        return "DISPATCH_NOW"

    if status.startswith("WAITING_"):
        return "WAITING_DEPENDENCY"

    if status == "BLOCKED":
        return "PREP_REQUIRED"

    return "UNKNOWN"


def _rank(dispatch_class: str) -> int:
    return {
        "DISPATCH_NOW": 0,
        "WAITING_DEPENDENCY": 1,
        "PREP_REQUIRED": 2,
        "UNKNOWN": 3,
    }[dispatch_class]


def build_dispatch_plan(matrix: dict) -> dict:
    if matrix.get("schema") != "EXTERNAL-EXECUTION-MATRIX-001":
        raise ValueError("unexpected execution matrix schema")

    rows = matrix.get("rows")
    if not isinstance(rows, list):
        raise ValueError("execution matrix must contain rows[]")

    planned = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("execution matrix row must be an object")

        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            raise ValueError("execution matrix row missing item_id")

        dispatch_class = _dispatch_class(
            row.get("preflight_status")
        )

        planned.append(
            {
                "item_id": item_id,
                "strategic_priority": int(
                    row.get("priority", 0)
                ),
                "directly_unlocks": int(
                    row.get("directly_unlocks", 0)
                ),
                "dispatch_class": dispatch_class,
                "preflight_status": row.get(
                    "preflight_status"
                ),
                "job_pack_status": row.get(
                    "job_pack_status"
                ),
                "job_pack_dir": row.get(
                    "job_pack_dir"
                ),
                "preflight_errors": list(
                    row.get("preflight_errors", [])
                ),
                "preflight_warnings": list(
                    row.get("preflight_warnings", [])
                ),
            }
        )

    planned.sort(
        key=lambda row: (
            _rank(row["dispatch_class"]),
            -int(row["directly_unlocks"]),
            int(row["strategic_priority"]),
            row["item_id"],
        )
    )

    for index, row in enumerate(planned, start=1):
        row["dispatch_priority"] = index

    dispatch_now = [
        row["item_id"]
        for row in planned
        if row["dispatch_class"] == "DISPATCH_NOW"
    ]

    return {
        "schema": SCHEMA,
        "status": "READY",
        "source_schema": matrix.get("schema"),
        "dispatch_now": dispatch_now,
        "next_dispatch_item": (
            dispatch_now[0]
            if dispatch_now
            else None
        ),
        "rows": planned,
        "summary": {
            "dispatch_now": sum(
                row["dispatch_class"] == "DISPATCH_NOW"
                for row in planned
            ),
            "waiting_dependency": sum(
                row["dispatch_class"] == "WAITING_DEPENDENCY"
                for row in planned
            ),
            "prep_required": sum(
                row["dispatch_class"] == "PREP_REQUIRED"
                for row in planned
            ),
            "unknown": sum(
                row["dispatch_class"] == "UNKNOWN"
                for row in planned
            ),
        },
        "notes": [
            (
                "Dispatch priority reflects immediate executability first, "
                "then dependency-unlock value and strategic queue priority."
            ),
            (
                "The strategic execution queue is not modified; this is a "
                "read-only operational view."
            ),
            (
                "DISPATCH_NOW means the template/preflight is ready to begin "
                "external execution, not that evidence has passed."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immediate external dispatch plan from "
            "EXTERNAL-EXECUTION-MATRIX-001"
        )
    )
    parser.add_argument("matrix")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    matrix = json.loads(
        Path(args.matrix).read_text(encoding="utf-8")
    )
    result = build_dispatch_plan(matrix)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
