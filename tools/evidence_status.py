from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_STATUSES = {
    "OPEN",
    "PASS",
    "FAIL",
    "HOLD",
    "CONDITIONAL",
}

MEASURED_LEVELS = {
    "MEASURED_EVM",
    "MEASURED_HIL",
    "MEASURED_BENCH",
    "MEASURED_EM",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_manifest(manifest: dict) -> dict:
    if manifest.get("schema") != "PROJECT-EVIDENCE-MANIFEST-001":
        raise ValueError("unexpected evidence manifest schema")

    items = manifest.get("items")

    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    by_id = {}
    errors: list[str] = []

    for item in items:
        item_id = str(item.get("id", "")).strip()

        if not item_id:
            errors.append("item_without_id")
            continue

        if item_id in by_id:
            errors.append(f"duplicate_id:{item_id}")
            continue

        by_id[item_id] = item

        status = str(item.get("status", ""))
        evidence_level = str(item.get("evidence_level", "UNSPECIFIED"))
        synthetic = bool(item.get("synthetic", False))

        if status not in ALLOWED_STATUSES:
            errors.append(f"invalid_status:{item_id}")

        if synthetic and evidence_level in MEASURED_LEVELS:
            errors.append(f"synthetic_marked_measured:{item_id}")

        if status == "PASS" and evidence_level in {"UNSPECIFIED", "NONE", "OPEN"}:
            errors.append(f"pass_without_evidence:{item_id}")

    milestone_results = {}

    milestones = manifest.get("milestones", {})

    if not isinstance(milestones, dict):
        raise ValueError("milestones must be an object")

    for milestone_id, required_ids in milestones.items():
        if not isinstance(required_ids, list) or not required_ids:
            errors.append(f"invalid_milestone:{milestone_id}")
            continue

        missing = [
            item_id
            for item_id in required_ids
            if item_id not in by_id
        ]

        if missing:
            errors.append(
                f"milestone_missing_items:{milestone_id}:"
                + ",".join(missing)
            )
            continue

        required = [by_id[item_id] for item_id in required_ids]

        if any(str(item.get("status")) == "FAIL" for item in required):
            status = "FAIL"
        elif all(str(item.get("status")) == "PASS" for item in required):
            status = "PASS"
        elif any(str(item.get("status")) == "CONDITIONAL" for item in required):
            status = "CONDITIONAL"
        else:
            status = "OPEN"

        milestone_results[milestone_id] = {
            "status": status,
            "required_items": required_ids,
            "open_items": [
                item["id"]
                for item in required
                if str(item.get("status")) != "PASS"
            ],
        }

    overall = "VALID" if not errors else "INVALID"

    return {
        "schema": "PROJECT-EVIDENCE-STATUS-001",
        "status": overall,
        "errors": errors,
        "item_count": len(by_id),
        "milestones": milestone_results,
        "measured_open_items": [
            item_id
            for item_id, item in by_id.items()
            if bool(item.get("requires_measured_evidence", False))
            and str(item.get("status")) != "PASS"
        ],
        "passed_items": [
            item_id
            for item_id, item in by_id.items()
            if str(item.get("status")) == "PASS"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate project evidence manifest and milestone readiness"
    )
    parser.add_argument("manifest")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = validate_manifest(load_json(args.manifest))

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
