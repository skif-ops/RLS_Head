from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


MANIFEST_SCHEMA = "ANT-MEASUREMENT-MANIFEST-001"
RESULT_SCHEMA = "ANT-MEASUREMENT-001"

REQUIRED_COLUMNS = {
    "measurement_id",
    "frequency_hz",
    "az_deg",
    "el_deg",
    "realized_gain_db",
    "gain_uncertainty_db",
    "sigma_az_deg",
    "sigma_el_deg",
    "ambiguity_flag",
    "track_usable",
    "high_acc_usable",
    "repeat_count",
}

MEASURED_LEVELS = {
    "MEASURED_EM",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}


@dataclass(frozen=True)
class MeasurementConfig:
    required_frequencies_hz: tuple[float, ...]
    min_points_per_frequency: int
    require_boresight: bool
    boresight_tolerance_deg: float
    max_gain_uncertainty_db: float
    min_repeat_count: int
    min_track_usable_points: int
    min_high_acc_usable_points: int


def load_json(path: str | Path) -> dict:
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(
    root: Path,
    relative: str,
) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe measurement path")

    root_resolved = root.resolve()
    candidate = (root / rel).resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            "measurement path escapes repository root"
        ) from exc

    return candidate


def load_config(
    path: str | Path,
) -> MeasurementConfig:
    data = load_json(path)

    cfg = MeasurementConfig(
        required_frequencies_hz=tuple(
            float(value)
            for value in data[
                "required_frequencies_hz"
            ]
        ),
        min_points_per_frequency=int(
            data["min_points_per_frequency"]
        ),
        require_boresight=bool(
            data["require_boresight"]
        ),
        boresight_tolerance_deg=float(
            data["boresight_tolerance_deg"]
        ),
        max_gain_uncertainty_db=float(
            data["max_gain_uncertainty_db"]
        ),
        min_repeat_count=int(
            data["min_repeat_count"]
        ),
        min_track_usable_points=int(
            data["min_track_usable_points"]
        ),
        min_high_acc_usable_points=int(
            data["min_high_acc_usable_points"]
        ),
    )

    if cfg.min_points_per_frequency < 1:
        raise ValueError(
            "min_points_per_frequency must be >= 1"
        )

    if cfg.min_repeat_count < 1:
        raise ValueError(
            "min_repeat_count must be >= 1"
        )

    if cfg.max_gain_uncertainty_db < 0.0:
        raise ValueError(
            "max_gain_uncertainty_db must be >= 0"
        )

    if cfg.boresight_tolerance_deg < 0.0:
        raise ValueError(
            "boresight_tolerance_deg must be >= 0"
        )

    return cfg


def _bool01(
    raw: str,
    field: str,
) -> bool:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{field} must be 0 or 1"
        ) from exc

    if value not in (0, 1):
        raise ValueError(
            f"{field} must be 0 or 1"
        )

    return bool(value)


def _finite_float(
    raw: str,
    field: str,
) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"invalid {field}"
        ) from exc

    if not math.isfinite(value):
        raise ValueError(
            f"non-finite {field}"
        )

    return value


