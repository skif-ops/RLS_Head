import json
from pathlib import Path

from tools.sys_err_external_preflight import (
    evaluate_preflight,
)


HEADER = (
    "cell_id,range_m,sigma_range_m,"
    "sigma_az_deg,sigma_el_deg,"
    "host_attitude_sigma_deg,"
    "extrinsic_sigma_deg,"
    "angular_rate_deg_s\n"
)


def config():
    return {
        "mandatory_range_m":
            300.0,
        "mandatory_max_position_rms_m":
            2.10,
        "max_timestamp_rms_us":
            200.0,
        "max_timestamp_abs_us":
            250.0,
        "min_cells": 3,
    }


def manifest():
    return {
        "schema":
            "SYS-ERR-MEASUREMENT-MANIFEST-001",
        "synthetic_fixture":
            False,
        "evidence_level":
            "MEASURED_BENCH",
        "timing_evidence": {
            "path":
                "timing/hil_r2.json",
            "sha256":
                "<FILL_SHA256>",
        },
        "cells_csv": {
            "path":
                "sys_err_cells.csv",
            "sha256":
                "<FILL_SHA256>",
        },
    }


def write_cells(
    root: Path,
):
    (
        root
        / "sys_err_cells.csv"
    ).write_text(
        HEADER,
        encoding="utf-8",
    )


def test_waits_for_hil_when_timing_missing(
    tmp_path,
):
    write_cells(
        tmp_path
    )
    (
        tmp_path
        / "timing"
    ).mkdir()

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert (
        result["status"]
        == "WAITING_FOR_HIL_R2"
    )
    assert (
        "timing:not_present_yet"
        in result["warnings"]
    )


def test_hil_pass_unblocks_collection(
    tmp_path,
):
    write_cells(
        tmp_path
    )
    timing_dir = (
        tmp_path
        / "timing"
    )
    timing_dir.mkdir()
    (
        timing_dir
        / "hil_r2.json"
    ).write_text(
        json.dumps(
            {
                "schema":
                    "HIL-R2-BENCH-EVIDENCE-001",
                "gate_status":
                    "PASS",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert (
        result["status"]
        == "READY_FOR_COLLECTION"
    )
    assert (
        result["timing_ready"]
        is True
    )
    assert (
        "cells:no_samples_yet"
        in result["warnings"]
    )


def test_hil_fail_blocks(
    tmp_path,
):
    write_cells(
        tmp_path
    )
    timing_dir = (
        tmp_path
        / "timing"
    )
    timing_dir.mkdir()
    (
        timing_dir
        / "hil_r2.json"
    ).write_text(
        json.dumps(
            {
                "schema":
                    "HIL-R2-BENCH-EVIDENCE-001",
                "gate_status":
                    "FAIL",
            }
        ),
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "timing:not_pass"
        in result["errors"]
    )


def test_bad_cells_header_blocks(
    tmp_path,
):
    (
        tmp_path
        / "timing"
    ).mkdir()
    (
        tmp_path
        / "sys_err_cells.csv"
    ).write_text(
        "bad,header\n",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=config(),
        repository_root=tmp_path,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "cells:header"
        in result["errors"]
    )


def test_bad_config_blocks(
    tmp_path,
):
    write_cells(
        tmp_path
    )
    (
        tmp_path
        / "timing"
    ).mkdir()
    cfg = config()
    cfg["min_cells"] = 0

    result = evaluate_preflight(
        manifest=manifest(),
        gate_config=cfg,
        repository_root=tmp_path,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "invalid_config:min_cells"
        in result["errors"]
    )
