import json

from tools.external_job_pack import (
    build_job_pack,
    validate_job_pack,
)


def queue_fixture():
    return {
        "schema": "EXTERNAL-EXECUTION-QUEUE-001",
        "status": "READY",
        "queue": [
            {
                "item_id": "M300_MEASURED",
                "next_action": "COLLECT_EVM_M300",
                "measurement_pack_kind": "m300",
                "requires_measured_evidence": True,
                "directly_unlocks": 2,
            },
            {
                "item_id": "HIL_R2_BENCH_MEASURED",
                "next_action": "COLLECT_HIL_R2_BENCH",
                "measurement_pack_kind": "hil_r2_bench",
                "requires_measured_evidence": True,
                "directly_unlocks": 1,
            },
            {
                "item_id": "ANT_D1_EM_REAL",
                "next_action": "RUN_D1_EM_SOLVER",
                "measurement_pack_kind": None,
                "requires_measured_evidence": False,
                "directly_unlocks": 1,
            },
            {
                "item_id": "REFERENCE_RANGE_MEASURED",
                "next_action": "COLLECT_EVM_REFERENCE_LADDER",
                "measurement_pack_kind": "reference_range",
                "requires_measured_evidence": True,
                "directly_unlocks": 0,
            },
            {
                "item_id": "CARRIER_REVIEW_A",
                "next_action": "CAPTURE_KICAD_AND_RUN_REVIEW_A",
                "measurement_pack_kind": None,
                "requires_measured_evidence": False,
                "directly_unlocks": 0,
            },
            {
                "item_id": "AWR_EVM_PROFILE_MEASURED",
                "next_action": "COLLECT_EVM_PROFILE_MATRIX",
                "measurement_pack_kind": "evm_profile",
                "requires_measured_evidence": True,
                "directly_unlocks": 0,
            },
            {
                "item_id": "SYS_ERR_MEASURED",
                "next_action": "ASSEMBLE_MEASURED_SYS_ERR",
                "measurement_pack_kind": "sys_err",
                "requires_measured_evidence": True,
                "directly_unlocks": 1,
            },
            {
                "item_id": "PHYSICAL_ANT_MEASUREMENT",
                "next_action": "MEASURE_PHYSICAL_ANTENNA",
                "measurement_pack_kind": "physical_antenna",
                "requires_measured_evidence": True,
                "directly_unlocks": 0,
            },
            {
                "item_id": "ANT_D1_SIM_GATE_REAL",
                "next_action": "ASSEMBLE_REAL_ANT_SIM_GATE",
                "measurement_pack_kind": None,
                "requires_measured_evidence": False,
                "directly_unlocks": 1,
            },
        ],
    }


def test_priority_one_m300_template_is_blocked_until_filled(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=1,
    )

    assert manifest["item_id"] == "M300_MEASURED"
    assert manifest["pack_kind"] == "m300"
    assert (
        manifest["preflight"]["schema"]
        == "M300-JOB-PACK-PREFLIGHT-001"
    )

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "BLOCKED"
    assert result["preflight_errors"]


def test_filled_m300_pack_reaches_ready_for_collection(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=1,
    )

    run_path = (
        tmp_path
        / "measurement_pack"
        / "run_manifest.json"
    )
    run = json.loads(
        run_path.read_text(encoding="utf-8")
    )
    run.update(
        {
            "run_id": "EVM-M300-001",
            "profile_id": "TRACK",
            "profile_config_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "target_id": "RCS-0P01",
            "start_time_us": 1000000,
            "end_time_us": 2000000,
            "truth_status": "VALID",
            "time_alignment_valid": True,
            "config_locked": True,
            "evidence_level": "MEASURED_EVM",
            "synthetic_fixture": False,
            "environment": {
                "temperature_c": 20.0,
                "precipitation_state": "NONE",
            },
            "files": [],
        }
    )
    run_path.write_text(
        json.dumps(run) + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert result["preflight_errors"] == []


def test_priority_two_selects_hil_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )

    assert manifest["item_id"] == "HIL_R2_BENCH_MEASURED"
    assert manifest["pack_kind"] == "hil_r2_bench"
    assert (
        manifest["preflight"]["schema"]
        == "HIL-R2-JOB-PACK-PREFLIGHT-001"
    )
    assert (tmp_path / "hil_r2_gate_config.json").is_file()
    assert (tmp_path / "preflight_config.json").is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert (
        "timing_csv_has_no_samples"
        in result["preflight_warnings"]
    )


