from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class RangeCriteria:
    pd_min: float = 0.90
    track_availability_min: float = 0.95
    false_track_max_per_10min: float = 1.0


@dataclass(frozen=True)
class RangePointSummary:
    range_m: float
    sample_count: int
    detection_count: int
    track_valid_count: int
    fresh_count: int
    pd: float
    pd_ci_low: float
    pd_ci_high: float
    track_availability: float
    fresh_fraction: float
    detector_margin_db_median: float | None
    detector_margin_db_mean: float | None


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be > 0")
    if successes < 0 or successes > total:
        raise ValueError("successes must be within [0,total]")

    p = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires values")
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def summarize_range_point(rows: list[dict[str, str]], range_m: float) -> RangePointSummary:
    selected = [
        row for row in rows
        if math.isclose(float(row["range_m"]), range_m, rel_tol=0.0, abs_tol=1e-6)
    ]
    if not selected:
        raise ValueError(f"no rows for range {range_m}")

    detections = 0
    tracks = 0
    fresh = 0
    margins: list[float] = []

    for idx, row in enumerate(selected, start=1):
        try:
            detected = int(row["detected"])
            track_valid = int(row["track_valid"])
            fresh_flag = int(row["fresh"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid boolean field at selected row {idx}") from exc

        for value in (detected, track_valid, fresh_flag):
            if value not in (0, 1):
                raise ValueError("detected/track_valid/fresh must be 0 or 1")

        detections += detected
        tracks += track_valid
        fresh += fresh_flag

        margin_text = (row.get("detector_margin_db") or "").strip()
        if margin_text:
            value = float(margin_text)
            if not math.isfinite(value):
                raise ValueError("non-finite detector margin")
            margins.append(value)

    total = len(selected)
    ci_low, ci_high = wilson_interval(detections, total)

    return RangePointSummary(
        range_m=range_m,
        sample_count=total,
        detection_count=detections,
        track_valid_count=tracks,
        fresh_count=fresh,
        pd=detections / total,
        pd_ci_low=ci_low,
        pd_ci_high=ci_high,
        track_availability=tracks / total,
        fresh_fraction=fresh / total,
        detector_margin_db_median=median(margins) if margins else None,
        detector_margin_db_mean=mean(margins) if margins else None,
    )


def fit_range_exponent(points: list[tuple[float, float]]) -> dict:
    if len(points) < 2:
        raise ValueError("at least two points required")

    x: list[float] = []
    y: list[float] = []

    for range_m, signal_db in points:
        if range_m <= 0 or not math.isfinite(range_m) or not math.isfinite(signal_db):
            raise ValueError("invalid fit point")
        x.append(math.log10(range_m))
        y.append(signal_db)

    x_mean = mean(x)
    y_mean = mean(y)

    sxx = sum((xi - x_mean) ** 2 for xi in x)
    if sxx <= 0.0:
        raise ValueError("range points must not all be equal")

    sxy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    n_hat = -slope / 10.0

    residuals = [
        yi - (intercept + slope * xi)
        for xi, yi in zip(x, y)
    ]

    rms_residual_db = math.sqrt(
        sum(r * r for r in residuals) / len(residuals)
    )

    return {
        "n_hat": n_hat,
        "slope_db_per_decade": slope,
        "intercept_db": intercept,
        "rms_residual_db": rms_residual_db,
        "sample_count": len(points),
    }


def required_margin_db(reference_range_m: float, target_range_m: float, exponent_n: float = 4.0) -> float:
    if reference_range_m <= 0 or target_range_m <= 0:
        raise ValueError("ranges must be positive")
    if exponent_n <= 0 or not math.isfinite(exponent_n):
        raise ValueError("exponent must be positive")
    return 10.0 * exponent_n * math.log10(target_range_m / reference_range_m)


def predicted_range_m(reference_range_m: float, margin_db: float, exponent_n: float = 4.0) -> float:
    if reference_range_m <= 0:
        raise ValueError("reference range must be positive")
    if exponent_n <= 0 or not math.isfinite(exponent_n):
        raise ValueError("exponent must be positive")
    return reference_range_m * 10.0 ** (margin_db / (10.0 * exponent_n))


def classify_track(summary: RangePointSummary, criteria: RangeCriteria) -> str:
    if (
        summary.pd >= criteria.pd_min
        and summary.track_availability >= criteria.track_availability_min
    ):
        return "TRACK_PASS"

    if summary.pd >= criteria.pd_min:
        return "DETECT_ONLY"

    return "TRACK_FAIL"


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "range_m",
            "detected",
            "track_valid",
            "fresh",
            "detector_margin_db",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV header must include {sorted(required)}")
        return list(reader)


def build_m300_result(rows: list[dict[str, str]], criteria: RangeCriteria) -> dict:
    summary = summarize_range_point(rows, 300.0)
    status = classify_track(summary, criteria)

    return {
        "schema": "M300-REPORT-001",
        "range_m": 300.0,
        "summary": asdict(summary),
        "criteria": asdict(criteria),
        "track_status": status,
        "m300_track_db": summary.detector_margin_db_median,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build M300 range evidence report")
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_csv(args.csv)
    result = build_m300_result(rows, RangeCriteria())

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["track_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
