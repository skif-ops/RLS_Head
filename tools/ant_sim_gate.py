from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AntSimGateConfig:
    min_mandatory_track_points: int = 1
    min_mandatory_high_acc_points: int = 1


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_ant_sim_gate(
    validation: dict,
    mc_summary: dict,
    revb: dict,
    config: AntSimGateConfig = AntSimGateConfig(),
) -> dict:
    if config.min_mandatory_track_points < 1:
        raise ValueError("min_mandatory_track_points must be >= 1")
    if config.min_mandatory_high_acc_points < 0:
        raise ValueError("min_mandatory_high_acc_points must be >= 0")

    if validation.get("schema") != "ANT-D1-MAP-VALIDATION-001":
        raise ValueError("unexpected validation schema")
    if mc_summary.get("schema") != "ANT-D1-MC-SUMMARY-001":
        raise ValueError("unexpected MC summary schema")
    if revb.get("schema") != "RAD-LB-006-REVB":
        raise ValueError("unexpected Rev.B schema")

    reason_codes: list[str] = []

    if validation.get("status") != "DATA_READY":
        return {
            "schema": "ANT-SIM-GATE-001",
            "status": "HOLD",
            "reason_codes": ["map_validation_not_ready"],
            "config": asdict(config),
        }

    if mc_summary.get("status") == "INCOMPLETE":
        return {
            "schema": "ANT-SIM-GATE-001",
            "status": "HOLD",
            "reason_codes": ["mc_incomplete"],
            "config": asdict(config),
        }

    if mc_summary.get("status") == "FAIL":
        return {
            "schema": "ANT-SIM-GATE-001",
            "status": "FAIL",
            "reason_codes": ["tolerance_robustness"],
            "config": asdict(config),
        }

    if revb.get("status") != "PROJECTED":
        return {
            "schema": "ANT-SIM-GATE-001",
            "status": "HOLD",
            "reason_codes": ["revb_not_ready"],
            "config": asdict(config),
        }

    mandatory_cells = [
        cell for cell in revb.get("cells", [])
        if float(cell.get("range_m", -1.0)) == 300.0
        and float(cell.get("rcs_m2", -1.0)) == 0.01
    ]

    if not mandatory_cells:
        return {
            "schema": "ANT-SIM-GATE-001",
            "status": "HOLD",
            "reason_codes": ["mandatory_cell_missing"],
            "config": asdict(config),
        }

    projected_track_cells = [
        cell for cell in mandatory_cells
        if bool(cell.get("projected_track_empirical"))
    ]

    projected_high_acc_cells = [
        cell for cell in projected_track_cells
        if bool(cell.get("high_acc_usable"))
    ]

    if len(projected_track_cells) < config.min_mandatory_track_points:
        status = "FAIL"
        reason_codes.append("mandatory_300m_track")

    elif len(projected_high_acc_cells) < config.min_mandatory_high_acc_points:
        status = "CONDITIONAL"
        reason_codes.append("angle_high_acc")

    else:
        status = "PASS"

    margins = [
        float(cell["m_total_empirical_db"])
        for cell in mandatory_cells
        if cell.get("track_usable")
    ]

    return {
        "schema": "ANT-SIM-GATE-001",
        "status": status,
        "reason_codes": reason_codes,
        "config": asdict(config),
        "mandatory_300m": {
            "map_point_count": len(mandatory_cells),
            "projected_track_point_count": len(projected_track_cells),
            "projected_high_acc_point_count": len(projected_high_acc_cells),
            "max_projected_margin_db": max(margins) if margins else None,
            "min_projected_margin_db": min(margins) if margins else None,
        },
        "input_status": {
            "map_validation": validation.get("status"),
            "mc_summary": mc_summary.get("status"),
            "rad_lb_revb": revb.get("status"),
        },
        "open_evidence": [
            "physical antenna measurement",
            "measured FOV correlation",
            "field range verification",
        ],
        "notes": [
            "PASS is simulation-gate PASS, not physical antenna validation.",
            "TRACK and HIGH_ACC remain separate.",
            "No production Tx/Rx geometry is encoded by this gate.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate combined ANT-SIM-GATE-001"
    )
    parser.add_argument("--validation", required=True)
    parser.add_argument("--mc", required=True)
    parser.add_argument("--revb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-track-points", type=int, default=1)
    parser.add_argument("--min-high-acc-points", type=int, default=1)

    args = parser.parse_args()

    result = evaluate_ant_sim_gate(
        load_json(args.validation),
        load_json(args.mc),
        load_json(args.revb),
        AntSimGateConfig(
            min_mandatory_track_points=args.min_track_points,
            min_mandatory_high_acc_points=args.min_high_acc_points,
        ),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
