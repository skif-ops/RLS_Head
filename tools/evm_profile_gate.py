from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from tools.evm_run_manifest import (
    load_json,
    validate_run_manifest,
)


RESULT_SCHEMA = "EVM-PROFILE-RESULT-001"

PROFILE_CLASSES = {
    "TRACK",
    "LR1",
    "LR2",
    "LRX",
}

ANGLE_STATUSES = {
    "PASS",
    "RESTRICTED",
    "FAIL",
}


@dataclass(frozen=True)
class GateConfig:
    pd_min: float = 0.90
    track_availability_min: float = 0.95
    update_min_hz: float = 20.0
    latency_operational_max_ms: float = 50.0
    latency_conditional_max_ms: float = 75.0
    compute_operational_max_pct: float = 80.0
    compute_conditional_max_pct: float = 90.0
    ram_operational_max_pct: float = 80.0
    ram_conditional_max_pct: float = 90.0
    gain_min_db: float = 0.0


@dataclass(frozen=True)
class MetricRow:
    run_id: str
    profile_id: str
    profile_class: str
    range_m: float
    rcs_m2: float
    dynamics_class: str
    fov_class: str
    pd: float
    track_availability: float
    fresh_fraction: float
    margin_db: float
    sigma_az_deg: float
    sigma_el_deg: float
    update_hz: float
    radar_latency_p99_ms: float
    compute_util_p99_pct: float
    ram_peak_pct: float
    overrun_count: int
    deadline_miss_count: int
    edma_error_count: int
    angle_status: str


def _finite_float(
    raw: str,
    field: str,
) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid float:{field}"
        ) from exc

    if not math.isfinite(value):
        raise ValueError(
            f"non-finite:{field}"
        )

    return value


def _nonnegative_int(
    raw: str,
    field: str,
) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid integer:{field}"
        ) from exc

    if value < 0:
        raise ValueError(
            f"negative integer:{field}"
        )

    return value