def test_hil_gate_config_is_self_contained(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=2,
    )

    gate = json.loads(
        (
            tmp_path
            / "hil_r2_gate_config.json"
        ).read_text(encoding="utf-8")
    )

    assert gate["min_radar_imu_samples"] == 100
    assert gate["min_pps_samples"] == 30
    assert gate["max_missed_events"] == 0


def test_priority_three_selects_reference_range_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=4,
    )

    assert manifest["item_id"] == "REFERENCE_RANGE_MEASURED"
    assert manifest["pack_kind"] == "reference_range"
    assert (
        manifest["preflight"]["schema"]
        == "REFERENCE-RANGE-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "README.txt"
    ).is_file()
    assert (tmp_path / "preflight_config.json").is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert (
        "reference_csv_has_no_samples"
        in result["preflight_warnings"]
    )
    assert any(
        warning.startswith(
            "missing_range_manifests:"
        )
        for warning
        in result["preflight_warnings"]
    )


def test_reference_range_invalid_manifest_blocks_preflight(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=4,
    )

    bad = (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "bad.json"
    )
    bad.write_text(
        "{bad",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "BLOCKED"
    assert (
        "invalid_manifest_json:bad.json"
        in result["preflight_errors"]
    )


def test_reference_required_ranges_are_embedded(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=4,
    )

    assert manifest["preflight"]["required_ranges_m"] == [
        50,
        100,
        150,
        200,
        250,
        300,
    ]


def test_priority_three_selects_d1_em_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    assert manifest["item_id"] == "ANT_D1_EM_REAL"
    assert manifest["pack_kind"] is None
    assert (
        manifest["preflight"]["schema"]
        == "ANT-D1-EM-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "em_package"
        / "d1_em_manifest.json"
    ).is_file()
    assert (
        tmp_path
        / "d1_map_validation_config.json"
    ).is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "BLOCKED"
    assert result["preflight_errors"]


def test_d1_em_inputs_can_reach_solver_ready(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    model_dir = tmp_path / "em_package" / "model"
    (model_dir / "model_input.dat").write_text(
        "model\n",
        encoding="utf-8",
    )
    (model_dir / "material_definition.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    manifest_path = (
        tmp_path
        / "em_package"
        / "d1_em_manifest.json"
    )
    em = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    em.update(
        {
            "model_id": "D1",
            "model_revision": "A",
            "solver_name": "EM_SOLVER",
            "solver_version": "1.0",
        }
    )
    manifest_path.write_text(
        json.dumps(em) + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)
    assert (
        result["preflight_status"]
        == "READY_FOR_SOLVER_EXECUTION"
    )
    assert result["preflight_errors"] == []
    assert any(
        warning.startswith(
            "solver_export:output_not_present_yet"
        )
        for warning in result["preflight_warnings"]
    )


def test_d1_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=3,
    )

    assert (
        "<MAP_CONFIG>"
        not in manifest["validator_command"]
    )
    assert (
        "--map-config d1_map_validation_config.json"
        in manifest["validator_command"]
    )


def test_priority_five_selects_carrier_review_a_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=5,
    )

    assert manifest["item_id"] == "CARRIER_REVIEW_A"
    assert manifest["pack_kind"] is None
    assert (
        manifest["preflight"]["schema"]
        == "CARRIER-REVIEW-A-JOB-PACK-PREFLIGHT-001"
    )

    pinmap = (
        tmp_path
        / "carrier_package"
        / "inputs"
        / "pinmap.csv"
    )
    bom = (
        tmp_path
        / "carrier_package"
        / "inputs"
        / "bom.csv"
    )

    assert pinmap.is_file()
    assert bom.is_file()

    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert (
        result["preflight_status"]
        == "READY_FOR_CAD_REVIEW_EXECUTION"
    )
    assert "schematic:not_present_yet" in result["preflight_warnings"]
    assert "erc_json:not_present_yet" in result["preflight_warnings"]


def test_carrier_job_pack_uses_authoritative_timing_pinmap(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=5,
    )

    pinmap = (
        tmp_path
        / "carrier_package"
        / "inputs"
        / "pinmap.csv"
    ).read_text(encoding="utf-8")

    assert "GNSS_PPS,PA0" in pinmap
    assert "RADAR_REF,PB10" in pinmap
    assert "IMU_DRDY,PB11" in pinmap


