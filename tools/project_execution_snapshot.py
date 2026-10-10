from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evidence_status import load_json
from tools.external_execution_queue import build_queue
from tools.external_execution_recipe import build_recipes
from tools.external_job_pack import build_job_pack, validate_job_pack
from tools.measurement_readiness import build_readiness


SCHEMA = "PROJECT-EXECUTION-SNAPSHOT-001"


def build_snapshot(
    project_manifest: dict,
    *,
    job_pack_dir: str | Path | None = None,
    job_pack_priority: int = 1,
) -> dict:
    readiness = build_readiness(project_manifest)
    queue = build_queue(readiness)
    recipes = build_recipes(queue)

    result = {
        "schema": SCHEMA,
        "status": "READY",
        "evidence_schema": project_manifest.get("schema"),
        "readiness": readiness,
        "execution_queue": queue,
        "execution_recipes": recipes,
        "next_job_pack": None,
        "next_job_pack_validation": None,
        "summary": {
            "ready_for_external_execution": len(
                readiness.get("ready_for_external_execution", [])
            ),
            "blocked_items": len(
                readiness.get("blocked_items", [])
            ),
            "closed_items": len(
                readiness.get("closed_items", [])
            ),
            "queue_depth": len(queue.get("queue", [])),
        },
        "notes": [
            "Snapshot is read-only with respect to authoritative project evidence.",
            "Queue, recipes, and job packs are workflow artifacts, not measured evidence.",
        ],
    }

    if job_pack_dir is not None and queue.get("queue"):
        job_pack = build_job_pack(
            queue,
            job_pack_dir,
            priority=job_pack_priority,
        )
        result["next_job_pack"] = job_pack
        result["next_job_pack_validation"] = validate_job_pack(
            job_pack_dir
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only project execution snapshot from the "
            "authoritative evidence manifest"
        )
    )
    parser.add_argument(
        "--manifest",
        default="evidence/project_evidence_manifest.json",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-job-pack-dir")
    parser.add_argument("--job-pack-priority", type=int, default=1)
    args = parser.parse_args()

    result = build_snapshot(
        load_json(args.manifest),
        job_pack_dir=args.output_job_pack_dir,
        job_pack_priority=args.job_pack_priority,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