def load_rows(
    path: str | Path,
) -> list[dict]:
    with Path(path).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if (
            reader.fieldnames is None
            or not REQUIRED_COLUMNS.issubset(
                reader.fieldnames
            )
        ):
            raise ValueError(
                "physical antenna CSV missing required columns"
            )

        parsed: list[dict] = []

        for index, row in enumerate(
            reader,
            start=2,
        ):
            measurement_id = str(
                row["measurement_id"]
            ).strip()

            if not measurement_id:
                raise ValueError(
                    f"row {index}: blank measurement_id"
                )

            frequency_hz = _finite_float(
                row["frequency_hz"],
                "frequency_hz",
            )
            az_deg = _finite_float(
                row["az_deg"],
                "az_deg",
            )
            el_deg = _finite_float(
                row["el_deg"],
                "el_deg",
            )
            realized_gain_db = _finite_float(
                row["realized_gain_db"],
                "realized_gain_db",
            )
            gain_uncertainty_db = _finite_float(
                row["gain_uncertainty_db"],
                "gain_uncertainty_db",
            )
            sigma_az_deg = _finite_float(
                row["sigma_az_deg"],
                "sigma_az_deg",
            )
            sigma_el_deg = _finite_float(
                row["sigma_el_deg"],
                "sigma_el_deg",
            )

            try:
                repeat_count = int(
                    row["repeat_count"]
                )
            except ValueError as exc:
                raise ValueError(
                    f"row {index}: invalid repeat_count"
                ) from exc

            if frequency_hz <= 0.0:
                raise ValueError(
                    f"row {index}: frequency must be positive"
                )

            if not -180.0 <= az_deg <= 180.0:
                raise ValueError(
                    f"row {index}: az outside [-180,180]"
                )

            if not -90.0 <= el_deg <= 90.0:
                raise ValueError(
                    f"row {index}: el outside [-90,90]"
                )

            if (
                gain_uncertainty_db < 0.0
                or sigma_az_deg < 0.0
                or sigma_el_deg < 0.0
                or repeat_count < 1
            ):
                raise ValueError(
                    f"row {index}: negative uncertainty/sigma or invalid repeats"
                )

            ambiguity = _bool01(
                row["ambiguity_flag"],
                "ambiguity_flag",
            )
            track_usable = _bool01(
                row["track_usable"],
                "track_usable",
            )
            high_acc_usable = _bool01(
                row["high_acc_usable"],
                "high_acc_usable",
            )

            if ambiguity and track_usable:
                raise ValueError(
                    f"row {index}: ambiguous cell cannot be track usable"
                )

            if (
                high_acc_usable
                and not track_usable
            ):
                raise ValueError(
                    f"row {index}: high-accuracy cell requires TRACK usability"
                )

            parsed.append(
                {
                    "measurement_id":
                        measurement_id,
                    "frequency_hz":
                        frequency_hz,
                    "az_deg": az_deg,
                    "el_deg": el_deg,
                    "realized_gain_db":
                        realized_gain_db,
                    "gain_uncertainty_db":
                        gain_uncertainty_db,
                    "sigma_az_deg":
                        sigma_az_deg,
                    "sigma_el_deg":
                        sigma_el_deg,
                    "ambiguity_flag":
                        ambiguity,
                    "track_usable":
                        track_usable,
                    "high_acc_usable":
                        high_acc_usable,
                    "repeat_count":
                        repeat_count,
                }
            )

    if not parsed:
        raise ValueError(
            "physical antenna CSV is empty"
        )

    return parsed


