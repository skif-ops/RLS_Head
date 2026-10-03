from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


RCS_GRID_M2 = (0.01, 0.03, 0.10)
RANGE_GRID_M = (300.0, 400.0, 500.0, 600.0)


def rcs_gain_db(rcs_m2: float, reference_rcs_m2: float = 0.01) -> float:
    if rcs_m2 <= 0.0 or reference_rcs_m2 <= 0.0:
        raise ValueError("RCS must be positive")
    return 10.0 * math.log10(rcs_m2 / reference_rcs_m2)


def range_loss_db(
    range_m: float,
    reference_range_m: float,
    exponent_n: float,
) -> float:
    if range_m <= 0.0 or reference_range_m <= 0.0:
        raise ValueError("ranges must be positive")
    if exponent_n <= 0.0 or not math.isfinite(exponent_n):
        raise ValueError("exponent_n must be finite and positive")

    return 10.0 * exponent_n * math.log10(range_m / reference_range_m)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_reference_result(reference: dict) -> float:
    if reference.get("schema") != "REFERENCE-RANGE-RESULT-001":
        raise ValueError("unexpected reference-range schema")

    fit = reference.get("fit")

    if not isinstance(fit, dict):
        raise ValueError("reference-range fit missing")

    n_hat = float(fit["n_hat"])

    if not math.isfinite(n_hat) or n_hat <= 0.0:
        raise ValueError("invalid n_hat")

    return n_hat


def _validate_m300_result(m300: dict) -> float:
    if m300.get("schema") != "M300-REPORT-001":
        raise ValueError("unexpected M300 schema")

    margin = m300.get("m300_track_db")

    if margin is None:
        raise ValueError("M300 track margin missing")

    margin = float(margin)

    if not math.isfinite(margin):
        raise ValueError("invalid M300 track margin")

    return margin


def build_rad_lb006_reva(
    reference: dict,
    m300: dict,
) -> dict:
    n_hat = _validate_reference_result(reference)
    m300_track_db = _validate_m300_result(m300)

    reference_status = str(reference.get("status", "UNKNOWN"))
    track_status = str(m300.get("track_status", "UNKNOWN"))

    status = "PROJECTED"

    reason_codes: list[str] = []

    if reference_status != "DATA_READY":
        status = "INPUT_NOT_READY"
        reason_codes.append("reference_range")

    if track_status != "TRACK_PASS":
        status = "ANCHOR_NOT_VERIFIED"
        reason_codes.append("m300_track")

    cells = []

    for rcs_m2 in RCS_GRID_M2:
        gain_rcs_db = rcs_gain_db(rcs_m2)

        for range_m in RANGE_GRID_M:
            loss_empirical_db = range_loss_db(
                range_m,
                300.0,
                n_hat,
            )

            loss_r4_db = range_loss_db(
                range_m,
                300.0,
                4.0,
            )

            margin_empirical_db = (
                m300_track_db
                + gain_rcs_db
                - loss_empirical_db
            )

            margin_r4_db = (
                m300_track_db
                + gain_rcs_db
                - loss_r4_db
            )

            cells.append(
                {
                    "range_m": range_m,
                    "rcs_m2": rcs_m2,
                    "m_anchor_db": m300_track_db,
                    "m_rcs_db": gain_rcs_db,
                    "l_range_empirical_db": loss_empirical_db,
                    "l_range_r4_db": loss_r4_db,
                    "m_total_empirical_db": margin_empirical_db,
                    "m_total_r4_db": margin_r4_db,
                    "track_possible_empirical": margin_empirical_db >= 0.0,
                    "track_possible_r4": margin_r4_db >= 0.0,
                    "evidence_level": "PROJECTED_FROM_EVM_ANCHOR",
                }
            )

    return {
        "schema": "RAD-LB-006-REVA",
        "revision": "A",
        "status": status,
        "reason_codes": reason_codes,
        "reference_anchor": {
            "range_m": 300.0,
            "rcs_m2": 0.01,
            "track_status": track_status,
            "m300_track_db": m300_track_db,
        },
        "range_model": {
            "n_hat": n_hat,
            "n_theory": 4.0,
            "reference_range_status": reference_status,
            "fit_rms_residual_db": reference.get("fit", {}).get("rms_residual_db"),
            "r4_rms_residual_db": reference.get("r4_rms_residual_db"),
        },
        "cells": cells,
        "notes": [
            "Rev.A contains no custom-antenna correction.",
            "Positive projected margin is not a verified field-range PASS.",
            "Measured results supersede projected cells.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build RAD-LB-006 Rev.A from reference ladder and M300 evidence"
    )
    parser.add_argument("--reference", required=True)
    parser.add_argument("--m300", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = build_rad_lb006_reva(
        load_json(args.reference),
        load_json(args.m300),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "PROJECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
