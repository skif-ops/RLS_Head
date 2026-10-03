from tools.hw_sensor_prototype_gate import (
    evaluate_hw_sensor_prototype_gate,
)


def m300(
    track_status="TRACK_PASS",
    evidence_level="MEASURED_EVM",
):
    return {
        "schema": "M300-REPORT-001",
        "track_status": track_status,
        "evidence_level": evidence_level,
        "m300_track_db": 2.0,
    }


def ant(status="PASS"):
    return {
        "schema": "ANT-SIM-GATE-001",
        "status": status,
    }


def syserr(
    status="PASS",
    evidence_level="MEASURED_BENCH",
):
    return {
        "schema": "SYS-ERR-GATE-001",
        "status": status,
        "evidence_level": evidence_level,
    }


def test_gate_pass_authorizes_measurement_prototype():
    result = evaluate_hw_sensor_prototype_gate(
        m300=m300(),
        ant_sim_gate=ant(),
        sys_err_gate=syserr(),
    )

    assert result["status"] == "PASS"
    assert result["prototype_authorization"] == "AUTHORIZED_FOR_MEASUREMENT"
    assert "integrated radar PCB production" in result["explicitly_not_authorized"]


def test_synthetic_m300_cannot_authorize_hardware():
    result = evaluate_hw_sensor_prototype_gate(
        m300=m300(evidence_level="SIMULATED"),
        ant_sim_gate=ant(),
        sys_err_gate=syserr(),
    )

    assert result["status"] == "HOLD"
    assert result["prototype_authorization"] == "NOT_AUTHORIZED"
    assert "m300_not_measured" in result["reason_codes"]


def test_m300_track_fail_blocks_prototype():
    result = evaluate_hw_sensor_prototype_gate(
        m300=m300(track_status="DETECT_ONLY"),
        ant_sim_gate=ant(),
        sys_err_gate=syserr(),
    )

    assert result["status"] == "FAIL"
    assert "mandatory_300m_track_not_passed" in result["reason_codes"]


def test_conditional_inputs_remain_conditional():
    result = evaluate_hw_sensor_prototype_gate(
        m300=m300(),
        ant_sim_gate=ant("CONDITIONAL"),
        sys_err_gate=syserr("CONDITIONAL"),
    )

    assert result["status"] == "CONDITIONAL"
    assert result["prototype_authorization"] == "CONDITIONAL_MEASUREMENT_PROTOTYPE"
    assert "ant_sim_conditional" in result["reason_codes"]
    assert "sys_err_conditional" in result["reason_codes"]


def test_unmeasured_syserr_holds():
    result = evaluate_hw_sensor_prototype_gate(
        m300=m300(),
        ant_sim_gate=ant(),
        sys_err_gate=syserr(evidence_level="CALCULATED"),
    )

    assert result["status"] == "HOLD"
    assert "sys_err_not_measured" in result["reason_codes"]