def evaluate_rows(
    rows: list[dict],
    config: MeasurementConfig,
) -> dict:
    reasons: list[str] = []
    groups = {}

    seen = set()
    duplicates = []

    for row in rows:
        key = (
            row["measurement_id"],
            row["frequency_hz"],
            row["az_deg"],
            row["el_deg"],
        )

        if key in seen:
            duplicates.append(key)

        seen.add(key)

        groups.setdefault(
            row["frequency_hz"],
            [],
        ).append(row)

    if duplicates:
        reasons.append("duplicate_points")

    missing_frequencies = []
    underfilled = []
    missing_boresight = []

    required_keys = []

    for frequency in (
        config.required_frequencies_hz
    ):
        matching = None

        for actual in groups:
            if math.isclose(
                actual,
                frequency,
                rel_tol=0.0,
                abs_tol=1.0,
            ):
                matching = actual
                break

        if matching is None:
            missing_frequencies.append(
                frequency
            )
            continue

        required_keys.append(matching)
        group = groups[matching]

        if (
            len(group)
            < config.min_points_per_frequency
        ):
            underfilled.append(
                {
                    "frequency_hz":
                        matching,
                    "count":
                        len(group),
                }
            )

        if config.require_boresight:
            if not any(
                abs(row["az_deg"])
                <= config.boresight_tolerance_deg
                and abs(row["el_deg"])
                <= config.boresight_tolerance_deg
                for row in group
            ):
                missing_boresight.append(
                    matching
                )

    if missing_frequencies:
        reasons.append(
            "missing_frequencies"
        )

    if underfilled:
        reasons.append(
            "underfilled_frequencies"
        )

    if missing_boresight:
        reasons.append(
            "missing_boresight"
        )

    uncertainty_fail = [
        row
        for row in rows
        if row["gain_uncertainty_db"]
        > config.max_gain_uncertainty_db
    ]

    repeat_fail = [
        row
        for row in rows
        if row["repeat_count"]
        < config.min_repeat_count
    ]

    if uncertainty_fail:
        reasons.append(
            "gain_uncertainty"
        )

    if repeat_fail:
        reasons.append(
            "repeat_count"
        )

    required_rows = [
        row
        for key in required_keys
        for row in groups[key]
    ]

    track_points = sum(
        1
        for row in required_rows
        if row["track_usable"]
        and not row["ambiguity_flag"]
    )

    high_acc_points = sum(
        1
        for row in required_rows
        if row["high_acc_usable"]
        and not row["ambiguity_flag"]
    )

    ambiguity_points = sum(
        1
        for row in required_rows
        if row["ambiguity_flag"]
    )

    mandatory_fail = False
    conditional = False

    if (
        track_points
        < config.min_track_usable_points
    ):
        mandatory_fail = True
        reasons.append(
            "track_usable_region"
        )

    elif (
        high_acc_points
        < config.min_high_acc_usable_points
    ):
        conditional = True
        reasons.append(
            "high_acc_region"
        )

    summaries = []

    for frequency, group in sorted(
        groups.items()
    ):
        summaries.append(
            {
                "frequency_hz":
                    frequency,
                "point_count":
                    len(group),
                "realized_gain_min_db":
                    min(
                        row[
                            "realized_gain_db"
                        ]
                        for row in group
                    ),
                "realized_gain_max_db":
                    max(
                        row[
                            "realized_gain_db"
                        ]
                        for row in group
                    ),
                "gain_uncertainty_max_db":
                    max(
                        row[
                            "gain_uncertainty_db"
                        ]
                        for row in group
                    ),
                "sigma_az_max_deg":
                    max(
                        row["sigma_az_deg"]
                        for row in group
                    ),
                "sigma_el_max_deg":
                    max(
                        row["sigma_el_deg"]
                        for row in group
                    ),
                "track_usable_count":
                    sum(
                        1
                        for row in group
                        if row[
                            "track_usable"
                        ]
                    ),
                "high_acc_usable_count":
                    sum(
                        1
                        for row in group
                        if row[
                            "high_acc_usable"
                        ]
                    ),
                "ambiguity_count":
                    sum(
                        1
                        for row in group
                        if row[
                            "ambiguity_flag"
                        ]
                    ),
            }
        )

    structural = {
        "duplicate_points",
        "missing_frequencies",
        "underfilled_frequencies",
        "missing_boresight",
    }

    if any(
        reason in structural
        for reason in reasons
    ):
        status = "INCOMPLETE"
    elif (
        "gain_uncertainty" in reasons
        or "repeat_count" in reasons
        or mandatory_fail
    ):
        status = "FAIL"
    elif conditional:
        status = "CONDITIONAL"
    else:
        status = "PASS"

    return {
        "status": status,
        "reason_codes":
            sorted(set(reasons)),
        "row_count": len(rows),
        "measurement_ids": sorted(
            {
                row["measurement_id"]
                for row in rows
            }
        ),
        "track_usable_point_count":
            track_points,
        "high_acc_usable_point_count":
            high_acc_points,
        "ambiguity_point_count":
            ambiguity_points,
        "missing_frequencies_hz":
            missing_frequencies,
        "underfilled_frequencies":
            underfilled,
        "missing_boresight_hz":
            missing_boresight,
        "groups": summaries,
    }


