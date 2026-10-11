from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "HIL-R2-EXTERNAL-PREFLIGHT-001"


def evaluate_preflight(
    *,
    timing_csv: str | Path,
    gate_config: dict,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    required_cfg = {
        "min_radar_imu_samples",
        "min_pps_samples",
        "radar_imu_max_abs_us",
        "radar_imu_rms_us",
        "pps_max_abs_us",
        "pps_rms_us",
        "holdover_max_abs_us",
        "max_missed_events",
        "max_monotonic_failures",
    }

    missing_cfg = sorted(
        required_cfg - set(gate_config)
    )
    errors.extend(
        f"missing_config:{name}"
        for name in missing_cfg
    )

    csv_path = Path(timing_csv)
    row_count = 0
    kinds: set[str] = set()

    if not csv_path.is_file():
        errors.append("timing_csv_missing")
    else:
        try:
            with csv_path.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)
                required = {"kind", "value_us", "count"}

                if (
                    reader.fieldnames is None
                    or not required.issubset(
                        reader.fieldnames
                    )
                ):
                    errors.append(
                        "timing_csv_header"
                    )
                else:
                    for line_no, row in enumerate(
                        reader,
                        start=2,
                    ):
                        row_count += 1
                        kind = (
                            row.get("kind") or ""
                        ).strip()
                        if not kind:
                            errors.append(
                                f"missing_kind:{line_no}"
                            )
                            continue

                        kinds.add(kind)

                        if kind in {
                            "radar_imu",
                            "pps",
                            "holdover",
                        }:
                            value = (
                                row.get("value_us")
                                or ""
                            ).strip()
                            if not value:
                                errors.append(
                                    f"missing_value_us:{line_no}"
                                )
                            else:
                                try:
                                    float(value)
                                except ValueError:
                                    errors.append(
                                        f"invalid_value_us:{line_no}"
                                    )
                        else:
                            count = (
                                row.get("count")
                                or "1"
                            ).strip()
                            try:
                                parsed = int(count)
                                if parsed < 0:
                                    raise ValueError
                            except ValueError:
                                errors.append(
                                    f"invalid_count:{line_no}"
                                )

        except OSError:
            errors.append("timing_csv_read")

    if row_count == 0:
        warnings.append("timing_csv_has_no_samples")

    if row_count > 0:
        if "radar_imu" not in kinds:
            warnings.append(
                "no_radar_imu_samples_yet"
            )
        if "pps" not in kinds:
            warnings.append(
                "no_pps_samples_yet"
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
        "checks": {
            "timing_csv_structure": True,
            "gate_config_complete": not missing_cfg,
            "required_columns": [
                "kind",
                "value_us",
                "count",
            ],
        },
        "notes": [
            (
                "READY_FOR_COLLECTION means the HIL-R2 bench job is "
                "structurally ready to collect timing evidence."
            ),
            (
                "It does not mean the HIL-R2 gate passed; sample-count "
                "and residual thresholds are evaluated after collection."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a HIL-R2 external bench measurement job"
    )
    parser.add_argument(
        "--timing-csv",
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

    config = json.loads(
        Path(args.config).read_text(
            encoding="utf-8"
        )
    )

    result = evaluate_preflight(
        timing_csv=args.timing_csv,
        gate_config=config,
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
    return (
        0
        if result["status"]
        == "READY_FOR_COLLECTION"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
