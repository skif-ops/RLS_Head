from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-FOOTPRINT-READINESS-001"
ALLOWED_STATUS = {
    "LOCKED",
    "VERIFY_REQUIRED",
    "CUSTOM_REQUIRED",
}


def evaluate(path: str | Path) -> dict:
    path = Path(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "ref",
            "mpn",
            "package_code",
            "footprint_source",
            "footprint_id",
            "status",
            "verification_basis",
            "notes",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("footprint plan CSV missing required columns")
        rows = list(reader)

    errors: list[str] = []
    locked: list[str] = []
    unresolved: list[str] = []

    seen = set()

    for row in rows:
        ref = str(row.get("ref", "")).strip()
        status = str(row.get("status", "")).strip()
        footprint_id = str(row.get("footprint_id", "")).strip()
        basis = str(row.get("verification_basis", "")).strip()
        package_code = str(row.get("package_code", "")).strip()

        if not ref:
            errors.append("blank_ref")
            continue

        if ref in seen:
            errors.append(f"duplicate_ref:{ref}")
        seen.add(ref)

        if status not in ALLOWED_STATUS:
            errors.append(f"invalid_status:{ref}:{status}")
            continue

        if not package_code:
            errors.append(f"missing_package_code:{ref}")

        if not basis:
            errors.append(f"missing_verification_basis:{ref}")

        if status == "LOCKED":
            if not footprint_id:
                errors.append(f"locked_without_footprint:{ref}")
            elif str(row.get("footprint_source", "")).strip() == "PROJECT_LOCAL":
                local_path = path.parent / footprint_id
                if not local_path.is_file():
                    errors.append(f"missing_local_footprint:{ref}:{footprint_id}")
                else:
                    locked.append(ref)
            else:
                locked.append(ref)
        else:
            unresolved.append(ref)

    if errors:
        status = "INVALID"
    elif unresolved:
        status = "FOOTPRINT_PLAN_READY"
    else:
        status = "FOOTPRINT_FREEZE_READY"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "locked_refs": sorted(locked),
        "unresolved_refs": sorted(unresolved),
        "row_count": len(rows),
        "notes": [
            "FOOTPRINT_PLAN_READY means package decisions are explicit but PCB placement freeze is not authorized.",
            "FOOTPRINT_FREEZE_READY requires every listed footprint to be LOCKED.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(args.csv)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    return 0 if result["status"] != "INVALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