def evaluate_measurement(
    *,
    manifest: dict,
    config: MeasurementConfig,
    repository_root: str | Path,
) -> dict:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(
            "unexpected antenna measurement manifest schema"
        )

    root = Path(repository_root)
    errors: list[str] = []

    measurement_id = str(
        manifest.get(
            "measurement_id",
            "",
        )
    ).strip()

    if not measurement_id:
        errors.append(
            "missing_measurement_id"
        )

    synthetic = bool(
        manifest.get(
            "synthetic_fixture",
            False,
        )
    )

    evidence_level = str(
        manifest.get(
            "evidence_level",
            "",
        )
    ).strip()

    source = manifest.get("measurement_csv")

    if not isinstance(source, dict):
        errors.append(
            "missing_measurement_csv"
        )
        source = {}

    relative = str(
        source.get("path", "")
    ).strip()

    expected_hash = str(
        source.get("sha256", "")
    ).strip().lower()

    csv_path = None

    if not relative:
        errors.append(
            "missing_measurement_csv_path"
        )
    else:
        try:
            csv_path = safe_path(
                root,
                relative,
            )
        except ValueError as exc:
            errors.append(
                f"measurement_csv_path:{exc}"
            )

    if (
        len(expected_hash) != 64
        or any(
            ch not in "0123456789abcdef"
            for ch in expected_hash
        )
    ):
        errors.append(
            "invalid_measurement_csv_sha256"
        )

    actual_hash = None

    if csv_path is not None:
        if not csv_path.is_file():
            errors.append(
                "measurement_csv_missing"
            )
        else:
            actual_hash = sha256_file(
                csv_path
            )

            if actual_hash != expected_hash:
                errors.append(
                    "measurement_csv_hash_mismatch"
                )

    if errors:
        return {
            "schema": RESULT_SCHEMA,
            "status": "INVALID",
            "measurement_id":
                measurement_id,
            "synthetic_fixture":
                synthetic,
            "evidence_level":
                evidence_level,
            "errors": errors,
        }

    rows = load_rows(csv_path)

    wrong_ids = sorted(
        {
            row["measurement_id"]
            for row in rows
            if row["measurement_id"]
            != measurement_id
        }
    )

    if wrong_ids:
        return {
            "schema": RESULT_SCHEMA,
            "status": "INVALID",
            "measurement_id":
                measurement_id,
            "synthetic_fixture":
                synthetic,
            "evidence_level":
                evidence_level,
            "errors": [
                "measurement_id_mismatch"
            ],
            "csv_measurement_ids":
                wrong_ids,
        }

    evaluated = evaluate_rows(
        rows,
        config,
    )

    raw_status = evaluated.pop(
        "status"
    )

    if synthetic:
        status = (
            "TEST_READY"
            if raw_status
            in {"PASS", "CONDITIONAL"}
            else raw_status
        )
    elif evidence_level not in MEASURED_LEVELS:
        status = "HOLD"
    else:
        status = raw_status

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "measurement_status":
            raw_status,
        "measurement_id":
            measurement_id,
        "synthetic_fixture":
            synthetic,
        "evidence_level":
            evidence_level,
        "instrument_id": str(
            manifest.get(
                "instrument_id",
                "",
            )
        ),
        "calibration_id": str(
            manifest.get(
                "calibration_id",
                "",
            )
        ),
        "measurement_csv": {
            "path": relative,
            "sha256": actual_hash,
        },
        "config": asdict(config),
        "errors": [],
        **evaluated,
        "notes": [
            "No production Tx/Rx physical coordinates are encoded.",
            "TEST_READY is synthetic CI only and cannot close physical antenna evidence.",
            "PASS/CONDITIONAL/FAIL requires a non-synthetic measured evidence level.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate physical antenna measurement evidence"
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

    result = evaluate_measurement(
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
        "CONDITIONAL",
        "TEST_READY",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
