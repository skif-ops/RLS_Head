from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


SCHEMA = "INTEGRATED-RADAR-GATE-001"

REQUIRED_ITEMS = (
    "AWR_EVM_PROFILE_MEASURED",
    "PHYSICAL_ANT_MEASUREMENT",
    "SYS_ERR_MEASURED",
)


@dataclass(frozen=True)
class GateDecision:
    status: str
    authorization: str
    reason_codes: tuple[str, ...]


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_integrated_radar_gate(
    project_manifest: dict,
) -> dict:
    if project_manifest.get("schema") != "PROJECT-EVIDENCE-MANIFEST-001":
        raise ValueError("unexpected project evidence manifest schema")

    items = project_manifest.get("items")

    if not isinstance(items, list):
        raise ValueError("project evidence items must be a list")

    by_id = {
        str(item.get("id", "")): item
        for item in items
        if isinstance(item, dict)
    }

    missing = [
        item_id
        for item_id in REQUIRED_ITEMS
        if item_id not in by_id
    ]

    if missing:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": [
                f"missing_item:{item_id}"
                for item_id in missing
            ],
        }

    snapshot = {
        item_id: {
            "status": str(by_id[item_id].get("status", "OPEN")),
            "evidence_level": str(
                by_id[item_id].get("evidence_level", "OPEN")
            ),
            "synthetic": bool(
                by_id[item_id].get("synthetic", False)
            ),
        }
        for item_id in REQUIRED_ITEMS
    }

    reasons: list[str] = []

    for item_id, item in snapshot.items():
        if item["synthetic"]:
            reasons.append(f"synthetic:{item_id}")

    if reasons:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": sorted(reasons),
            "input_status": snapshot,
        }

    statuses = {
        item_id: snapshot[item_id]["status"]
        for item_id in REQUIRED_ITEMS
    }

    if any(status == "FAIL" for status in statuses.values()):
        failed = [
            item_id
            for item_id, status in statuses.items()
            if status == "FAIL"
        ]

        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": [
                f"failed:{item_id}"
                for item_id in failed
            ],
            "input_status": snapshot,
        }

    open_like = {
        "OPEN",
        "HOLD",
    }

    blocked = [
        item_id
        for item_id, status in statuses.items()
        if status in open_like
    ]

    if blocked:
        return {
            "schema": SCHEMA,
            "status": "HOLD",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": [
                f"not_ready:{item_id}"
                for item_id in blocked
            ],
            "input_status": snapshot,
        }

    unsupported = [
        item_id
        for item_id, status in statuses.items()
        if status not in {
            "PASS",
            "CONDITIONAL",
        }
    ]

    if unsupported:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": [
                f"unsupported_status:{item_id}:{statuses[item_id]}"
                for item_id in unsupported
            ],
            "input_status": snapshot,
        }

    conditional_items = [
        item_id
        for item_id, status in statuses.items()
        if status == "CONDITIONAL"
    ]

    if conditional_items:
        status = "CONDITIONAL"
        authorization = "CONDITIONAL_INTEGRATED_MEASUREMENT_PROTOTYPE"
        reasons = [
            f"conditional:{item_id}"
            for item_id in conditional_items
        ]
    else:
        status = "PASS"
        authorization = "AUTHORIZED_FOR_INTEGRATED_MEASUREMENT_PROTOTYPE"
        reasons = []

    return {
        "schema": SCHEMA,
        "status": status,
        "prototype_authorization": authorization,
        "reason_codes": reasons,
        "input_status": snapshot,
        "authorized_scope": [
            "integrated sensing prototype design",
            "integrated RF/antenna correlation measurements",
            "integrated timing/TargetState verification",
        ],
        "explicitly_not_authorized": [
            "production release",
            "production antenna freeze",
            "production waveform freeze",
            "vehicle-control or guidance functions",
        ],
        "notes": [
            "This gate uses authoritative project evidence items only.",
            "It authorizes an integrated measurement prototype, not production.",
            "All three required evidence items remain independently traceable.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate INTEGRATED-RADAR-GATE-001"
    )
    parser.add_argument("manifest")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = evaluate_integrated_radar_gate(
        load_json(args.manifest)
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {
        "PASS",
        "CONDITIONAL",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
