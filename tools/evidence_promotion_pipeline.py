from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.evidence_promote import promote_claim
from tools.evidence_status import load_json
from tools.external_evidence_ingest import ingest_bundle
from tools.external_execution_queue import build_queue
from tools.external_execution_recipe import build_recipes
from tools.measurement_readiness import build_readiness


RESULT_SCHEMA = "EVIDENCE-PROMOTION-PIPELINE-001"


def run_pipeline(
    *,
    project_manifest: dict,
    bundle: dict,
    bundle_root: str | Path,
) -> tuple[dict, dict | None]:
    ingest_result, claim = ingest_bundle(
        bundle,
        bundle_root=bundle_root,
    )

    result = {
        "schema": RESULT_SCHEMA,
        "status": "REJECTED",
        "ingest": ingest_result,
        "promotion": None,
        "readiness": None,
        "execution_queue": None,
        "execution_recipes": None,
        "notes": [
            (
                "The pipeline never mutates the authoritative manifest in place; "
                "it returns a candidate manifest only."
            ),
            (
                "Promotion remains subject to item-specific evidence_promote "
                "validation and provenance checks."
            ),
            (
                "The execution queue and recipes are derived only from the "
                "candidate readiness view and are not evidence."
            ),
        ],
    }

    if claim is None:
        return result, None

    promotion_result, candidate_manifest = promote_claim(
        project_manifest=project_manifest,
        claim=claim,
        repository_root=bundle_root,
    )
    result["promotion"] = promotion_result

    if not promotion_result.get("promotion_allowed"):
        return result, None

    readiness = build_readiness(candidate_manifest)
    queue = build_queue(readiness)

    result["readiness"] = readiness
    result["execution_queue"] = queue
    result["execution_recipes"] = build_recipes(queue)
    result["status"] = "CANDIDATE_READY"

    return result, candidate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run external bundle ingest, evidence promotion, readiness "
            "recalculation, next-action queue, and execution recipes"
        )
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--output-result", required=True)
    parser.add_argument("--output-manifest", required=True)
    args = parser.parse_args()

    result, candidate_manifest = run_pipeline(
        project_manifest=load_json(args.manifest),
        bundle=load_json(args.bundle),
        bundle_root=args.bundle_root,
    )

    Path(args.output_result).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if candidate_manifest is not None:
        Path(args.output_manifest).write_text(
            json.dumps(candidate_manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    print(result["status"])
    return 0 if candidate_manifest is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