def load_metrics_csv(
    path: str | Path,
) -> list[MetricRow]:
    required = {
        "run_id",
        "profile_id",
        "profile_class",
        "range_m",
        "rcs_m2",
        "dynamics_class",
        "fov_class",
        "pd",
        "track_availability",
        "fresh_fraction",
        "margin_db",
        "sigma_az_deg",
        "sigma_el_deg",
        "update_hz",
        "radar_latency_p99_ms",
        "compute_util_p99_pct",
        "ram_peak_pct",
        "overrun_count",
        "deadline_miss_count",
        "edma_error_count",
        "angle_status",
    }

    rows: list[MetricRow] = []

    with Path(path).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if (
            reader.fieldnames is None
            or not required.issubset(
                reader.fieldnames
            )
        ):
            raise ValueError(
                "profile metrics CSV missing required columns"
            )

        seen_run_ids: set[str] = set()

        for line_number, raw in enumerate(
            reader,
            start=2,
        ):
            run_id = str(
                raw.get("run_id", "")
            ).strip()

            profile_id = str(
                raw.get("profile_id", "")
            ).strip()

            profile_class = str(
                raw.get("profile_class", "")
            ).strip()

            dynamics_class = str(
                raw.get("dynamics_class", "")
            ).strip()

            fov_class = str(
                raw.get("fov_class", "")
            ).strip()

            angle_status = str(
                raw.get("angle_status", "")
            ).strip()

            if not run_id:
                raise ValueError(
                    f"line {line_number}: blank run_id"
                )

            if run_id in seen_run_ids:
                raise ValueError(
                    f"line {line_number}: duplicate run_id"
                )

            seen_run_ids.add(run_id)

            if not profile_id:
                raise ValueError(
                    f"line {line_number}: blank profile_id"
                )

            if profile_class not in PROFILE_CLASSES:
                raise ValueError(
                    f"line {line_number}: invalid profile_class"
                )

            if not dynamics_class or not fov_class:
                raise ValueError(
                    f"line {line_number}: blank condition class"
                )

            if angle_status not in ANGLE_STATUSES:
                raise ValueError(
                    f"line {line_number}: invalid angle_status"
                )

            row = MetricRow(
                run_id=run_id,
                profile_id=profile_id,
                profile_class=profile_class,
                range_m=_finite_float(
                    raw["range_m"],
                    "range_m",
                ),
                rcs_m2=_finite_float(
                    raw["rcs_m2"],
                    "rcs_m2",
                ),
                dynamics_class=dynamics_class,
                fov_class=fov_class,
                pd=_finite_float(
                    raw["pd"],
                    "pd",
                ),
                track_availability=_finite_float(
                    raw["track_availability"],
                    "track_availability",
                ),
                fresh_fraction=_finite_float(
                    raw["fresh_fraction"],
                    "fresh_fraction",
                ),
                margin_db=_finite_float(
                    raw["margin_db"],
                    "margin_db",
                ),
                sigma_az_deg=_finite_float(
                    raw["sigma_az_deg"],
                    "sigma_az_deg",
                ),
                sigma_el_deg=_finite_float(
                    raw["sigma_el_deg"],
                    "sigma_el_deg",
                ),
                update_hz=_finite_float(
                    raw["update_hz"],
                    "update_hz",
                ),
                radar_latency_p99_ms=_finite_float(
                    raw["radar_latency_p99_ms"],
                    "radar_latency_p99_ms",
                ),
                compute_util_p99_pct=_finite_float(
                    raw["compute_util_p99_pct"],
                    "compute_util_p99_pct",
                ),
                ram_peak_pct=_finite_float(
                    raw["ram_peak_pct"],
                    "ram_peak_pct",
                ),
                overrun_count=_nonnegative_int(
                    raw["overrun_count"],
                    "overrun_count",
                ),
                deadline_miss_count=_nonnegative_int(
                    raw["deadline_miss_count"],
                    "deadline_miss_count",
                ),
                edma_error_count=_nonnegative_int(
                    raw["edma_error_count"],
                    "edma_error_count",
                ),
                angle_status=angle_status,
            )

            if row.range_m <= 0.0:
                raise ValueError(
                    f"line {line_number}: range must be positive"
                )

            if row.rcs_m2 <= 0.0:
                raise ValueError(
                    f"line {line_number}: RCS must be positive"
                )

            for name, value in {
                "pd": row.pd,
                "track_availability":
                    row.track_availability,
                "fresh_fraction":
                    row.fresh_fraction,
            }.items():
                if value < 0.0 or value > 1.0:
                    raise ValueError(
                        f"line {line_number}: {name} outside [0,1]"
                    )

            for name, value in {
                "update_hz": row.update_hz,
                "radar_latency_p99_ms":
                    row.radar_latency_p99_ms,
                "compute_util_p99_pct":
                    row.compute_util_p99_pct,
                "ram_peak_pct":
                    row.ram_peak_pct,
                "sigma_az_deg":
                    row.sigma_az_deg,
                "sigma_el_deg":
                    row.sigma_el_deg,
            }.items():
                if value < 0.0:
                    raise ValueError(
                        f"line {line_number}: negative {name}"
                    )

            if (
                row.compute_util_p99_pct > 100.0
                or row.ram_peak_pct > 100.0
            ):
                raise ValueError(
                    f"line {line_number}: utilization exceeds 100%"
                )

            rows.append(row)

    if not rows:
        raise ValueError(
            "profile metrics CSV contains no rows"
        )

    return rows


def _condition_key(
    row: MetricRow,
) -> tuple[float, float, str, str]:
    return (
        row.range_m,
        row.rcs_m2,
        row.dynamics_class,
        row.fov_class,
    )


def _campaign_readiness(
    validations: list[dict],
) -> tuple[str, list[str]]:
    statuses = {
        result["status"]
        for result in validations
    }

    if "INVALID" in statuses:
        return "INVALID", ["invalid_run_manifest"]

    if "HOLD" in statuses:
        return "HOLD", ["run_manifest_hold"]

    if statuses == {"TEST_READY"}:
        return "TEST_READY", []

    if statuses == {"MEASURED_READY"}:
        return "MEASURED_READY", []

    return "HOLD", ["mixed_evidence_readiness"]


