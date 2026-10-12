from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "EVM-PROFILE-EXTERNAL-PREFLIGHT-001"
REQUIRED_PROFILES = {"TRACK", "LR1", "LR2", "LRX"}

REQUIRED_COLUMNS = {
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


def evaluate_preflight(
    *,
    metrics_csv: str | Path,
    manifest_dir: str | Path,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    metrics_path = Path(metrics_csv)
    classes_in_csv: set[str] = set()

    if not metrics_path.is_file():
        errors.append("metrics_csv_missing")
    else:
        with metrics_path.open(
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
                errors.append("metrics_csv_header")
                rows = []
            else:
                rows = list(reader)

        if not rows:
            warnings.append("metrics_csv_has_no_samples")
        else:
            for index, row in enumerate(
                rows,
                start=2,
            ):
                profile_class = str(
                    row.get(
                        "profile_class",
                        "",
                    )
                ).strip()
                if (
                    profile_class
                    not in REQUIRED_PROFILES
                ):
                    errors.append(
                        f"invalid_profile_class:{index}"
                    )
                else:
                    classes_in_csv.add(
                        profile_class
                    )

        missing_classes = sorted(
            REQUIRED_PROFILES
            - classes_in_csv
        )
        if missing_classes:
            warnings.append(
                "missing_profile_classes_in_csv:"
                + ",".join(
                    missing_classes
                )
            )

    manifests = Path(manifest_dir)
    profile_ids: set[str] = set()

    if not manifests.is_dir():
        errors.append("manifest_dir_missing")
    else:
        for path in sorted(
            manifests.glob("*.json")
        ):
            try:
                data = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                json.JSONDecodeError,
            ):
                errors.append(
                    f"invalid_manifest_json:{path.name}"
                )
                continue

            if (
                data.get("schema")
                != "EVM-RUN-MANIFEST-001"
            ):
                errors.append(
                    f"manifest_schema:{path.name}"
                )
                continue

            if data.get("mode") != "QUALIFY":
                errors.append(
                    f"manifest_mode:{path.name}"
                )

            if (
                data.get("synthetic_fixture")
                is not False
            ):
                errors.append(
                    f"manifest_synthetic:{path.name}"
                )

            if (
                data.get("truth_status")
                != "VALID"
            ):
                errors.append(
                    f"manifest_truth:{path.name}"
                )

            if (
                data.get(
                    "time_alignment_valid"
                )
                is not True
            ):
                errors.append(
                    f"manifest_time_alignment:{path.name}"
                )

            if (
                data.get("config_locked")
                is not True
            ):
                errors.append(
                    f"manifest_config_lock:{path.name}"
                )

            if (
                data.get("evidence_level")
                != "MEASURED_EVM"
            ):
                errors.append(
                    f"manifest_evidence_level:{path.name}"
                )

            profile_id = str(
                data.get(
                    "profile_id",
                    "",
                )
            ).strip()
            if not profile_id:
                errors.append(
                    f"manifest_profile_id:{path.name}"
                )
            else:
                profile_ids.add(
                    profile_id
                )

    missing_profiles = sorted(
        REQUIRED_PROFILES
        - profile_ids
    )

    if missing_profiles:
        warnings.append(
            "missing_profile_manifests:"
            + ",".join(
                missing_profiles
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
        "errors": sorted(
            set(errors)
        ),
        "warnings": sorted(
            set(warnings)
        ),
        "required_profiles": sorted(
            REQUIRED_PROFILES
        ),
        "manifest_profile_ids": sorted(
            profile_ids
        ),
        "notes": [
            (
                "READY_FOR_COLLECTION means the TRACK/LR profile campaign "
                "is structurally ready to collect measured metrics."
            ),
            (
                "It does not classify any profile as operational or change "
                "waveform/profile parameters."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight an AWR EVM profile "
            "measurement campaign"
        )
    )
    parser.add_argument(
        "--metrics",
        required=True,
    )
    parser.add_argument(
        "--manifest-dir",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = evaluate_preflight(
        metrics_csv=args.metrics,
        manifest_dir=args.manifest_dir,
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
    print(
        result["status"]
    )
    return (
        0
        if result["status"]
        == "READY_FOR_COLLECTION"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
