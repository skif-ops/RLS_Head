from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from tools.range_analysis import fit_range_exponent, median


DEFAULT_RANGES_M = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0)


@dataclass(frozen=True)
class ReferenceRangeConfig:
    expected_ranges_m: tuple[float, ...] = DEFAULT_RANGES_M
    min_samples_per_range: int = 20
    max_fit_rms_db: float = 2.0


@dataclass(frozen=True)
class ReferenceRangePoint:
    range_m: float
    sample_count: int
    signal_db_median: float
    signal_db_mean: float
    detector_margin_db_median: float | None
    detected_fraction: float
    track_valid_fraction: float


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
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
            raise ValueError(
                f"CSV header must include {sorted(required)}"
            )

        rows = list(reader)

    if not rows:
        raise ValueError("reference-range CSV is empty")

    return rows


def _parse_bool01(text: str, field: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be 0 or 1") from exc

    if value not in (0, 1):
        raise ValueError(f"{field} must be 0 or 1")

    return value


def summarize_point(
    rows: list[dict[str, str]],
    range_m: float,
) -> ReferenceRangePoint:
    selected: list[dict[str, str]] = []

    for row in rows:
        try:
            row_range = float(row["range_m"])
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid range_m") from exc

        if not math.isfinite(row_range) or row_range <= 0.0:
            raise ValueError("range_m must be finite and positive")

        if math.isclose(row_range, range_m, rel_tol=0.0, abs_tol=1.0e-6):
            selected.append(row)

    if not selected:
        raise ValueError(f"no samples for range {range_m}")

    signal_values: list[float] = []
    margin_values: list[float] = []
    detected = 0
    track_valid = 0

    for row in selected:
        try:
            signal_db = float(row["signal_db"])
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid signal_db") from exc

        if not math.isfinite(signal_db):
            raise ValueError("signal_db must be finite")

        signal_values.append(signal_db)

        margin_text = (row.get("detector_margin_db") or "").strip()
        if margin_text:
            margin = float(margin_text)
            if not math.isfinite(margin):
                raise ValueError("detector_margin_db must be finite")
            margin_values.append(margin)

        detected += _parse_bool01(row["detected"], "detected")
        track_valid += _parse_bool01(row["track_valid"], "track_valid")

    count = len(selected)

    return ReferenceRangePoint(
        range_m=range_m,
        sample_count=count,
        signal_db_median=median(signal_values),
        signal_db_mean=mean(signal_values),
        detector_margin_db_median=median(margin_values) if margin_values else None,
        detected_fraction=detected / count,
        track_valid_fraction=track_valid / count,
    )


def build_reference_range_result(
    rows: list[dict[str, str]],
    config: ReferenceRangeConfig = ReferenceRangeConfig(),
) -> dict:
    if config.min_samples_per_range <= 0:
        raise ValueError("min_samples_per_range must be > 0")

    if config.max_fit_rms_db <= 0.0 or not math.isfinite(config.max_fit_rms_db):
        raise ValueError("max_fit_rms_db must be finite and positive")

    summaries: list[ReferenceRangePoint] = []
    missing_ranges: list[float] = []
    underfilled_ranges: list[float] = []

    for range_m in config.expected_ranges_m:
        try:
            point = summarize_point(rows, range_m)
        except ValueError as exc:
            if str(exc).startswith("no samples for range"):
                missing_ranges.append(range_m)
                continue
            raise

        summaries.append(point)

        if point.sample_count < config.min_samples_per_range:
            underfilled_ranges.append(range_m)

    if len(summaries) < 2:
        fit = None
    else:
        fit = fit_range_exponent(
            [
                (point.range_m, point.signal_db_median)
                for point in summaries
            ]
        )

    status = "DATA_READY"
    reason_codes: list[str] = []

    if missing_ranges:
        status = "INCOMPLETE"
        reason_codes.append("missing_ranges")

    if underfilled_ranges:
        status = "INCOMPLETE"
        reason_codes.append("insufficient_samples")

    if fit is None:
        status = "INCOMPLETE"
        reason_codes.append("insufficient_fit_points")
    elif fit["rms_residual_db"] > config.max_fit_rms_db:
        status = "FIT_POOR"
        reason_codes.append("fit_residual")

    r4_residuals: list[float] = []

    if summaries:
        anchor = summaries[0]
        anchor_log = math.log10(anchor.range_m)
        for point in summaries:
            predicted = (
                anchor.signal_db_median
                - 40.0 * (math.log10(point.range_m) - anchor_log)
            )
            r4_residuals.append(point.signal_db_median - predicted)

    r4_rms_db = (
        math.sqrt(sum(v * v for v in r4_residuals) / len(r4_residuals))
        if r4_residuals
        else None
    )

    run_ids = sorted(
        {
            (row.get("run_id") or "").strip()
            for row in rows
            if (row.get("run_id") or "").strip()
        }
    )

    return {
        "schema": "REFERENCE-RANGE-RESULT-001",
        "status": status,
        "reason_codes": reason_codes,
        "config": {
            "expected_ranges_m": list(config.expected_ranges_m),
            "min_samples_per_range": config.min_samples_per_range,
            "max_fit_rms_db": config.max_fit_rms_db,
        },
        "run_ids": run_ids,
        "missing_ranges_m": missing_ranges,
        "underfilled_ranges_m": underfilled_ranges,
        "points": [asdict(point) for point in summaries],
        "fit": fit,
        "r4_rms_residual_db": r4_rms_db,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build reference-range ladder result and empirical n-hat"
    )
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--max-fit-rms-db", type=float, default=2.0)

    args = parser.parse_args()

    rows = load_csv(args.csv)
    config = ReferenceRangeConfig(
        min_samples_per_range=args.min_samples,
        max_fit_rms_db=args.max_fit_rms_db,
    )
    result = build_reference_range_result(rows, config)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "DATA_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