def _profile_summary(
    profile_class: str,
    rows: list[MetricRow],
    track_margin_by_condition:
        dict[tuple[float, float, str, str], float],
    config: GateConfig,
) -> dict:
    min_pd = min(row.pd for row in rows)
    min_track_availability = min(
        row.track_availability
        for row in rows
    )
    min_fresh_fraction = min(
        row.fresh_fraction
        for row in rows
    )
    min_update_hz = min(
        row.update_hz
        for row in rows
    )
    max_latency = max(
        row.radar_latency_p99_ms
        for row in rows
    )
    max_compute = max(
        row.compute_util_p99_pct
        for row in rows
    )
    max_ram = max(
        row.ram_peak_pct
        for row in rows
    )
    max_sigma_az = max(
        row.sigma_az_deg
        for row in rows
    )
    max_sigma_el = max(
        row.sigma_el_deg
        for row in rows
    )

    overruns = sum(
        row.overrun_count
        for row in rows
    )
    deadline_misses = sum(
        row.deadline_miss_count
        for row in rows
    )
    edma_errors = sum(
        row.edma_error_count
        for row in rows
    )

    angle_statuses = {
        row.angle_status
        for row in rows
    }

    gain_samples: list[float] = []

    if profile_class != "TRACK":
        for row in rows:
            baseline = track_margin_by_condition.get(
                _condition_key(row)
            )

            if baseline is not None:
                gain_samples.append(
                    row.margin_db - baseline
                )

    gain_median = (
        median(gain_samples)
        if gain_samples
        else None
    )

    reason_codes: list[str] = []

    if overruns:
        reason_codes.append("OVERRUN")

    if deadline_misses:
        reason_codes.append(
            "DEADLINE_MISS"
        )

    if edma_errors:
        reason_codes.append("EDMA_ERROR")

    if "FAIL" in angle_statuses:
        reason_codes.append("ANGLE_FAIL")

    if max_ram > config.ram_conditional_max_pct:
        reason_codes.append(
            "RAM_OVER_CONDITIONAL_LIMIT"
        )

    functional_track = (
        min_pd >= config.pd_min
        and min_track_availability
        >= config.track_availability_min
    )

    positive_gain = (
        profile_class == "TRACK"
        or (
            gain_median is not None
            and gain_median > config.gain_min_db
        )
    )

    if (
        profile_class != "TRACK"
        and gain_median is None
    ):
        status = "HOLD"
        reason_codes.append(
            "NO_TRACK_BASELINE_MATCH"
        )

    elif not positive_gain:
        status = "FAIL"
        reason_codes.append(
            "NO_RANGE_BENEFIT"
        )

    elif (
        overruns
        or deadline_misses
        or edma_errors
        or "FAIL" in angle_statuses
        or max_ram
        > config.ram_conditional_max_pct
    ):
        status = "FAIL"

    elif profile_class == "LRX":
        status = "RESEARCH_ONLY"

    else:
        operational = (
            functional_track
            and min_update_hz
            >= config.update_min_hz
            and max_latency
            < config.latency_operational_max_ms
            and max_compute
            <= config.compute_operational_max_pct
            and max_ram
            <= config.ram_operational_max_pct
            and angle_statuses == {"PASS"}
        )

        conditional = (
            functional_track
            and min_update_hz
            >= config.update_min_hz
            and max_latency
            < config.latency_conditional_max_ms
            and max_compute
            <= config.compute_conditional_max_pct
            and max_ram
            <= config.ram_conditional_max_pct
            and "FAIL" not in angle_statuses
        )

        if operational:
            status = "OPERATIONAL"
        elif conditional:
            status = "CONDITIONAL"
        elif (
            profile_class in {"LR1", "LR2"}
            and functional_track
        ):
            status = "RESEARCH_ONLY"
            reason_codes.append(
                "NOT_OPERATIONAL_ENVELOPE"
            )
        else:
            status = "FAIL"
            if not functional_track:
                reason_codes.append(
                    "TRACK_CRITERIA"
                )

    return {
        "profile_class": profile_class,
        "profile_ids": sorted(
            {row.profile_id for row in rows}
        ),
        "run_ids": sorted(
            row.run_id for row in rows
        ),
        "status": status,
        "reason_codes": sorted(
            set(reason_codes)
        ),
        "conditions": len(rows),
        "min_pd": min_pd,
        "min_track_availability":
            min_track_availability,
        "min_fresh_fraction":
            min_fresh_fraction,
        "min_update_hz": min_update_hz,
        "max_radar_latency_p99_ms":
            max_latency,
        "max_compute_util_p99_pct":
            max_compute,
        "max_ram_peak_pct": max_ram,
        "max_sigma_az_deg": max_sigma_az,
        "max_sigma_el_deg": max_sigma_el,
        "overrun_count": overruns,
        "deadline_miss_count":
            deadline_misses,
        "edma_error_count": edma_errors,
        "angle_statuses": sorted(
            angle_statuses
        ),
        "gain_vs_track_db_samples":
            gain_samples,
        "gain_vs_track_db_median":
            gain_median,
    }