def test_carrier_bad_pinmap_blocks_preflight(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=5,
    )

    pinmap = (
        tmp_path
        / "carrier_package"
        / "inputs"
        / "pinmap.csv"
    )
    pinmap.write_text(
        "signal,mcu_pin,peripheral,direction,criticality\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "BLOCKED"
    assert "pinmap_not_ready" in result["preflight_errors"]


def test_carrier_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=5,
    )

    assert (
        "carrier_package/carrier_review_a_manifest.json"
        in manifest["validator_command"]
    )
    assert "<" not in manifest["validator_command"]


def test_priority_six_selects_evm_profile_with_preflight(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=6,
    )

    assert manifest["item_id"] == "AWR_EVM_PROFILE_MEASURED"
    assert manifest["pack_kind"] == "evm_profile"
    assert (
        manifest["preflight"]["schema"]
        == "EVM-PROFILE-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "README.txt"
    ).is_file()
    assert (
        tmp_path
        / "evm_profile_gate_config.json"
    ).is_file()

    result = validate_job_pack(tmp_path)
    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert "metrics_csv_has_no_samples" in result["preflight_warnings"]
    assert any(
        warning.startswith("missing_profile_manifests:")
        for warning in result["preflight_warnings"]
    )


def test_evm_profile_bad_manifest_blocks_preflight(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=6,
    )

    bad = (
        tmp_path
        / "measurement_pack"
        / "run_manifests"
        / "TRACK.json"
    )
    bad.write_text("{bad", encoding="utf-8")

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "BLOCKED"
    assert "invalid_manifest_json:TRACK.json" in result["preflight_errors"]


def test_evm_profile_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=6,
    )

    command = manifest["validator_command"]

    assert "<" not in command
    assert "--metrics measurement_pack/profile_metrics.csv" in command
    assert "--config evm_profile_gate_config.json" in command
    for profile in ("TRACK", "LR1", "LR2", "LRX"):
        assert (
            f"--manifest measurement_pack/run_manifests/{profile}.json"
            in command
        )


def test_evm_profile_gate_config_is_copied(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=6,
    )

    config = json.loads(
        (
            tmp_path
            / "evm_profile_gate_config.json"
        ).read_text(encoding="utf-8")
    )

    assert config["pd_min"] == 0.90
    assert config["track_availability_min"] == 0.95
    assert config["update_min_hz"] == 20.0


def test_priority_seven_selects_sys_err_waiting_for_hil(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=7,
    )

    assert manifest["item_id"] == "SYS_ERR_MEASURED"
    assert manifest["pack_kind"] == "sys_err"
    assert (
        manifest["preflight"]["schema"]
        == "SYS-ERR-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "sys_err_gate_config.json"
    ).is_file()
    assert (
        tmp_path
        / "measurement_pack"
        / "timing"
        / "README.txt"
    ).is_file()

    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "WAITING_FOR_HIL_R2"
    assert result["preflight_errors"] == []
    assert "timing:not_present_yet" in result["preflight_warnings"]


