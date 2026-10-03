from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "mc_sample_id",
    "frequency_hz",
    "az_deg",
    "el_deg",
    "combined_gain_delta_db",
    "sigma_az_deg",
    "sigma_el_deg",
    "ambiguity_flag",
    "track_usable",
    "mandatory_region",
}


@dataclass(frozen=True)
class McGateConfig:
    min_samples_per_cell: int = 20
    min_track_usable_probability: float = 0.95
    max_ambiguity_probability: float = 0.05


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    if q < 0.0 or q > 1.0:
        raise ValueError("q must be in [0,1]")

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = q * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))

    if lo == hi:
        return ordered[lo]

    alpha = position - lo
    return ordered[lo] * (1.0 - alpha) + ordered[hi] * alpha


def _bool01(text: str, field: str) -> bool:
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be 0 or 1") from exc

    if value not in (0, 1):
        raise ValueError(f"{field} must be 0 or 1")

    return bool(value)


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(
                f"MC CSV header must include {sorted(REQUIRED_COLUMNS)}"
            )

        rows = list(reader)

    if not rows:
        raise ValueError("MC CSV is empty")

    return rows


def _parse_row(row: dict[str, str], index: int) -> dict:
    sample_id = (row["mc_sample_id"] or "").strip()

    if not sample_id:
        raise ValueError(f"row {index}: empty mc_sample_id")

    parsed = {"mc_sample_id": sample_id}

    for field in (
        "frequency_hz",
        "az_deg",
        "el_deg",
        "combined_gain_delta_db",
        "sigma_az_deg",
        "sigma_el_deg",
    ):
        try:
            value = float(row[field])
        except ValueError as exc:
            raise ValueError(f"row {index}: invalid {field}") from exc

        if not math.isfinite(value):
            raise ValueError(f"row {index}: non-finite {field}")

        parsed[field] = value

    if parsed["frequency_hz"] <= 0.0:
        raise ValueError(f"row {index}: frequency_hz must be positive")

    if parsed["sigma_az_deg"] < 0.0 or parsed["sigma_el_deg"] < 0.0:
        raise ValueError(f"row {index}: angle sigma must be non-negative")

    parsed["ambiguity_flag"] = _bool01(
        row["ambiguity_flag"], "ambiguity_flag"
    )
    parsed["track_usable"] = _bool01(
        row["track_usable"], "track_usable"
    )
    parsed["mandatory_region"] = _bool01(
        row["mandatory_region"], "mandatory_region"
    )

    if parsed["ambiguity_flag"] and parsed["track_usable"]:
        raise ValueError(
            f"row {index}: ambiguous point cannot be track_usable"
        )

    return parsed


def summarize_mc(
    rows: list[dict[str, str]],
    config: McGateConfig = McGateConfig(),
) -> dict:
    if config.min_samples_per_cell <= 0:
        raise ValueError("min_samples_per_cell must be > 0")

    if not (0.0 <= config.min_track_usable_probability <= 1.0):
        raise ValueError("min_track_usable_probability must be in [0,1]")

    if not (0.0 <= config.max_ambiguity_probability <= 1.0):
        raise ValueError("max_ambiguity_probability must be in [0,1]")

    parsed = [
        _parse_row(row, index)
        for index, row in enumerate(rows, start=2)
    ]

    groups: dict[tuple[float, float, float], list[dict]] = defaultdict(list)

    for row in parsed:
        key = (
            row["frequency_hz"],
            row["az_deg"],
            row["el_deg"],
        )
        groups[key].append(row)

    cells = []
    underfilled = []
    mandatory_failures = []

    for (frequency_hz, az_deg, el_deg), group in sorted(groups.items()):
        gains = [row["combined_gain_delta_db"] for row in group]
        sig_az = [row["sigma_az_deg"] for row in group]
        sig_el = [row["sigma_el_deg"] for row in group]

        track_probability = (
            sum(1 for row in group if row["track_usable"])
            / len(group)
        )

        ambiguity_probability = (
            sum(1 for row in group if row["ambiguity_flag"])
            / len(group)
        )

        mandatory = any(row["mandatory_region"] for row in group)

        robust = (
            len(group) >= config.min_samples_per_cell
            and track_probability >= config.min_track_usable_probability
            and ambiguity_probability <= config.max_ambiguity_probability
        )

        cell = {
            "frequency_hz": frequency_hz,
            "az_deg": az_deg,
            "el_deg": el_deg,
            "sample_count": len(group),
            "mandatory_region": mandatory,
            "gain_p05_db": percentile(gains, 0.05),
            "gain_p50_db": percentile(gains, 0.50),
            "gain_p95_db": percentile(gains, 0.95),
            "sigma_az_p95_deg": percentile(sig_az, 0.95),
            "sigma_el_p95_deg": percentile(sig_el, 0.95),
            "track_usable_probability": track_probability,
            "ambiguity_probability": ambiguity_probability,
            "robust": robust,
        }

        cells.append(cell)

        if len(group) < config.min_samples_per_cell:
            underfilled.append(
                {
                    "frequency_hz": frequency_hz,
                    "az_deg": az_deg,
                    "el_deg": el_deg,
                    "sample_count": len(group),
                }
            )

        if (
            mandatory
            and len(group) >= config.min_samples_per_cell
            and not robust
        ):
            mandatory_failures.append(
                {
                    "frequency_hz": frequency_hz,
                    "az_deg": az_deg,
                    "el_deg": el_deg,
                }
            )

    status = "PASS"

    reason_codes = []

    if underfilled:
        status = "INCOMPLETE"
        reason_codes.append("underfilled_cells")

    if mandatory_failures:
        status = "FAIL"
        reason_codes.append("mandatory_region_not_robust")

    return {
        "schema": "ANT-D1-MC-SUMMARY-001",
        "status": status,
        "reason_codes": reason_codes,
        "config": {
            "min_samples_per_cell": config.min_samples_per_cell,
            "min_track_usable_probability": config.min_track_usable_probability,
            "max_ambiguity_probability": config.max_ambiguity_probability,
        },
        "sample_rows": len(parsed),
        "cell_count": len(cells),
        "underfilled_cells": underfilled,
        "mandatory_failures": mandatory_failures,
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize D1 manufacturing/RF Monte-Carlo evidence"
    )
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--min-track-probability", type=float, default=0.95)
    parser.add_argument("--max-ambiguity-probability", type=float, default=0.05)

    args = parser.parse_args()

    result = summarize_mc(
        load_csv(args.csv),
        McGateConfig(
            min_samples_per_cell=args.min_samples,
            min_track_usable_probability=args.min_track_probability,
            max_ambiguity_probability=args.max_ambiguity_probability,
        ),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
