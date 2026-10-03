from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


MANIFEST_SCHEMA = "SYS-ERR-MEASUREMENT-MANIFEST-001"
RESULT_SCHEMA = "SYS-ERR-GATE-001"

MEASURED_LEVELS = {
    "MEASURED_HIL",
    "MEASURED_BENCH",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}


@dataclass(frozen=True)
class GateConfig:
    mandatory_range_m: float
    mandatory_max_position_rms_m: float
    max_timestamp_rms_us: float
    max_timestamp_abs_us: float
    min_cells: int


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe evidence path")

    root_resolved = root.resolve()
    candidate = (root / rel).resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            "evidence path escapes repository root"
        ) from exc

    return candidate


def load_config(path: str | Path) -> GateConfig:
    data = load_json(path)

    cfg = GateConfig(
        mandatory_range_m=float(
            data["mandatory_range_m"]
        ),
        mandatory_max_position_rms_m=float(
            data["mandatory_max_position_rms_m"]
        ),
        max_timestamp_rms_us=float(
            data["max_timestamp_rms_us"]
        ),
        max_timestamp_abs_us=float(
            data["max_timestamp_abs_us"]
        ),
        min_cells=int(data["min_cells"]),
    )

    if (
        cfg.mandatory_range_m <= 0.0
        or cfg.mandatory_max_position_rms_m <= 0.0
        or cfg.max_timestamp_rms_us < 0.0
        or cfg.max_timestamp_abs_us < 0.0
        or cfg.min_cells < 1
    ):
        raise ValueError("invalid SYS-ERR gate configuration")

    return cfg


def _finite_float(raw: str, field: str) -> float:
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


def load_cells(path: str | Path) -> list[dict]:
    required = {
        "cell_id",
        "range_m",
        "sigma_range_m",
        "sigma_az_deg",
        "sigma_el_deg",
        "host_attitude_sigma_deg",
        "extrinsic_sigma_deg",
        "angular_rate_deg_s",
    }

    rows: list[dict] = []

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
                "SYS-ERR CSV missing required columns"
            )

        seen = set()

        for line_number, raw in enumerate(
            reader,
            start=2,
        ):
            cell_id = str(
                raw.get("cell_id", "")
            ).strip()

            if not cell_id:
                raise ValueError(
                    f"line {line_number}: blank cell_id"
                )

            if cell_id in seen:
                raise ValueError(
                    f"line {line_number}: duplicate cell_id"
                )

            seen.add(cell_id)

            row = {
                "cell_id": cell_id,
                "range_m": _finite_float(
                    raw["range_m"],
                    "range_m",
                ),
                "sigma_range_m": _finite_float(
                    raw["sigma_range_m"],
                    "sigma_range_m",
                ),
                "sigma_az_deg": _finite_float(
                    raw["sigma_az_deg"],
                    "sigma_az_deg",
                ),
                "sigma_el_deg": _finite_float(
                    raw["sigma_el_deg"],
                    "sigma_el_deg",
                ),
                "host_attitude_sigma_deg":
                    _finite_float(
                        raw[
                            "host_attitude_sigma_deg"
                        ],
                        "host_attitude_sigma_deg",
                    ),
                "extrinsic_sigma_deg":
                    _finite_float(
                        raw[
                            "extrinsic_sigma_deg"
                        ],
                        "extrinsic_sigma_deg",
                    ),
                "angular_rate_deg_s":
                    _finite_float(
                        raw[
                            "angular_rate_deg_s"
                        ],
                        "angular_rate_deg_s",
                    ),
            }

            for name in (
                "range_m",
                "sigma_range_m",
                "sigma_az_deg",
                "sigma_el_deg",
                "host_attitude_sigma_deg",
                "extrinsic_sigma_deg",
                "angular_rate_deg_s",
            ):
                if row[name] < 0.0:
                    raise ValueError(
                        f"line {line_number}: negative {name}"
                    )

            if row["range_m"] <= 0.0:
                raise ValueError(
                    f"line {line_number}: range must be positive"
                )

            rows.append(row)

    if not rows:
        raise ValueError("SYS-ERR cell CSV is empty")

    return rows


