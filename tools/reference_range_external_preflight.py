from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "REFERENCE-RANGE-EXTERNAL-PREFLIGHT-001"
REQUIRED_RANGES = (50, 100, 150, 200, 250, 300)


def evaluate_preflight(
    *,
    reference_csv: str | Path,
    manifest_dir: str | Path,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    csv_path = Path(reference_csv)
    if not csv_path.is_file():
        errors.append("reference_csv_missing")
    else:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "run_id",
                "range_m",
                "signal_db",
                "detector_margin_db",
                "detected",
                "track_valid",
            }
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                errors.append("reference_csv_header")
            rows = list(reader) if reader.fieldnames else []

        if rows:
            ranges = set()
            for index, row in enumerate(rows, start=2):
                try:
                    ranges.add(int(float(row["range_m"])))
                    int(row["detected"])
                    int(row["track_valid"])
                    float(row["signal_db"])
                    margin = (row.get("detector_margin_db") or "").strip()
                    if margin:
                        float(margin)
                except (KeyError, TypeError, ValueError):
                    errors.append(f"invalid_row:{index}")
            missing = [r for r in REQUIRED_RANGES if r not in ranges]
            if missing:
                warnings.append(
                    "missing_ranges_in_csv:" + ",".join(map(str, missing))
                )
        else:
            warnings.append("reference_csv_has_no_samples")

    manifests = Path(manifest_dir)
    found_ranges: set[int] = set()

    if not manifests.is_dir():
        errors.append("manifest_dir_missing")
    else:
        for path in sorted(manifests.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append(f"invalid_manifest_json:{path.name}")
                continue

            if data.get("schema") != "EVM-RUN-MANIFEST-001":
                errors.append(f"manifest_schema:{path.name}")
                continue

            if data.get("mode") != "QUALIFY":
                errors.append(f"manifest_mode:{path.name}")

            if data.get("synthetic_fixture") is not False:
                errors.append(f"manifest_synthetic:{path.name}")

            if data.get("truth_status") != "VALID":
                errors.append(f"manifest_truth:{path.name}")

            if data.get("time_alignment_valid") is not True:
                errors.append(f"manifest_time_alignment:{path.name}")

            if data.get("config_locked") is not True:
                errors.append(f"manifest_config_lock:{path.name}")

            if data.get("evidence_level") != "MEASURED_EVM":
                errors.append(f"manifest_evidence_level:{path.name}")

            try:
                range_m = int(float(data.get("range_nominal_m")))
            except (TypeError, ValueError):
                errors.append(f"manifest_range:{path.name}")
                continue

            if range_m in REQUIRED_RANGES:
                found_ranges.add(range_m)

    missing_manifests = [
        r for r in REQUIRED_RANGES if r not in found_ranges
    ]
    if missing_manifests:
        warnings.append(
            "missing_range_manifests:"
            + ",".join(map(str, missing_manifests))
        )

    status = "READY_FOR_COLLECTION" if not errors else "BLOCKED"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "required_ranges_m": list(REQUIRED_RANGES),
        "manifest_ranges_present_m": sorted(found_ranges),
        "notes": [
            "READY_FOR_COLLECTION means the reference-range campaign is structurally ready.",
            "It does not mean the 50-300 m ladder is complete or DATA_READY.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a reference-range external measurement campaign"
    )
    parser.add_argument("--reference-csv", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate_preflight(
        reference_csv=args.reference_csv,
        manifest_dir=args.manifest_dir,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY_FOR_COLLECTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
