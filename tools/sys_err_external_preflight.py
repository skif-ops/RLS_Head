from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYS-ERR-EXTERNAL-PREFLIGHT-001"
MEASURED_LEVELS = {
    "MEASURED_HIL",
    "MEASURED_BENCH",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}
REQUIRED_CONFIG = {
    "mandatory_range_m",
    "mandatory_max_position_rms_m",
    "max_timestamp_rms_us",
    "max_timestamp_abs_us",
    "min_cells",
}
REQUIRED_CELLS_COLUMNS = {
    "cell_id",
    "range_m",
    "sigma_range_m",
    "sigma_az_deg",
    "sigma_el_deg",
    "host_attitude_sigma_deg",
    "extrinsic_sigma_deg",
    "angular_rate_deg_s",
}


def _safe_path(
    root: Path,
    relative: str,
) -> Path:
    rel = Path(relative)
    if (
        rel.is_absolute()
        or ".." in rel.parts
    ):
        raise ValueError("unsafe_path")

    root_resolved = root.resolve()
    candidate = (
        root
        / rel
    ).resolve()

    try:
        candidate.relative_to(
            root_resolved
        )
    except ValueError as exc:
        raise ValueError(
            "path_escapes_root"
        ) from exc

    return candidate


def _validate_config(
    config: dict,
) -> list[str]:
    errors: list[str] = []

    missing = sorted(
        REQUIRED_CONFIG
        - set(config)
    )
    errors.extend(
        f"missing_config:{name}"
        for name in missing
    )

    if missing:
        return errors

    try:
        mandatory_range = float(
            config[
                "mandatory_range_m"
            ]
        )
        mandatory_rms = float(
            config[
                "mandatory_max_position_rms_m"
            ]
        )
        timestamp_rms = float(
            config[
                "max_timestamp_rms_us"
            ]
        )
        timestamp_abs = float(
            config[
                "max_timestamp_abs_us"
            ]
        )
        min_cells = int(
            config[
                "min_cells"
            ]
        )
    except (
        TypeError,
        ValueError,
    ):
        return [
            "invalid_config_value"
        ]

    if mandatory_range <= 0:
        errors.append(
            "invalid_config:mandatory_range_m"
        )
    if mandatory_rms <= 0:
        errors.append(
            "invalid_config:mandatory_max_position_rms_m"
        )
    if timestamp_rms < 0:
        errors.append(
            "invalid_config:max_timestamp_rms_us"
        )
    if timestamp_abs < 0:
        errors.append(
            "invalid_config:max_timestamp_abs_us"
        )
    if min_cells < 1:
        errors.append(
            "invalid_config:min_cells"
        )

    return errors


def evaluate_preflight(
    *,
    manifest: dict,
    gate_config: dict,
    repository_root: str | Path,
) -> dict:
    root = Path(repository_root)
    errors = _validate_config(
        gate_config
    )
    warnings: list[str] = []

    if (
        manifest.get("schema")
        != "SYS-ERR-MEASUREMENT-MANIFEST-001"
    ):
        errors.append(
            "manifest_schema"
        )

    if (
        manifest.get(
            "synthetic_fixture"
        )
        is not False
    ):
        errors.append(
            "synthetic_fixture_not_false"
        )

    evidence_level = str(
        manifest.get(
            "evidence_level",
            "",
        )
    ).strip()

    if (
        evidence_level
        not in MEASURED_LEVELS
    ):
        errors.append(
            "unsupported_evidence_level"
        )

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

    timing_path = None
    cells_path = None

    for label, entry in (
        (
            "timing",
            timing_entry,
        ),
        (
            "cells",
            cells_entry,
        ),
    ):
        relative = str(
            entry.get(
                "path",
                "",
            )
        ).strip()

        if (
            not relative
            or "<FILL" in relative
        ):
            errors.append(
                f"{label}:missing_or_placeholder_path"
            )
            continue

        try:
            path = _safe_path(
                root,
                relative,
            )
        except ValueError as exc:
            errors.append(
                f"{label}:{exc}"
            )
            continue

        expected = str(
            entry.get(
                "sha256",
                "",
            )
        ).strip().lower()

        if (
            not expected
            or "<fill" in expected
            or len(expected) != 64
            or any(
                ch not in
                "0123456789abcdef"
                for ch in expected
            )
        ):
            warnings.append(
                f"{label}:sha256_not_final"
            )

        if label == "timing":
            timing_path = path
        else:
            cells_path = path

    timing_ready = False

    if timing_path is not None:
        if not timing_path.is_file():
            warnings.append(
                "timing:not_present_yet"
            )
        else:
            try:
                timing = json.loads(
                    timing_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                json.JSONDecodeError,
            ):
                errors.append(
                    "timing:invalid_json"
                )
            else:
                if (
                    timing.get("schema")
                    !=
                    "HIL-R2-BENCH-EVIDENCE-001"
                ):
                    errors.append(
                        "timing:unexpected_schema"
                    )
                elif (
                    timing.get(
                        "gate_status"
                    )
                    != "PASS"
                ):
                    errors.append(
                        "timing:not_pass"
                    )
                else:
                    timing_ready = True

    if cells_path is not None:
        if not cells_path.is_file():
            errors.append(
                "cells:missing_file"
            )
        else:
            try:
                with cells_path.open(
                    "r",
                    encoding="utf-8",
                    newline="",
                ) as handle:
                    reader = (
                        csv.DictReader(
                            handle
                        )
                    )
                    if (
                        reader.fieldnames
                        is None
                        or not
                        REQUIRED_CELLS_COLUMNS
                        .issubset(
                            reader.fieldnames
                        )
                    ):
                        errors.append(
                            "cells:header"
                        )
                        rows = []
                    else:
                        rows = list(
                            reader
                        )
            except OSError:
                errors.append(
                    "cells:read"
                )
                rows = []

            if (
                cells_path.is_file()
                and not errors
                and not rows
            ):
                warnings.append(
                    "cells:no_samples_yet"
                )

    if errors:
        status = "BLOCKED"
    elif not timing_ready:
        status = (
            "WAITING_FOR_HIL_R2"
        )
    else:
        status = (
            "READY_FOR_COLLECTION"
        )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(
            set(errors)
        ),
        "warnings": sorted(
            set(warnings)
        ),
        "timing_ready": (
            timing_ready
        ),
        "notes": [
            (
                "WAITING_FOR_HIL_R2 preserves the explicit dependency "
                "on real HIL-R2 bench PASS evidence."
            ),
            (
                "READY_FOR_COLLECTION means SYS-ERR uncertainty cells "
                "can be completed against verified timing evidence."
            ),
            (
                "This preflight does not calculate or assert SYS-ERR-GATE PASS."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight measured SYS-ERR "
            "evidence assembly"
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

    manifest = json.loads(
        Path(
            args.manifest
        ).read_text(
            encoding="utf-8"
        )
    )
    config = json.loads(
        Path(
            args.config
        ).read_text(
            encoding="utf-8"
        )
    )

    result = evaluate_preflight(
        manifest=manifest,
        gate_config=config,
        repository_root=
            args.repository_root,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        result["status"]
    )

    return (
        0
        if result["status"]
        in {
            "WAITING_FOR_HIL_R2",
            "READY_FOR_COLLECTION",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
