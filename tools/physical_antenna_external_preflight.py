from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "PHYSICAL-ANTENNA-EXTERNAL-PREFLIGHT-001"
MEASURED_LEVELS = {
    "MEASURED_EM",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}
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


def _safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe_path")
    root_resolved = root.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("path_escapes_root") from exc
    return candidate


def _filled(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and "<FILL" not in text


def _validate_config(config: dict) -> list[str]:
    errors: list[str] = []

    required = (
        "required_frequencies_hz",
        "min_points_per_frequency",
        "require_boresight",
        "boresight_tolerance_deg",
        "max_gain_uncertainty_db",
        "min_repeat_count",
        "min_track_usable_points",
        "min_high_acc_usable_points",
    )

    for name in required:
        if name not in config:
            errors.append(f"missing_config:{name}")

    if errors:
        return errors

    freqs = config.get("required_frequencies_hz")
    if (
        not isinstance(freqs, list)
        or not freqs
    ):
        errors.append("invalid_config:required_frequencies_hz")
    else:
        try:
            if any(float(value) <= 0.0 for value in freqs):
                errors.append("invalid_config:required_frequencies_hz")
        except (TypeError, ValueError):
            errors.append("invalid_config:required_frequencies_hz")

    for name in (
        "min_points_per_frequency",
        "min_repeat_count",
        "min_track_usable_points",
        "min_high_acc_usable_points",
    ):
        try:
            if int(config[name]) < 1:
                errors.append(f"invalid_config:{name}")
        except (TypeError, ValueError):
            errors.append(f"invalid_config:{name}")

    for name in (
        "boresight_tolerance_deg",
        "max_gain_uncertainty_db",
    ):
        try:
            if float(config[name]) < 0.0:
                errors.append(f"invalid_config:{name}")
        except (TypeError, ValueError):
            errors.append(f"invalid_config:{name}")

    return sorted(set(errors))


def evaluate_preflight(
    *,
    manifest: dict,
    gate_config: dict,
    repository_root: str | Path,
) -> dict:
    root = Path(repository_root)
    errors = _validate_config(gate_config)
    warnings: list[str] = []

    if manifest.get("schema") != "ANT-MEASUREMENT-MANIFEST-001":
        errors.append("manifest_schema")

    for field in (
        "measurement_id",
        "instrument_id",
        "calibration_id",
    ):
        if not _filled(manifest.get(field)):
            errors.append(f"missing_or_placeholder:{field}")

    if manifest.get("synthetic_fixture") is not False:
        errors.append("synthetic_fixture_not_false")

    evidence_level = str(
        manifest.get("evidence_level", "")
    ).strip()

    if evidence_level not in MEASURED_LEVELS:
        errors.append("unsupported_evidence_level")

    source = manifest.get("measurement_csv")
    if not isinstance(source, dict):
        errors.append("missing_measurement_csv")
        source = {}

    relative = str(source.get("path", "")).strip()
    csv_path = None

    if not relative or "<FILL" in relative:
        errors.append("measurement_csv:missing_or_placeholder_path")
    else:
        try:
            csv_path = _safe_path(root, relative)
        except ValueError as exc:
            errors.append(f"measurement_csv:{exc}")

    expected_hash = str(
        source.get("sha256", "")
    ).strip().lower()

    if (
        not expected_hash
        or "<fill" in expected_hash
        or len(expected_hash) != 64
        or any(
            ch not in "0123456789abcdef"
            for ch in expected_hash
        )
    ):
        warnings.append("measurement_csv:sha256_not_final")

    frequencies: set[float] = set()

    if csv_path is not None:
        if not csv_path.is_file():
            errors.append("measurement_csv:missing_file")
        else:
            try:
                with csv_path.open(
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
                        errors.append("measurement_csv:header")
                        rows = []
                    else:
                        rows = list(reader)
            except OSError:
                errors.append("measurement_csv:read")
                rows = []

            if not rows:
                warnings.append("measurement_csv:no_samples_yet")
            else:
                for index, row in enumerate(rows, start=2):
                    row_measurement_id = str(
                        row.get("measurement_id", "")
                    ).strip()
                    if (
                        row_measurement_id
                        and _filled(manifest.get("measurement_id"))
                        and row_measurement_id
                        != str(manifest["measurement_id"]).strip()
                    ):
                        errors.append(
                            f"measurement_id_mismatch:{index}"
                        )
                    try:
                        frequency = float(
                            row["frequency_hz"]
                        )
                        if frequency <= 0.0:
                            raise ValueError
                        frequencies.add(frequency)
                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        errors.append(
                            f"invalid_frequency:{index}"
                        )

    required_freqs = []
    for value in gate_config.get(
        "required_frequencies_hz",
        [],
    ):
        try:
            required_freqs.append(float(value))
        except (TypeError, ValueError):
            pass

    if frequencies and required_freqs:
        missing = [
            required
            for required in required_freqs
            if not any(
                abs(actual - required) <= 1.0
                for actual in frequencies
            )
        ]
        if missing:
            warnings.append(
                "missing_required_frequencies:"
                + ",".join(
                    str(int(value))
                    for value in missing
                )
            )

    status = (
        "READY_FOR_COLLECTION"
        if not errors
        else "BLOCKED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "required_frequencies_hz": required_freqs,
        "notes": [
            (
                "READY_FOR_COLLECTION means the physical antenna measurement "
                "package is structurally ready for real data collection."
            ),
            (
                "This preflight does not evaluate gain/FOV/angle/ambiguity "
                "performance or modify antenna geometry."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a physical antenna measurement package"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(
        Path(args.manifest).read_text(encoding="utf-8")
    )
    config = json.loads(
        Path(args.config).read_text(encoding="utf-8")
    )

    result = evaluate_preflight(
        manifest=manifest,
        gate_config=config,
        repository_root=args.repository_root,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY_FOR_COLLECTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
