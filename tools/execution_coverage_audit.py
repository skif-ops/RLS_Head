from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.external_execution_recipe import (
    RECIPES,
    build_recipes,
)
from tools.external_job_pack import (
    build_job_pack,
    validate_job_pack,
)
from tools.measurement_readiness import PLAN


SCHEMA = "EXECUTION-COVERAGE-AUDIT-001"


def _coverage_queue() -> dict:
    rows = []

    for item_id, spec in PLAN.items():
        rows.append(
            {
                "item_id": item_id,
                "next_action": spec["action"],
                "directly_unlocks": 0,
            }
        )

    return {
        "schema": "EXTERNAL-EXECUTION-QUEUE-001",
        "status": "READY",
        "queue": rows,
    }


def build_audit(
    *,
    output_root: str | Path,
) -> dict:
    root = Path(output_root)
    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    queue = _coverage_queue()
    recipe_result = build_recipes(
        queue
    )

    missing_recipes = sorted(
        item_id
        for item_id in PLAN
        if item_id not in RECIPES
    )

    rows = []
    errors: list[str] = []

    for priority, queue_row in enumerate(
        queue["queue"],
        start=1,
    ):
        item_id = queue_row[
            "item_id"
        ]

        if item_id in missing_recipes:
            rows.append(
                {
                    "item_id": item_id,
                    "priority": priority,
                    "recipe_status": "UNSUPPORTED",
                    "job_pack_status": None,
                    "preflight_status": None,
                }
            )
            continue

        directory = (
            root
            / (
                f"{priority:02d}-"
                f"{item_id.lower()}"
            )
        )

        try:
            job_manifest = build_job_pack(
                queue,
                directory,
                priority=priority,
            )
            validation = (
                validate_job_pack(
                    directory
                )
            )
        except Exception as exc:
            errors.append(
                f"{item_id}:job_pack:{type(exc).__name__}"
            )
            rows.append(
                {
                    "item_id": item_id,
                    "priority": priority,
                    "recipe_status": "READY",
                    "job_pack_status": "ERROR",
                    "preflight_status": None,
                }
            )
            continue

        preflight = job_manifest.get(
            "preflight"
        )
        preflight_status = (
            validation.get(
                "preflight_status"
            )
        )

        if (
            validation.get("status")
            != "TEMPLATE_READY"
        ):
            errors.append(
                f"{item_id}:job_pack_not_template_ready"
            )

        if preflight is None:
            errors.append(
                f"{item_id}:missing_preflight"
            )

        if preflight_status is None:
            errors.append(
                f"{item_id}:missing_preflight_status"
            )

        rows.append(
            {
                "item_id": item_id,
                "priority": priority,
                "recipe_status": "READY",
                "result_schema": (
                    job_manifest.get(
                        "result_schema"
                    )
                ),
                "pack_kind": (
                    job_manifest.get(
                        "pack_kind"
                    )
                ),
                "job_pack_status": (
                    validation.get(
                        "status"
                    )
                ),
                "preflight_status": (
                    preflight_status
                ),
                "preflight_errors": (
                    validation.get(
                        "preflight_errors",
                        [],
                    )
                ),
                "preflight_warnings": (
                    validation.get(
                        "preflight_warnings",
                        [],
                    )
                ),
            }
        )

    if (
        recipe_result.get(
            "status"
        )
        != "READY"
    ):
        errors.append(
            "recipe_catalog_not_ready"
        )

    if missing_recipes:
        errors.extend(
            f"missing_recipe:{item_id}"
            for item_id
            in missing_recipes
        )

    status = (
        "PASS"
        if not errors
        else "FAIL"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "plan_item_count": len(
            PLAN
        ),
        "covered_item_count": sum(
            1
            for row in rows
            if (
                row.get(
                    "recipe_status"
                )
                == "READY"
                and row.get(
                    "job_pack_status"
                )
                == "TEMPLATE_READY"
                and row.get(
                    "preflight_status"
                )
                is not None
            )
        ),
        "missing_recipes": (
            missing_recipes
        ),
        "errors": sorted(
            set(errors)
        ),
        "rows": rows,
        "notes": [
            (
                "This is a tooling-coverage audit only. "
                "It deliberately materializes template job packs for "
                "blocked as well as ready evidence items."
            ),
            (
                "PASS does not mean any external evidence item is measured "
                "or closed."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit recipe/job-pack/preflight coverage "
            "for every measurement-readiness PLAN item"
        )
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

    result = build_audit(
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

    return (
        0
        if result["status"]
        == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
