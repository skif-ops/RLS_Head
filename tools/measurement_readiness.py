from __future__ import annotations

import argparse
import json
from pathlib import Path


RESULT_SCHEMA = "MEASUREMENT-READINESS-001"

PLAN = {
    "REFERENCE_RANGE_MEASURED": {
        "action": "COLLECT_EVM_REFERENCE_LADDER",
        "pack_kind": "reference_range",
        "tooling": ["M300_TOOLING"],
        "dependencies": [],
    },
    "M300_MEASURED": {
        "action": "COLLECT_EVM_M300",
        "pack_kind": "m300",
        "tooling": ["M300_TOOLING"],
        "dependencies": [],
    },
    "ANT_D1_EM_REAL": {
        "action": "RUN_D1_EM_SOLVER",
        "pack_kind": None,
        "tooling": ["ANT_D1_EM_TOOLING"],
        "dependencies": [],
    },
    "ANT_D1_SIM_GATE_REAL": {
        "action": "ASSEMBLE_REAL_ANT_SIM_GATE",
        "pack_kind": None,
        "tooling": [
            "ANT_D1_EM_TOOLING",
            "RAD_LB_PIPELINE",
        ],
        "dependencies": [
            "ANT_D1_EM_REAL",
            "M300_MEASURED",
        ],
    },
    "HIL_R2_BENCH_MEASURED": {
        "action": "COLLECT_HIL_R2_BENCH",
        "pack_kind": "hil_r2_bench",
        "tooling": [
            "HIL_R2_LOGIC",
            "TIME_SERVICE_LOGIC",
        ],
        "dependencies": [],
    },
    "SYS_ERR_MEASURED": {
        "action": "ASSEMBLE_MEASURED_SYS_ERR",
        "pack_kind": "sys_err",
        "tooling": [
            "SYS_ERR_MEASURED_TOOLING",
        ],
        "dependencies": [
            "HIL_R2_BENCH_MEASURED",
        ],
    },
    "CARRIER_REVIEW_A": {
        "action": "CAPTURE_KICAD_AND_RUN_REVIEW_A",
        "pack_kind": None,
        "tooling": [
            "CARRIER_DESIGN_INPUTS",
            "CARRIER_REVIEW_A_TOOLING",
        ],
        "dependencies": [],
    },
    "AWR_EVM_PROFILE_MEASURED": {
        "action": "COLLECT_EVM_PROFILE_MATRIX",
        "pack_kind": "evm_profile",
        "tooling": [
            "AWR_EVM_PROFILE_TOOLING",
        ],
        "dependencies": [],
    },
    "PHYSICAL_ANT_MEASUREMENT": {
        "action": "MEASURE_PHYSICAL_ANTENNA",
        "pack_kind": "physical_antenna",
        "tooling": [
            "PHYSICAL_ANT_MEASUREMENT_TOOLING",
        ],
        "dependencies": [
            "M300_MEASURED",
            "ANT_D1_SIM_GATE_REAL",
            "SYS_ERR_MEASURED",
        ],
    },
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_readiness(manifest: dict) -> dict:
    if manifest.get("schema") != "PROJECT-EVIDENCE-MANIFEST-001":
        raise ValueError("unexpected project evidence manifest schema")

    items = manifest.get("items")

    if not isinstance(items, list):
        raise ValueError("project evidence items must be a list")

    by_id = {
        str(item.get("id", "")): item
        for item in items
        if isinstance(item, dict)
        and str(item.get("id", "")).strip()
    }

    errors: list[str] = []
    rows = []

    for item_id, spec in PLAN.items():
        item = by_id.get(item_id)

        if item is None:
            errors.append(
                f"missing_project_item:{item_id}"
            )
            continue

        status = str(
            item.get("status", "OPEN")
        )

        tooling_missing = [
            tooling_id
            for tooling_id in spec["tooling"]
            if tooling_id not in by_id
            or str(
                by_id[tooling_id].get(
                    "status",
                    "OPEN",
                )
            )
            != "PASS"
        ]

        dependency_open = [
            dependency_id
            for dependency_id in spec[
                "dependencies"
            ]
            if dependency_id not in by_id
            or str(
                by_id[dependency_id].get(
                    "status",
                    "OPEN",
                )
            )
            != "PASS"
        ]

        if status == "PASS":
            readiness = "CLOSED"
        elif status == "FAIL":
            readiness = "FAILED_EVIDENCE"
        elif tooling_missing:
            readiness = "BLOCKED_TOOLING"
        elif dependency_open:
            readiness = "BLOCKED_DEPENDENCY"
        else:
            readiness = "READY_FOR_EXTERNAL_EXECUTION"

        rows.append(
            {
                "item_id": item_id,
                "current_status": status,
                "readiness": readiness,
                "next_action": spec[
                    "action"
                ],
                "measurement_pack_kind":
                    spec["pack_kind"],
                "tooling_required":
                    list(spec["tooling"]),
                "tooling_missing":
                    tooling_missing,
                "dependencies":
                    list(
                        spec[
                            "dependencies"
                        ]
                    ),
                "dependencies_open":
                    dependency_open,
                "requires_measured_evidence":
                    bool(
                        item.get(
                            "requires_measured_evidence",
                            False,
                        )
                    ),
            }
        )

    if errors:
        status = "INVALID"
    else:
        status = "READY"

    ready_actions = [
        row["item_id"]
        for row in rows
        if row["readiness"]
        == "READY_FOR_EXTERNAL_EXECUTION"
    ]

    blocked_actions = [
        row["item_id"]
        for row in rows
        if row["readiness"]
        in {
            "BLOCKED_TOOLING",
            "BLOCKED_DEPENDENCY",
        }
    ]

    closed = [
        row["item_id"]
        for row in rows
        if row["readiness"] == "CLOSED"
    ]

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "errors": errors,
        "ready_for_external_execution":
            ready_actions,
        "blocked_items":
            blocked_actions,
        "closed_items":
            closed,
        "items": rows,
        "notes": [
            "READY_FOR_EXTERNAL_EXECUTION means software/contracts are ready; it does not mean physical evidence exists.",
            "BLOCKED_DEPENDENCY is derived only from explicit project evidence dependencies.",
            "Measurement packs are templates and remain non-evidence until completed and promoted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build project measurement execution readiness report"
        )
    )

    parser.add_argument(
        "manifest"
    )
    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = build_readiness(
        load_json(args.manifest)
    )

    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