def _cell_result(
    row: dict,
    timestamp_sigma_us: float,
) -> dict:
    range_m = row["range_m"]

    sigma_az = math.radians(
        row["sigma_az_deg"]
    )
    sigma_el = math.radians(
        row["sigma_el_deg"]
    )
    sigma_att = math.radians(
        row["host_attitude_sigma_deg"]
    )
    sigma_ext = math.radians(
        row["extrinsic_sigma_deg"]
    )
    omega = math.radians(
        row["angular_rate_deg_s"]
    )
    sigma_t = timestamp_sigma_us * 1.0e-6

    range_var = (
        row["sigma_range_m"]
        * row["sigma_range_m"]
    )

    az_var = (
        range_m
        * range_m
        * (
            sigma_az * sigma_az
            + sigma_att * sigma_att
            + sigma_ext * sigma_ext
        )
    )

    el_var = (
        range_m
        * range_m
        * (
            sigma_el * sigma_el
            + sigma_att * sigma_att
            + sigma_ext * sigma_ext
        )
    )

    timing_sigma_m = (
        range_m
        * omega
        * sigma_t
    )
    timing_var = (
        timing_sigma_m
        * timing_sigma_m
    )

    total_var = (
        range_var
        + az_var
        + el_var
        + timing_var
    )

    position_rms_m = math.sqrt(
        max(0.0, total_var)
    )

    contributions = {
        "range_var_m2": range_var,
        "az_att_ext_var_m2": az_var,
        "el_att_ext_var_m2": el_var,
        "timing_var_m2": timing_var,
    }

    dominant = max(
        contributions,
        key=contributions.get,
    )

    return {
        **row,
        "timestamp_sigma_us":
            timestamp_sigma_us,
        "timing_sigma_m":
            timing_sigma_m,
        "position_rms_m":
            position_rms_m,
        "variance_contributions":
            contributions,
        "dominant_contribution":
            dominant,
    }


