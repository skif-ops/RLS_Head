from __future__ import annotations

import argparse
import json
from pathlib import Path


MEASURED_LEVELS = {
    "MEASURED_EVM",
    "MEASURED_BENCH",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_hw_sensor_prototype_gate(
    *,
    m300: dict,
    ant_sim_gate: dict,
    sys_err_gate: dict,
) -> dict:
    if m300.get("schema") != "M300-REPORT-001":
        raise ValueError("unexpected M300 schema")
    if ant_sim_gate.get("schema") != "ANT-SIM-GATE-001":
        raise ValueError("unexpected ANT-SIM schema")
    if sys_err_gate.get("schema") != "SYS-ERR-GATE-001":
        raise ValueError("unexpected SYS-ERR schema")

    reason_codes: list[str] = []

    m300_track_status = str(m300.get("track_status", "UNKNOWN"))
    m300_evidence_level = str(m300.get("evidence_level", "UNSPECIFIED"))
    ant_status = str(ant_sim_gate.get("status", "UNKNOWN"))
    sys_err_status = str(sys_err_gate.get("status", "UNKNOWN"))
    sys_err_evidence_level = str(
        sys_err_gate.get("evidence_level", "UNSPECIFIED")
    )

    if m300_evidence_level not in MEASURED_LEVELS:
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "HOLD",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["m300_not_measured"],
            "input_status": {
                "m300_track_status": m300_track_status,
                "m300_evidence_level": m300_evidence_level,
                "ant_sim_gate": ant_status,
                "sys_err_gate": sys_err_status,
                "sys_err_evidence_level": sys_err_evidence_level,
            },
        }

    if m300_track_status != "TRACK_PASS":
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "FAIL",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["mandatory_300m_track_not_passed"],
            "input_status": {
                "m300_track_status": m300_track_status,
                "m300_evidence_level": m300_evidence_level,
                "ant_sim_gate": ant_status,
                "sys_err_gate": sys_err_status,
                "sys_err_evidence_level": sys_err_evidence_level,
            },
        }

    if ant_status == "HOLD":
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "HOLD",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["ant_sim_hold"],
        }

    if ant_status == "FAIL":
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "FAIL",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["ant_sim_fail"],
        }

    if sys_err_evidence_level not in MEASURED_LEVELS:
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "HOLD",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["sys_err_not_measured"],
        }

    if sys_err_status == "HOLD":
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "HOLD",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["sys_err_hold"],
        }

    if sys_err_status == "FAIL":
        return {
            "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
            "status": "FAIL",
            "prototype_authorization": "NOT_AUTHORIZED",
            "reason_codes": ["sys_err_fail"],
        }

    conditional = False

    if ant_status == "CONDITIONAL":
        conditional = True
        reason_codes.append("ant_sim_conditional")

    if sys_err_status == "CONDITIONAL":
        conditional = True
        reason_codes.append("sys_err_conditional")

    if conditional:
        status = "CONDITIONAL"
        authorization = "CONDITIONAL_MEASUREMENT_PROTOTYPE"
    else:
        status = "PASS"
        authorization = "AUTHORIZED_FOR_MEASUREMENT"

    return {
        "schema": "HW-SENSOR-PROTOTYPE-GATE-001",
        "status": status,
        "prototype_authorization": authorization,
        "reason_codes": reason_codes,
        "input_status": {
            "m300_track_status": m300_track_status,
            "m300_evidence_level": m300_evidence_level,
            "ant_sim_gate": ant_status,
            "sys_err_gate": sys_err_status,
            "sys_err_evidence_level": sys_err_evidence_level,
        },
        "prototype_scope": [
            "realized gain measurement",
            "radiation/FOV pattern measurement",
            "channel gain/phase characterization",
            "angle bias/variance measurement",
            "simulation correlation",
        ],
        "explicitly_not_authorized": [
            "production antenna freeze",
            "integrated radar PCB production",
            "production waveform freeze",
        ],
        "notes": [
            "This gate authorizes only a measurement prototype.",
            "Synthetic/CI evidence cannot authorize hardware.",
            "Integrated radar PCB remains behind a separate gate.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate HW-SENSOR-PROTOTYPE-GATE-001"
    )
    parser.add_argument("--m300", required=True)
    parser.add_argument("--ant-sim", required=True)
    parser.add_argument("--sys-err", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = evaluate_hw_sensor_prototype_gate(
        m300=load_json(args.m300),
        ant_sim_gate=load_json(args.ant_sim),
        sys_err_gate=load_json(args.sys_err),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {"PASS", "CONDITIONAL", "HOLD"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
