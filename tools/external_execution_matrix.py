from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evidence_status import load_json
from tools.external_execution_queue import build_queue
from tools.external_job_pack import (
    build_job_pack,
    validate_job_pack,
)
from tools.measurement_readiness import build_readiness


SCHEMA = "EXTERNAL-EXECUTION-MATRIX-001"


def _directory_name(
    priority: int,
    item_id: str,
) -> str:
    safe = "".join(
        ch.lower()
        if ch.isalnum()
        else "-"
        for ch in item_id
    ).strip("-")
    return (
        f"{priority:02d}-"
        f"{safe}"
    )


def build_matrix(
    project_manifest: dict,
    *,
    output_root: str | Path,
) -> dict:
    readiness = build_readiness(
        project_manifest
    )
    queue = build_queue(
        readiness
    )

    root = Path(
        output_root
    )
    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for priority, queue_row in enumerate(
        queue.get(
            "queue",
            [],
        ),
        start=1,
    ):
        item_id = str(
            queue_row.get(
                "item_id",
                "",
            )
        )

        directory = (
            root
            / _directory_name(
                priority,
                item_id,
            )
        )

        job_manifest = (
            build_job_pack(
                queue,
                directory,
                priority=priority,
            )
        )

        validation = (
            validate_job_pack(
                directory
            )
        )

        rows.append(
            {
                "priority":
                    priority,
                "item_id":
                    item_id,
                "directly_unlocks":
                    queue_row.get(
                        "directly_unlocks",
                        0,
                    ),
                "job_pack_dir":
                    str(
                        directory
                    ),
                "job_pack_status":
                    validation.get(
                        "status"
                    ),
                "preflight_status":
                    validation.get(
                        "preflight_status"
                    ),
                "preflight_errors":
                    validation.get(
                        "preflight_errors",
                        [],
                    ),
                "preflight_warnings":
                    validation.get(
                        "preflight_warnings",
                        [],
                    ),
                "pack_kind":
                    job_manifest.get(
                        "pack_kind"
                    ),
            }
        )

    return {
        "schema":
            SCHEMA,
        "status":
            "READY",
        "readiness_schema":
            readiness.get(
                "schema"
            ),
        "queue_schema":
            queue.get(
                "schema"
            ),
        "queue_depth":
            len(rows),
        "rows":
            rows,
        "summary": {
            "template_ready":
                sum(
                    1
                    for row in rows
                    if row[
                        "job_pack_status"
                    ]
                    == "TEMPLATE_READY"
                ),
            "preflight_ready":
                sum(
                    1
                    for row in rows
                    if row[
                        "preflight_status"
                    ]
                    in {
                        "READY_FOR_COLLECTION",
                        "READY_FOR_SOLVER_EXECUTION",
                        "READY_FOR_CAD_REVIEW_EXECUTION",
                    }
                ),
            "preflight_blocked":
                sum(
                    1
                    for row in rows
                    if row[
                        "preflight_status"
                    ]
                    == "BLOCKED"
                ),
            "waiting_dependency":
                sum(
                    1
                    for row in rows
                    if str(
                        row[
                            "preflight_status"
                        ]
                    ).startswith(
                        "WAITING_"
                    )
                ),
        },
        "notes": [
            (
                "The matrix is derived from the authoritative evidence manifest "
                "but does not modify it."
            ),
            (
                "Materialized job packs and preflight states are workflow "
                "artifacts, not measured evidence."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize and validate every current "
            "READY_FOR_EXTERNAL_EXECUTION job pack"
        )
    )
    parser.add_argument(
        "--manifest",
        default=(
            "evidence/"
            "project_evidence_manifest.json"
        ),
    )
    parser.add_argument(
        "--output-root",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = build_matrix(
        load_json(
            args.manifest
        ),
        output_root=
            args.output_root,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        result["status"]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
