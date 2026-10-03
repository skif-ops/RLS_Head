from tools.ant_sim_gate import (
    AntSimGateConfig,
    evaluate_ant_sim_gate,
)


def validation(status="DATA_READY"):
    return {
        "schema": "ANT-D1-MAP-VALIDATION-001",
        "status": status,
    }


def mc(status="PASS"):
    return {
        "schema": "ANT-D1-MC-SUMMARY-001",
        "status": status,
    }


def revb(
    *,
    track=True,
    high_acc=True,
    margin=2.0,
):
    return {
        "schema": "RAD-LB-006-REVB",
        "status": "PROJECTED",
        "cells": [
            {
                "range_m": 300.0,
                "rcs_m2": 0.01,
                "az_deg": 0.0,
                "el_deg": 0.0,
                "track_usable": True,
                "high_acc_usable": high_acc,
                "projected_track_empirical": track,
                "m_total_empirical_db": margin,
            },
            {
                "range_m": 300.0,
                "rcs_m2": 0.01,
                "az_deg": 30.0,
                "el_deg": 0.0,
                "track_usable": True,
                "high_acc_usable": False,
                "projected_track_empirical": False,
                "m_total_empirical_db": -1.0,
            },
        ],
    }


def test_gate_pass():
    result = evaluate_ant_sim_gate(
        validation(),
        mc(),
        revb(),
    )

    assert result["schema"] == "ANT-SIM-GATE-001"
    assert result["status"] == "PASS"
    assert result["mandatory_300m"]["projected_track_point_count"] == 1
    assert result["mandatory_300m"]["projected_high_acc_point_count"] == 1


def test_gate_conditional_angle():
    result = evaluate_ant_sim_gate(
        validation(),
        mc(),
        revb(high_acc=False),
    )

    assert result["status"] == "CONDITIONAL"
    assert "angle_high_acc" in result["reason_codes"]


def test_gate_fail_range():
    result = evaluate_ant_sim_gate(
        validation(),
        mc(),
        revb(track=False),
    )

    assert result["status"] == "FAIL"
    assert "mandatory_300m_track" in result["reason_codes"]


def test_gate_hold_on_validation():
    result = evaluate_ant_sim_gate(
        validation("INCOMPLETE"),
        mc(),
        revb(),
    )

    assert result["status"] == "HOLD"
    assert "map_validation_not_ready" in result["reason_codes"]


def test_gate_fail_on_mc_robustness():
    result = evaluate_ant_sim_gate(
        validation(),
        mc("FAIL"),
        revb(),
    )

    assert result["status"] == "FAIL"
    assert "tolerance_robustness" in result["reason_codes"]


def test_gate_can_require_more_track_points():
    result = evaluate_ant_sim_gate(
        validation(),
        mc(),
        revb(),
        AntSimGateConfig(
            min_mandatory_track_points=2,
            min_mandatory_high_acc_points=1,
        ),
    )

    assert result["status"] == "FAIL"
