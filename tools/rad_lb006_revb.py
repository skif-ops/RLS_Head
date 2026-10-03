from __future__ import annotations

import argparse
import csv
import json
import math
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


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_antenna_csv(path: str | Path) -> list[dict[str, str]]:
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


def select_antenna_rows(
    rows: list[dict[str, str]],
    *,
    case_id: str,
    frequency_hz: float,
) -> list[dict]:
    selected: list[dict] = []

    for row in rows:
        if (row["case_id"] or "").strip() != case_id:
            continue

        freq = float(row["frequency_hz"])

        if not math.isfinite(freq) or freq <= 0.0:
            raise ValueError("frequency_hz must be finite and positive")

        if not math.isclose(freq, frequency_hz, rel_tol=0.0, abs_tol=1.0):
            continue

        numeric_fields = (
            "az_deg",
            "el_deg",
            "gain_tx_delta_db",
            "gain_rx_delta_db",
            "sigma_az_deg",
            "sigma_el_deg",
        )

        values = {}

        for field in numeric_fields:
            value = float(row[field])

            if not math.isfinite(value):
                raise ValueError(f"{field} must be finite")

            values[field] = value

        ambiguity = _bool01(row["ambiguity_flag"], "ambiguity_flag")
        track_usable = _bool01(row["track_usable"], "track_usable")
        high_acc_usable = _bool01(row["high_acc_usable"], "high_acc_usable")

        if values["sigma_az_deg"] < 0.0 or values["sigma_el_deg"] < 0.0:
            raise ValueError("angle sigma must be non-negative")

        selected.append(
            {
                "case_id": case_id,
                "frequency_hz": freq,
                **values,
                "ambiguity_flag": ambiguity,
                "track_usable": track_usable,
                "high_acc_usable": high_acc_usable,
                "m_ant_db": (
                    values["gain_tx_delta_db"]
                    + values["gain_rx_delta_db"]
                ),
            }
        )

    if not selected:
        raise ValueError(
            f"no antenna rows for case={case_id!r}, frequency_hz={frequency_hz}"
        )

    return selected


def build_rad_lb006_revb(
    reva: dict,
    antenna_rows: list[dict],
    *,
    case_id: str,
    frequency_hz: float,
) -> dict:
    if reva.get("schema") != "RAD-LB-006-REVA":
        raise ValueError("unexpected Rev.A schema")

    selected = select_antenna_rows(
        antenna_rows,
        case_id=case_id,
        frequency_hz=frequency_hz,
    )

    source_cells = reva.get("cells")

    if not isinstance(source_cells, list) or not source_cells:
        raise ValueError("Rev.A cells missing")

    out_cells = []

    for source in source_cells:
        for antenna in selected:
            margin_empirical = (
                float(source["m_total_empirical_db"])
                + antenna["m_ant_db"]
            )

            margin_r4 = (
                float(source["m_total_r4_db"])
                + antenna["m_ant_db"]
            )

            usable_track = (
                antenna["track_usable"]
                and not antenna["ambiguity_flag"]
            )

            usable_high_acc = (
                usable_track
                and antenna["high_acc_usable"]
            )

            out_cells.append(
                {
                    "range_m": float(source["range_m"]),
                    "rcs_m2": float(source["rcs_m2"]),
                    "az_deg": antenna["az_deg"],
                    "el_deg": antenna["el_deg"],
                    "frequency_hz": antenna["frequency_hz"],
                    "case_id": antenna["case_id"],
                    "m_anchor_db": float(source["m_anchor_db"]),
                    "m_rcs_db": float(source["m_rcs_db"]),
                    "l_range_empirical_db": float(
                        source["l_range_empirical_db"]
                    ),
                    "l_range_r4_db": float(source["l_range_r4_db"]),
                    "m_ant_db": antenna["m_ant_db"],
                    "m_total_empirical_db": margin_empirical,
                    "m_total_r4_db": margin_r4,
                    "sigma_az_deg": antenna["sigma_az_deg"],
                    "sigma_el_deg": antenna["sigma_el_deg"],
                    "ambiguity_flag": antenna["ambiguity_flag"],
                    "track_usable": usable_track,
                    "high_acc_usable": usable_high_acc,
                    "projected_track_empirical": (
                        usable_track and margin_empirical >= 0.0
                    ),
                    "projected_track_r4": (
                        usable_track and margin_r4 >= 0.0
                    ),
                    "evidence_level": "PROJECTED_WITH_SIMULATED_ANTENNA",
                }
            )

    status = "PROJECTED"

    if reva.get("status") != "PROJECTED":
        status = "INPUT_NOT_READY"

    usable_count = sum(1 for row in selected if row["track_usable"] and not row["ambiguity_flag"])

    if usable_count == 0:
        status = "ANTENNA_UNUSABLE"

    return {
        "schema": "RAD-LB-006-REVB",
        "revision": "B",
        "status": status,
        "source_reva_status": reva.get("status"),
        "antenna_selection": {
            "case_id": case_id,
            "frequency_hz": frequency_hz,
            "map_points": len(selected),
            "track_usable_points": usable_count,
        },
        "cells": out_cells,
        "notes": [
            "Rev.B adds simulated antenna gain and angle-usability terms.",
            "No production Tx/Rx physical coordinates are encoded.",
            "Positive projected margin is not a verified field-range PASS.",
            "Measured antenna/range evidence supersedes projected cells.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build RAD-LB-006 Rev.B from Rev.A and antenna map"
    )
    parser.add_argument("--reva", required=True)
    parser.add_argument("--antenna", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--frequency-hz", type=float, required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = build_rad_lb006_revb(
        load_json(args.reva),
        load_antenna_csv(args.antenna),
        case_id=args.case_id,
        frequency_hz=args.frequency_hz,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "PROJECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