def evaluate_gate(
    *,
    manifest: dict,
    config: GateConfig,
    repository_root: str | Path,
) -> dict:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(
            "unexpected SYS-ERR measurement manifest schema"
        )

    root = Path(repository_root)
    errors: list[str] = []

    synthetic = bool(
        manifest.get("synthetic_fixture", False)
    )
    evidence_level = str(
        manifest.get("evidence_level", "")
    ).strip()

    timing_entry = manifest.get(
        "timing_evidence"
    )
    cells_entry = manifest.get(
        "cells_csv"
    )

    if not isinstance(
        timing_entry,
        dict,
    ):
        errors.append(
            "missing_timing_evidence"
        )
        timing_entry = {}

    if not isinstance(
        cells_entry,
        dict,
    ):
        errors.append(
            "missing_cells_csv"
        )
        cells_entry = {}

    def verify(
        entry: dict,
        label: str,
    ) -> Path | None:
        relative = str(
            entry.get("path", "")
        ).strip()
        expected = str(
            entry.get("sha256", "")
        ).strip().lower()

        if not relative:
            errors.append(
                f"{label}:missing_path"
            )
            return None

        if (
            len(expected) != 64
            or any(
                ch not in "0123456789abcdef"
                for ch in expected
            )
        ):
            errors.append(
                f"{label}:invalid_sha256"
            )
            return None

        try:
            path = safe_path(
                root,
                relative,
            )
        except ValueError as exc:
            errors.append(
                f"{label}:{exc}"
            )
            return None

        if not path.is_file():
            errors.append(
                f"{label}:missing_file"
            )
            return None

        actual = sha256_file(path)

        if actual != expected:
            errors.append(
                f"{label}:hash_mismatch"
            )

        return path

    timing_path = verify(
        timing_entry,
        "timing",
    )
    cells_path = verify(
        cells_entry,
        "cells",
    )

    timing = {}

    if timing_path is not None:
        try:
            timing = load_json(
                timing_path
            )
        except json.JSONDecodeError as exc:
            errors.append(
                f"timing:json:{exc}"
            )

    if timing:
        if (
            timing.get("schema")
            != "HIL-R2-BENCH-EVIDENCE-001"
        ):
            errors.append(
                "timing:unexpected_schema"
            )

        if timing.get("gate_status") != "PASS":
            errors.append(
                "timing:not_pass"
            )

    rows: list[dict] = []

    if cells_path is not None:
        try:
            rows = load_cells(
                cells_path
            )
        except ValueError as exc:
            errors.append(
                f"cells:{exc}"
            )

    if errors:
        return {
            "schema": RESULT_SCHEMA,
            "status": "INVALID",
            "evidence_level":
                evidence_level,
            "synthetic_fixture":
                synthetic,
            "errors": errors,
            "reason_codes": [],
        }

    radar_imu = timing.get(
        "radar_imu",
        {},
    )

    try:
        timestamp_rms_us = float(
            radar_imu["rms_us"]
        )
        timestamp_max_abs_us = float(
            radar_imu["max_abs_us"]
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "timing evidence missing Radar-IMU residual statistics"
        ) from exc

    if (
        not math.isfinite(
            timestamp_rms_us
        )
        or not math.isfinite(
            timestamp_max_abs_us
        )
        or timestamp_rms_us < 0.0
        or timestamp_max_abs_us < 0.0
    ):
        raise ValueError(
            "invalid timing residual statistics"
        )

    cell_results = [
        _cell_result(
            row,
            timestamp_rms_us,
        )
        for row in rows
    ]

    reasons: list[str] = []

    if len(cell_results) < config.min_cells:
        reasons.append(
            "insufficient_cells"
        )

    if (
        timestamp_rms_us
        > config.max_timestamp_rms_us
    ):
        reasons.append(
            "timestamp_rms"
        )

    if (
        timestamp_max_abs_us
        > config.max_timestamp_abs_us
    ):
        reasons.append(
            "timestamp_max_abs"
        )

    mandatory = [
        cell
        for cell in cell_results
        if math.isclose(
            cell["range_m"],
            config.mandatory_range_m,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
    ]

    if not mandatory:
        reasons.append(
            "mandatory_range_missing"
        )

    mandatory_fail = [
        cell
        for cell in mandatory
        if (
            cell["position_rms_m"]
            > config.mandatory_max_position_rms_m
        )
    ]

    if mandatory_fail:
        reasons.append(
            "mandatory_position_rms"
        )

    if reasons:
        raw_status = "FAIL"
    else:
        raw_status = "PASS"

    if synthetic:
        status = (
            "TEST_READY"
            if raw_status == "PASS"
            else raw_status
        )
    elif evidence_level not in MEASURED_LEVELS:
        status = "HOLD"
    else:
        status = raw_status

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "gate_status": raw_status,
        "evidence_level":
            evidence_level,
        "synthetic_fixture":
            synthetic,
        "errors": [],
        "reason_codes":
            sorted(set(reasons)),
        "config": asdict(config),
        "timestamp": {
            "rms_us":
                timestamp_rms_us,
            "max_abs_us":
                timestamp_max_abs_us,
        },
        "cells": cell_results,
        "mandatory_cells": mandatory,
        "max_position_rms_m":
            max(
                (
                    cell[
                        "position_rms_m"
                    ]
                    for cell in cell_results
                ),
                default=None,
            ),
        "notes": [
            "Position RMS is a first-order sensing uncertainty budget.",
            "Timing sigma is taken from measured Radar-IMU residual RMS.",
            "Synthetic fixtures cannot produce physical SYS_ERR_MEASURED PASS.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build measured SYS-ERR-GATE-001 from timing and angle/range evidence"
        )
    )

    parser.add_argument(
        "--manifest",
        required=True,
    )
    parser.add_argument(
        "--config",
        required=True,
    )
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = evaluate_gate(
        manifest=load_json(
            args.manifest
        ),
        config=load_config(
            args.config
        ),
        repository_root=
            args.repository_root,
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
        "PASS",
        "TEST_READY",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
