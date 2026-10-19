from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-MAGJACK-SELECTION-001"
SELECTED_MPN = "SI-60182-F"
SYMBOL_ID = "Connector:RJ45_Bel_SI-60062-F"
FOOTPRINT_ID = "Connector_RJ:RJ45_Bel_SI-60062-F"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        return list(reader)


def validate(directory: str | Path) -> dict:
    root = Path(directory)
    errors: list[str] = []

    bom = {
        str(row.get("ref", "")).strip(): row
        for row in _rows(root / "BOM_SYS_CARRIER_003.csv")
    }
    package = {
        str(row.get("ref", "")).strip(): row
        for row in _rows(root / "PACKAGE_CONTRACT_SYS_001.csv")
    }
    footprint = {
        str(row.get("ref", "")).strip(): row
        for row in _rows(root / "FOOTPRINT_PLAN_SYS_001.csv")
    }
    blockers = {
        str(row.get("blocker_id", "")).strip(): row
        for row in _rows(root / "EXTERNAL_DOCUMENT_BLOCKERS_SYS_001.csv")
    }

    eth = bom.get("J6")
    if eth is None:
        errors.append("missing_bom:J6")
    else:
        if str(eth.get("mpn", "")).strip() != SELECTED_MPN:
            errors.append("bom_mpn")
        if str(eth.get("status", "")).strip() != "SELECTED":
            errors.append("bom_status")

    pkg = package.get("J6")
    if pkg is None:
        errors.append("missing_package:J6")
    else:
        if str(pkg.get("mpn", "")).strip() != SELECTED_MPN:
            errors.append("package_mpn")
        if str(pkg.get("status", "")).strip() != "LOCKED":
            errors.append("package_status")
        if str(pkg.get("footprint_candidate", "")).strip() != FOOTPRINT_ID:
            errors.append("package_footprint")

    fp = footprint.get("J6")
    if fp is None:
        errors.append("missing_footprint:J6")
    else:
        if str(fp.get("mpn", "")).strip() != SELECTED_MPN:
            errors.append("footprint_mpn")
        if str(fp.get("status", "")).strip() != "LOCKED":
            errors.append("footprint_status")
        if str(fp.get("footprint_id", "")).strip() != FOOTPRINT_ID:
            errors.append("footprint_id")

    blocker = blockers.get("MAGJACK_DRAWING")
    if blocker is None:
        errors.append("missing_blocker_record")
    else:
        if str(blocker.get("mpn", "")).strip() != SELECTED_MPN:
            errors.append("blocker_mpn")
        if str(blocker.get("status", "")).strip() != "CLOSED":
            errors.append("blocker_not_closed")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "selected_mpn": SELECTED_MPN,
        "stock_symbol_id": SYMBOL_ID,
        "stock_footprint_id": FOOTPRINT_ID,
        "notes": [
            (
                "SI-60182-F is the selected -40..+85C part. "
                "The SI-60062-F KiCad representation is reused only after "
                "drawing-level electrical/mechanical compatibility review."
            ),
            (
                "The SI-60062-F component itself is not selected for Rev.A."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.directory)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
