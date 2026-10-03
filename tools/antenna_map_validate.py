from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "case_id",
    "frequency_hz",
    "az_deg",
    "el_deg",
    "gain_tx_delta_db",
    "gain_rx_delta_db",
    "sigma_az_deg",
    "sigma_el_deg",
    "ambiguity_flag",
    "track_usable",
    "high_acc_usable",
}


@dataclass(frozen=True)
class ValidationConfig:
    required_cases: tuple[str, ...]
    required_frequencies_hz: tuple[float, ...]
    min_points_per_group: int = 1
    require_boresight: bool = True
    boresight_tolerance_deg: float = 1.0e-6


def load_config(path: str | Path) -> ValidationConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    return ValidationConfig(
        required_cases=tuple(str(x) for x in data["required_cases"]),
        required_frequencies_hz=tuple(
            float(x) for x in data["required_frequencies_hz"]
        ),
        min_points_per_group=int(data.get("min_points_per_group", 1)),
        require_boresight=bool(data.get("require_boresight", True)),
        boresight_tolerance_deg=float(
            data.get("boresight_tolerance_deg", 1.0e-6)
        ),
    )


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(
                f"antenna CSV header must include {sorted(REQUIRED_COLUMNS)}"
            )

        rows = list(reader)

    if not rows:
        raise ValueError("antenna CSV is empty")

    return rows


def _bool01(text: str, field: str) -> bool:
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be 0 or 1") from exc

    if value not in (0, 1):
        raise ValueError(f"{field} must be 0 or 1")

    return bool(value)


def _parse_row(row: dict[str, str], index: int) -> dict:
    case_id = (row["case_id"] or "").strip()

    if not case_id:
        raise ValueError(f"row {index}: empty case_id")

    parsed = {
        "case_id": case_id,
    }

    for field in (
        "frequency_hz",
        "az_deg",
        "el_deg",
        "gain_tx_delta_db",
        "gain_rx_delta_db",
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

    if parsed["az_deg"] < -180.0 or parsed["az_deg"] > 180.0:
        raise ValueError(f"row {index}: az_deg outside [-180,180]")

    if parsed["el_deg"] < -90.0 or parsed["el_deg"] > 90.0:
        raise ValueError(f"row {index}: el_deg outside [-90,90]")

    if parsed["sigma_az_deg"] < 0.0 or parsed["sigma_el_deg"] < 0.0:
        raise ValueError(f"row {index}: angle sigma must be non-negative")

    parsed["ambiguity_flag"] = _bool01(
        row["ambiguity_flag"],
        "ambiguity_flag",
    )
    parsed["track_usable"] = _bool01(
        row["track_usable"],
        "track_usable",
    )
    parsed["high_acc_usable"] = _bool01(
        row["high_acc_usable"],
        "high_acc_usable",
    )

    if parsed["ambiguity_flag"] and parsed["track_usable"]:
        raise ValueError(
            f"row {index}: ambiguous point cannot be track_usable"
        )

    if parsed["high_acc_usable"] and not parsed["track_usable"]:
        raise ValueError(
            f"row {index}: high_acc_usable requires track_usable"
        )

    return parsed


def validate_rows(
    rows: list[dict[str, str]],
    config: ValidationConfig,
) -> dict:
    if config.min_points_per_group <= 0:
        raise ValueError("min_points_per_group must be > 0")

    if config.boresight_tolerance_deg < 0.0:
        raise ValueError("boresight_tolerance_deg must be >= 0")

    parsed = [
        _parse_row(row, index)
        for index, row in enumerate(rows, start=2)
    ]

    seen = set()
    duplicates = []

    for row in parsed:
        key = (
            row["case_id"],
            row["frequency_hz"],
            row["az_deg"],
            row["el_deg"],
        )

        if key in seen:
            duplicates.append(key)

        seen.add(key)

    groups: dict[tuple[str, float], list[dict]] = defaultdict(list)

    for row in parsed:
        groups[(row["case_id"], row["frequency_hz"])].append(row)

    missing_groups = []
    underfilled_groups = []
    missing_boresight = []

    for case_id in config.required_cases:
        for frequency_hz in config.required_frequencies_hz:
            matching_key = None

            for key in groups:
                if (
                    key[0] == case_id
                    and math.isclose(
                        key[1],
                        frequency_hz,
                        rel_tol=0.0,
                        abs_tol=1.0,
                    )
                ):
                    matching_key = key
                    break

            if matching_key is None:
                missing_groups.append(
                    {
                        "case_id": case_id,
                        "frequency_hz": frequency_hz,
                    }
                )
                continue

            group = groups[matching_key]

            if len(group) < config.min_points_per_group:
                underfilled_groups.append(
                    {
                        "case_id": case_id,
                        "frequency_hz": frequency_hz,
                        "count": len(group),
                    }
                )

            if config.require_boresight:
                has_boresight = any(
                    abs(row["az_deg"]) <= config.boresight_tolerance_deg
                    and abs(row["el_deg"]) <= config.boresight_tolerance_deg
                    for row in group
                )

                if not has_boresight:
                    missing_boresight.append(
                        {
                            "case_id": case_id,
                            "frequency_hz": frequency_hz,
                        }
                    )

    summaries = []

    for (case_id, frequency_hz), group in sorted(groups.items()):
        combined_gain = [
            row["gain_tx_delta_db"] + row["gain_rx_delta_db"]
            for row in group
        ]

        summaries.append(
            {
                "case_id": case_id,
                "frequency_hz": frequency_hz,
                "point_count": len(group),
                "track_usable_count": sum(
                    1 for row in group if row["track_usable"]
                ),
                "high_acc_usable_count": sum(
                    1 for row in group if row["high_acc_usable"]
                ),
                "ambiguity_count": sum(
                    1 for row in group if row["ambiguity_flag"]
                ),
                "combined_gain_min_db": min(combined_gain),
                "combined_gain_max_db": max(combined_gain),
                "sigma_az_max_deg": max(
                    row["sigma_az_deg"] for row in group
                ),
                "sigma_el_max_deg": max(
                    row["sigma_el_deg"] for row in group
                ),
            }
        )

    reason_codes = []

    if duplicates:
        reason_codes.append("duplicate_points")

    if missing_groups:
        reason_codes.append("missing_groups")

    if underfilled_groups:
        reason_codes.append("underfilled_groups")

    if missing_boresight:
        reason_codes.append("missing_boresight")

    status = "DATA_READY" if not reason_codes else "INCOMPLETE"

    return {
        "schema": "ANT-D1-MAP-VALIDATION-001",
        "status": status,
        "reason_codes": reason_codes,
        "config": asdict(config),
        "row_count": len(parsed),
        "duplicates": [
            {
                "case_id": key[0],
                "frequency_hz": key[1],
                "az_deg": key[2],
                "el_deg": key[3],
            }
            for key in duplicates
        ],
        "missing_groups": missing_groups,
        "underfilled_groups": underfilled_groups,
        "missing_boresight": missing_boresight,
        "groups": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate D1 antenna-map evidence before RAD-LB-006 Rev.B"
    )
    parser.add_argument("csv")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = validate_rows(
        load_csv(args.csv),
        load_config(args.config),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "DATA_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
