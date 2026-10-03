import copy

from tools.integrated_radar_gate import (
    evaluate_integrated_radar_gate,
)


def manifest_with(
    awr="PASS",
    ant="PASS",
    syserr="PASS",
):
    return {
        "schema": "PROJECT-EVIDENCE-MANIFEST-001",
        "items": [
            {
                "id": "AWR_EVM_PROFILE_MEASURED",
                "status": awr,
                "evidence_level": "MEASURED_EVM",
                "synthetic": False,
            },
            {
                "id": "PHYSICAL_ANT_MEASUREMENT",
                "status": ant,
                "evidence_level": "MEASURED_EM",
                "synthetic": False,
            },
            {
                "id": "SYS_ERR_MEASURED",
                "status": syserr,
                "evidence_level": "MEASURED_BENCH",
                "synthetic": False,
            },
        ],
        "milestones": {},
    }


def test_all_pass_authorizes_integrated_measurement_prototype():
    result = evaluate_integrated_radar_gate(
        manifest_with()
    )

    assert result["status"] == "PASS"
    assert (
        result["prototype_authorization"]
        == "AUTHORIZED_FOR_INTEGRATED_MEASUREMENT_PROTOTYPE"
    )
    assert "production release" in result["explicitly_not_authorized"]


def test_open_input_holds():
    result = evaluate_integrated_radar_gate(
        manifest_with(awr="OPEN")
    )

    assert result["status"] == "HOLD"
    assert result["prototype_authorization"] == "NOT_AUTHORIZED"
    assert "not_ready:AWR_EVM_PROFILE_MEASURED" in result["reason_codes"]


def test_conditional_input_is_conditional():
    result = evaluate_integrated_radar_gate(
        manifest_with(ant="CONDITIONAL")
    )

    assert result["status"] == "CONDITIONAL"
    assert (
        result["prototype_authorization"]
        == "CONDITIONAL_INTEGRATED_MEASUREMENT_PROTOTYPE"
    )
    assert "conditional:PHYSICAL_ANT_MEASUREMENT" in result["reason_codes"]


def test_failed_input_fails():
    result = evaluate_integrated_radar_gate(
        manifest_with(syserr="FAIL")
    )

    assert result["status"] == "FAIL"
    assert "failed:SYS_ERR_MEASURED" in result["reason_codes"]


def test_synthetic_input_invalid():
    manifest = manifest_with()
    manifest["items"][1]["synthetic"] = True

    result = evaluate_integrated_radar_gate(
        manifest
    )

    assert result["status"] == "INVALID"
    assert "synthetic:PHYSICAL_ANT_MEASUREMENT" in result["reason_codes"]


def test_missing_item_invalid():
    manifest = manifest_with()
    manifest["items"] = manifest["items"][:-1]

    result = evaluate_integrated_radar_gate(
        manifest
    )

    assert result["status"] == "INVALID"
    assert "missing_item:SYS_ERR_MEASURED" in result["reason_codes"]
