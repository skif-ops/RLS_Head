from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

SCHEMA = "SYSTEM-CARRIER-PCB-LAYOUT-CONTRACT-001"

REQUIRED = {
    "PCB-001","PCB-002","PCB-003","PCB-006","PCB-007","PCB-009",
    "PCB-011","PCB-013","PCB-014","PCB-016","PCB-020","PCB-024",
}


def validate(path: str | Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {
            "rule_id","domain","object","rule","criticality","verification",
        }
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError("layout contract CSV missing required columns")
        rows = list(reader)

    errors: list[str] = []
    ids = set()

    for row in rows:
        rule_id = str(row.get("rule_id","")).strip()
        if not rule_id:
            errors.append("blank_rule_id")
            continue
        if rule_id in ids:
            errors.append(f"duplicate_rule_id:{rule_id}")
        ids.add(rule_id)

        if str(row.get("criticality","")).strip() not in {"P0","P1","P2"}:
            errors.append(f"invalid_criticality:{rule_id}")

        for key in ("domain","object","rule","verification"):
            if not str(row.get(key,"")).strip():
                errors.append(f"blank_{key}:{rule_id}")

    for rule_id in sorted(REQUIRED - ids):
        errors.append(f"missing_required_rule:{rule_id}")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "rule_count": len(rows),
        "p0_count": sum(
            1 for row in rows
            if str(row.get("criticality","")).strip() == "P0"
        ),
        "notes": [
            "PASS validates the pre-routing contract only; it does not imply PCB placement or routing is complete.",
            "The System Carrier remains non-mmWave; 76-81 GHz RF routing is explicitly excluded.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.csv)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