def evaluate_profile_campaign(
    metrics: list[MetricRow],
    manifests: list[tuple[str, dict]],
    config: GateConfig,
) -> dict:
    validations = [
        {
            "path": path,
            "validation":
                validate_run_manifest(manifest),
        }
        for path, manifest in manifests
    ]

    readiness, readiness_reasons = (
        _campaign_readiness(
            [
                item["validation"]
                for item in validations
            ]
        )
    )

    manifest_by_run = {
        item["validation"]["run_id"]:
            item["validation"]
        for item in validations
    }

    errors: list[str] = []

    metric_run_ids = {
        row.run_id
        for row in metrics
    }

    manifest_run_ids = set(
        manifest_by_run
    )

    missing_manifests = sorted(
        metric_run_ids - manifest_run_ids
    )

    unused_manifests = sorted(
        manifest_run_ids - metric_run_ids
    )

    if missing_manifests:
        errors.extend(
            f"missing_manifest:{run_id}"
            for run_id in missing_manifests
        )

    if unused_manifests:
        errors.extend(
            f"unused_manifest:{run_id}"
            for run_id in unused_manifests
        )

    for row in metrics:
        manifest = manifest_by_run.get(
            row.run_id
        )

        if manifest is None:
            continue

        if manifest["profile_id"] != row.profile_id:
            errors.append(
                f"profile_id_mismatch:{row.run_id}"
            )

        if not math.isclose(
            float(manifest["range_nominal_m"]),
            row.range_m,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        ):
            errors.append(
                f"range_mismatch:{row.run_id}"
            )

        if not math.isclose(
            float(manifest["rcs_m2"]),
            row.rcs_m2,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        ):
            errors.append(
                f"rcs_mismatch:{row.run_id}"
            )

    track_rows = [
        row for row in metrics
        if row.profile_class == "TRACK"
    ]

    track_margin_by_condition: dict[
        tuple[float, float, str, str],
        float,
    ] = {}

    grouped_track: dict[
        tuple[float, float, str, str],
        list[float],
    ] = {}

    for row in track_rows:
        grouped_track.setdefault(
            _condition_key(row),
            [],
        ).append(row.margin_db)

    for key, values in grouped_track.items():
        track_margin_by_condition[key] = median(
            values
        )

    grouped: dict[str, list[MetricRow]] = {}

    for row in metrics:
        grouped.setdefault(
            row.profile_class,
            [],
        ).append(row)

    profiles = {
        profile_class: _profile_summary(
            profile_class,
            rows,
            track_margin_by_condition,
            config,
        )
        for profile_class, rows
        in sorted(grouped.items())
    }

    for required in {
        "TRACK",
        "LR1",
        "LR2",
        "LRX",
    }:
        if required not in profiles:
            errors.append(
                f"missing_profile_class:{required}"
            )

    if errors:
        status = "INVALID"
    else:
        status = readiness

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "readiness_reason_codes":
            readiness_reasons,
        "errors": sorted(set(errors)),
        "config": asdict(config),
        "profiles": profiles,
        "run_validations": validations,
        "notes": [
            "TEST_READY never implies measured profile performance.",
            "MEASURED_READY requires every referenced run manifest to be MEASURED_READY.",
            "LR gain is computed only against TRACK rows with matching range/RCS/dynamics/FOV conditions.",
            "LRX remains RESEARCH_ONLY even when its sensitivity gain is positive.",
        ],
    }


def load_config(
    path: str | Path,
) -> GateConfig:
    data = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )

    return GateConfig(**data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate AWR EVM TRACK/LR profile evidence"
        )
    )

    parser.add_argument(
        "--metrics",
        required=True,
    )

    parser.add_argument(
        "--manifest",
        action="append",
        required=True,
    )

    parser.add_argument(
        "--config",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    metrics = load_metrics_csv(
        args.metrics
    )

    manifests = [
        (
            path,
            load_json(path),
        )
        for path in args.manifest
    ]

    result = evaluate_profile_campaign(
        metrics,
        manifests,
        load_config(args.config),
    )

    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {
        "TEST_READY",
        "MEASURED_READY",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