def test_sys_err_hil_pass_reaches_ready_for_collection(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=7,
    )

    timing_path = (
        tmp_path
        / "measurement_pack"
        / "timing"
        / "hil_r2_evidence.json"
    )
    timing_path.write_text(
        json.dumps(
            {
                "schema": "HIL-R2-BENCH-EVIDENCE-001",
                "gate_status": "PASS",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert result["preflight_errors"] == []
    assert "cells:no_samples_yet" in result["preflight_warnings"]


def test_sys_err_manifest_paths_are_job_pack_relative(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=7,
    )

    manifest_path = (
        tmp_path
        / "measurement_pack"
        / "sys_err_manifest.json"
    )
    data = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    assert (
        data["timing_evidence"]["path"]
        == "measurement_pack/timing/hil_r2_evidence.json"
    )
    assert (
        data["cells_csv"]["path"]
        == "measurement_pack/sys_err_cells.csv"
    )


def test_sys_err_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=7,
    )

    command = manifest["validator_command"]

    assert "<" not in command
    assert (
        "--manifest measurement_pack/sys_err_manifest.json"
        in command
    )
    assert (
        "--config sys_err_gate_config.json"
        in command
    )


def test_priority_eight_selects_physical_antenna_blocked_template(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=8,
    )

    assert manifest["item_id"] == "PHYSICAL_ANT_MEASUREMENT"
    assert manifest["pack_kind"] == "physical_antenna"
    assert (
        manifest["preflight"]["schema"]
        == "PHYSICAL-ANTENNA-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "physical_antenna_measurement_config.json"
    ).is_file()

    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "BLOCKED"
    assert result["preflight_errors"]


def test_filled_physical_antenna_ids_reach_ready_for_collection(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=8,
    )

    manifest_path = (
        tmp_path
        / "measurement_pack"
        / "antenna_measurement_manifest.json"
    )
    data = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    data.update(
        {
            "measurement_id": "ANT-MEAS-001",
            "instrument_id": "INSTRUMENT-001",
            "calibration_id": "CAL-001",
        }
    )
    manifest_path.write_text(
        json.dumps(data) + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "READY_FOR_COLLECTION"
    assert result["preflight_errors"] == []
    assert "measurement_csv:no_samples_yet" in result["preflight_warnings"]


def test_physical_antenna_manifest_path_is_job_pack_relative(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=8,
    )

    data = json.loads(
        (
            tmp_path
            / "measurement_pack"
            / "antenna_measurement_manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert (
        data["measurement_csv"]["path"]
        == "measurement_pack/antenna_measurement.csv"
    )


def test_physical_antenna_config_is_copied(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=8,
    )

    config = json.loads(
        (
            tmp_path
            / "physical_antenna_measurement_config.json"
        ).read_text(encoding="utf-8")
    )

    assert config["required_frequencies_hz"] == [
        76000000000,
        78500000000,
        81000000000,
    ]
    assert config["min_repeat_count"] == 3
    assert config["max_gain_uncertainty_db"] == 1.0


def test_physical_antenna_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=8,
    )

    command = manifest["validator_command"]

    assert "<" not in command
    assert (
        "--manifest measurement_pack/antenna_measurement_manifest.json"
        in command
    )
    assert (
        "--config physical_antenna_measurement_config.json"
        in command
    )


def test_priority_nine_selects_ant_sim_waiting_for_upstream(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=9,
    )

    assert manifest["item_id"] == "ANT_D1_SIM_GATE_REAL"
    assert manifest["pack_kind"] is None
    assert (
        manifest["preflight"]["schema"]
        == "ANT-SIM-REAL-JOB-PACK-PREFLIGHT-001"
    )
    assert (
        tmp_path
        / "ant_sim_inputs"
        / "README.txt"
    ).is_file()

    result = validate_job_pack(tmp_path)

    assert result["status"] == "TEMPLATE_READY"
    assert result["preflight_status"] == "WAITING_FOR_UPSTREAM"
    assert result["preflight_errors"] == []
    assert any(
        warning.startswith("map_validation:not_present_yet")
        for warning in result["preflight_warnings"]
    )


def test_ant_sim_ready_inputs_reach_gate_assembly(tmp_path):
    build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=9,
    )

    inputs = (
        tmp_path
        / "ant_sim_inputs"
    )

    (
        inputs
        / "map_validation.json"
    ).write_text(
        json.dumps(
            {
                "schema": "ANT-D1-MAP-VALIDATION-001",
                "status": "DATA_READY",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (
        inputs
        / "mc_summary.json"
    ).write_text(
        json.dumps(
            {
                "schema": "ANT-D1-MC-SUMMARY-001",
                "status": "PASS",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (
        inputs
        / "rad_lb_revb.json"
    ).write_text(
        json.dumps(
            {
                "schema": "RAD-LB-006-REVB",
                "status": "PROJECTED",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_job_pack(tmp_path)

    assert result["preflight_status"] == "READY_FOR_GATE_ASSEMBLY"
    assert result["preflight_errors"] == []


def test_ant_sim_validator_command_is_self_contained(tmp_path):
    manifest = build_job_pack(
        queue_fixture(),
        tmp_path,
        priority=9,
    )

    command = manifest["validator_command"]

    assert "<" not in command
    assert "--validation ant_sim_inputs/map_validation.json" in command
    assert "--mc ant_sim_inputs/mc_summary.json" in command
    assert "--revb ant_sim_inputs/rad_lb_revb.json" in command


def test_invalid_priority_rejected(tmp_path):
    try:
        build_job_pack(
            queue_fixture(),
            tmp_path,
            priority=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "ValueError expected"
        )


def test_missing_manifest_is_invalid(tmp_path):
    result = validate_job_pack(tmp_path)
    assert result["status"] == "INVALID"
    assert (
        "missing_job_manifest"
        in result["errors"]
    )
