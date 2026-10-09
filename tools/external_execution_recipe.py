from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "EXTERNAL-EXECUTION-RECIPE-001"

RECIPES = {
    "REFERENCE_RANGE_MEASURED": {
        "collect": ["reference_range.csv", "6 x EVM-RUN-MANIFEST-001"],
        "validate": "python -m tools.reference_range reference_range.csv --output result.json",
        "result_schema": "REFERENCE-RANGE-RESULT-001",
        "pack_kind": "reference_range",
    },
    "M300_MEASURED": {
        "collect": ["range_samples.csv", "EVM-RUN-MANIFEST-001 @ 300 m / 0.01 m^2"],
        "validate": "python -m tools.range_analysis range_samples.csv --output result.json",
        "result_schema": "M300-REPORT-001",
        "pack_kind": "m300",
    },
    "ANT_D1_EM_REAL": {
        "collect": [
            "solver export",
            "model input",
            "material definition",
            "antenna map",
            "ANT-D1-EM-MANIFEST-001",
        ],
        "validate": (
            "python -m tools.ant_em_evidence --manifest ant_em_manifest.json "
            "--map-config <MAP_CONFIG> --repository-root . --output result.json"
        ),
        "result_schema": "ANT-D1-EM-EVIDENCE-001",
        "pack_kind": None,
    },
    "HIL_R2_BENCH_MEASURED": {
        "collect": ["timing_capture.csv"],
        "validate": (
            "python -m tools.hil_host.r2_evidence timing_capture.csv "
            "--config config/hil_r2_evidence_evt.json --output result.json"
        ),
        "result_schema": "HIL-R2-BENCH-EVIDENCE-001",
        "pack_kind": "hil_r2_bench",
    },
    "CARRIER_REVIEW_A": {
        "collect": [
            "KiCad schematic",
            "ERC JSON",
            "pinmap CSV",
            "BOM CSV",
            "CARRIER-REVIEW-A-MANIFEST-001",
        ],
        "validate": (
            "python -m tools.carrier_review_a carrier_review_a_manifest.json "
            "--repository-root . --output result.json"
        ),
        "result_schema": "CARRIER-REVIEW-A-RESULT-001",
        "pack_kind": None,
    },
    "AWR_EVM_PROFILE_MEASURED": {
        "collect": [
            "profile_metrics.csv",
            "validated EVM-RUN-MANIFEST-001 for TRACK/LR1/LR2/LRX",
        ],
        "validate": (
            "python -m tools.evm_profile_gate profile_metrics.csv "
            "--manifest-dir <MANIFEST_DIR> --output result.json"
        ),
        "result_schema": "EVM-PROFILE-RESULT-001",
        "pack_kind": "evm_profile",
    },
    "SYS_ERR_MEASURED": {
        "collect": ["sys_err_cells.csv", "SYS-ERR-MEASUREMENT-MANIFEST-001"],
        "validate": (
            "python -m tools.sys_err_measured_gate --manifest sys_err_manifest.json "
            "--repository-root . --output result.json"
        ),
        "result_schema": "SYS-ERR-GATE-001",
        "pack_kind": "sys_err",
    },
    "PHYSICAL_ANT_MEASUREMENT": {
        "collect": [
            "antenna_measurement.csv",
            "ANT-MEASUREMENT-MANIFEST-001",
        ],
        "validate": (
            "python -m tools.physical_antenna_measurement "
            "antenna_measurement_manifest.json --repository-root . "
            "--output result.json"
        ),
        "result_schema": "ANT-MEASUREMENT-001",
        "pack_kind": "physical_antenna",
    },
}


def build_recipes(queue: dict) -> dict:
    if queue.get("schema") != "EXTERNAL-EXECUTION-QUEUE-001":
        raise ValueError("unexpected execution queue schema")

    rows = queue.get("queue")
    if not isinstance(rows, list):
        raise ValueError("execution queue must contain queue[]")

    recipes = []

    for priority, row in enumerate(rows, start=1):
        item_id = str(row.get("item_id", "")).strip()
        spec = RECIPES.get(item_id)
        if spec is None:
            recipes.append(
                {
                    "priority": priority,
                    "item_id": item_id,
                    "status": "UNSUPPORTED",
                    "errors": ["missing_recipe"],
                }
            )
            continue

        recipes.append(
            {
                "priority": priority,
                "item_id": item_id,
                "status": "READY",
                "next_action": row.get("next_action"),
                "directly_unlocks": row.get("directly_unlocks", 0),
                "pack_kind": spec["pack_kind"],
                "collect": list(spec["collect"]),
                "validator_command": spec["validate"],
                "result_schema": spec["result_schema"],
                "continuation": [
                    "build EXTERNAL-EVIDENCE-BUNDLE-001",
                    "run tools.external_evidence_ingest",
                    "run tools.evidence_promotion_pipeline",
                    "review candidate manifest before merge",
                ],
            }
        )

    return {
        "schema": SCHEMA,
        "status": (
            "READY"
            if all(row["status"] == "READY" for row in recipes)
            else "PARTIAL"
        ),
        "recipes": recipes,
        "notes": [
            "Recipes describe evidence execution only; they do not create measurements.",
            "No authoritative project evidence status is modified by this report.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build execution recipes from EXTERNAL-EXECUTION-QUEUE-001"
    )
    parser.add_argument("queue")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    result = build_recipes(queue)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
