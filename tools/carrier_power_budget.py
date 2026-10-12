from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-POWER-BUDGET-001"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "rail",
            "source",
            "capacity",
            "load",
            "allocation",
            "unit",
            "criticality",
            "notes",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("power budget CSV missing required columns")
        return list(reader)


def evaluate_power_budget(path: str | Path) -> dict:
    rows = _rows(Path(path))
    errors: list[str] = []
    warnings: list[str] = []

    rails: dict[str, dict] = {}

    for row in rows:
        rail = str(row["rail"]).strip()
        if not rail:
            errors.append("blank_rail")
            continue

        try:
            capacity = float(row["capacity"])
            allocation = float(row["allocation"])
        except ValueError:
            errors.append(f"parse:{rail}:{row.get('load','')}")
            continue

        if capacity <= 0.0 or allocation < 0.0:
            errors.append(f"nonpositive:{rail}:{row.get('load','')}")
            continue

        item = rails.setdefault(
            rail,
            {
                "capacity": capacity,
                "allocated_total": 0.0,
                "allocated_nonreserve": 0.0,
                "loads": [],
            },
        )

        if abs(item["capacity"] - capacity) > 1.0e-9:
            errors.append(f"capacity_mismatch:{rail}")

        load = str(row["load"]).strip()
        item["allocated_total"] += allocation
        if load.lower() != "reserve":
            item["allocated_nonreserve"] += allocation

        item["loads"].append(
            {
                "load": load,
                "allocation": allocation,
                "criticality": str(row["criticality"]).strip(),
            }
        )

    results = {}

    for rail, item in rails.items():
        capacity = item["capacity"]
        total = item["allocated_total"]
        nonreserve = item["allocated_nonreserve"]
        headroom_total = capacity - total
        headroom_nonreserve = capacity - nonreserve
        margin_total_pct = 100.0 * headroom_total / capacity
        margin_nonreserve_pct = 100.0 * headroom_nonreserve / capacity

        if total > capacity + 1.0e-9:
            errors.append(f"overallocated:{rail}")
            state = "FAIL"
        elif margin_total_pct < 10.0:
            warnings.append(f"low_total_headroom:{rail}")
            state = "WARNING"
        else:
            state = "PASS"

        results[rail] = {
            **item,
            "headroom_total": headroom_total,
            "headroom_nonreserve": headroom_nonreserve,
            "margin_total_pct": margin_total_pct,
            "margin_nonreserve_pct": margin_nonreserve_pct,
            "state": state,
        }

    if "3V3" not in results:
        errors.append("missing_rail:3V3")

    if "RADAR_12V" not in results:
        errors.append("missing_rail:RADAR_12V")

    if "12V_IN" not in results:
        errors.append("missing_rail:12V_IN")

    status = "FAIL" if errors else ("WARNING" if warnings else "PASS")

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "rails": results,
        "notes": [
            "Allocation is an engineering budget, not measured consumption.",
            "WARNING requires bench/thermal verification but does not imply overload.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate System Carrier Rev.A power allocation headroom"
    )
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate_power_budget(args.csv)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    return 0 if result["status"] in {"PASS", "WARNING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
