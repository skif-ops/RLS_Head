import json
from pathlib import Path

from tools.evm_profile_external_preflight import (
    evaluate_preflight,
)


HEADER = (
    "run_id,profile_id,profile_class,range_m,rcs_m2,dynamics_class,"
    "fov_class,pd,track_availability,fresh_fraction,margin_db,"
    "sigma_az_deg,sigma_el_deg,update_hz,radar_latency_p99_ms,"
    "compute_util_p99_pct,ram_peak_pct,overrun_count,deadline_miss_count,"
    "edma_error_count,angle_status\n"
)


def write_manifest(
    path: Path,
    profile: str,
):
    path.write_text(
        json.dumps(
            {
                "schema":
                    "EVM-RUN-MANIFEST-001",
                "run_id":
                    f"RUN-{profile}",
                "mode": "QUALIFY",
                "profile_id": profile,
                "profile_config_sha256":
                    "a" * 64,
                "source_commit":
                    "b" * 40,
                "target_id": "TARGET",
                "range_nominal_m": 100.0,
                "rcs_m2": 0.01,
                "start_time_us": 1,
                "end_time_us": 2,
                "truth_status": "VALID",
                "time_alignment_valid": True,
                "config_locked": True,
                "evidence_level":
                    "MEASURED_EVM",
                "synthetic_fixture": False,
                "files": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_empty_campaign_ready_with_warnings(
    tmp_path,
):
    metrics = (
        tmp_path
        / "profile_metrics.csv"
    )
    metrics.write_text(
        HEADER,
        encoding="utf-8",
    )
    manifests = (
        tmp_path
        / "manifests"
    )
    manifests.mkdir()

    result = evaluate_preflight(
        metrics_csv=metrics,
        manifest_dir=manifests,
    )

    assert (
        result["status"]
        == "READY_FOR_COLLECTION"
    )
    assert (
        "metrics_csv_has_no_samples"
        in result["warnings"]
    )
    assert any(
        warning.startswith(
            "missing_profile_manifests:"
        )
        for warning
        in result["warnings"]
    )


def test_complete_profile_manifest_set_ready(
    tmp_path,
):
    metrics = (
        tmp_path
        / "profile_metrics.csv"
    )
    metrics.write_text(
        HEADER,
        encoding="utf-8",
    )
    manifests = (
        tmp_path
        / "manifests"
    )
    manifests.mkdir()

    for profile in (
        "TRACK",
        "LR1",
        "LR2",
        "LRX",
    ):
        write_manifest(
            manifests
            / f"{profile}.json",
            profile,
        )

    result = evaluate_preflight(
        metrics_csv=metrics,
        manifest_dir=manifests,
    )

    assert (
        result["status"]
        == "READY_FOR_COLLECTION"
    )
    assert (
        result["manifest_profile_ids"]
        == [
            "LR1",
            "LR2",
            "LRX",
            "TRACK",
        ]
    )


def test_invalid_manifest_blocks(
    tmp_path,
):
    metrics = (
        tmp_path
        / "profile_metrics.csv"
    )
    metrics.write_text(
        HEADER,
        encoding="utf-8",
    )
    manifests = (
        tmp_path
        / "manifests"
    )
    manifests.mkdir()
    (
        manifests
        / "bad.json"
    ).write_text(
        "{bad",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        metrics_csv=metrics,
        manifest_dir=manifests,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "invalid_manifest_json:bad.json"
        in result["errors"]
    )


def test_wrong_metrics_header_blocks(
    tmp_path,
):
    metrics = (
        tmp_path
        / "profile_metrics.csv"
    )
    metrics.write_text(
        "bad,header\n",
        encoding="utf-8",
    )
    manifests = (
        tmp_path
        / "manifests"
    )
    manifests.mkdir()

    result = evaluate_preflight(
        metrics_csv=metrics,
        manifest_dir=manifests,
    )

    assert (
        result["status"]
        == "BLOCKED"
    )
    assert (
        "metrics_csv_header"
        in result["errors"]
    )
