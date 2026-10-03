from copy import deepcopy

from tools.evm_run_manifest import (
    validate_reference_ladder,
    validate_run_manifest,
)


SHA256 = "a" * 64
SHA1 = "b" * 40


def manifest(
    *,
    run_id="EVM-E2-R050-001",
    range_m=50.0,
    evidence_level="MEASURED_EVM",
    synthetic=False,
):
    return {
        "schema": "EVM-RUN-MANIFEST-001",
        "run_id": run_id,
        "mode": "QUALIFY",
        "profile_id": "PF-TRACK-CFG-001",
        "profile_config_sha256": SHA256,
        "source_commit": SHA1,
        "target_id": "REF-TARGET-001",
        "range_nominal_m": range_m,
        "rcs_m2": 0.1,
        "start_time_us": 1_000_000,
        "end_time_us": 2_000_000,
        "truth_status": "VALID",
        "time_alignment_valid": True,
        "config_locked": True,
        "evidence_level": evidence_level,
        "synthetic_fixture": synthetic,
        "raw_capture_enabled": True,
        "environment": {
            "temperature_c": 20.0,
            "precipitation_state": "DRY"
        },
        "files": [
            {"path": "truth.csv", "sha256": SHA256, "kind": "truth"},
            {"path": "radar.bin", "sha256": SHA256, "kind": "radar"},
            {"path": "diag.json", "sha256": SHA256, "kind": "diagnostics"},
            {"path": "raw.bin", "sha256": SHA256, "kind": "raw_capture"},
        ],
    }


def test_measured_qualification_ready():
    result = validate_run_manifest(manifest())

    assert result["status"] == "MEASURED_READY"
    assert result["errors"] == []
    assert result["hold_reasons"] == []


def test_synthetic_fixture_never_measured_ready():
    data = manifest(
        evidence_level="SOFTWARE_CI",
        synthetic=True,
    )

    result = validate_run_manifest(data)

    assert result["status"] == "TEST_READY"


def test_synthetic_marked_measured_invalid():
    data = manifest(synthetic=True)

    result = validate_run_manifest(data)

    assert result["status"] == "INVALID"
    assert "synthetic_marked_measured" in result["errors"]


def test_qualification_without_truth_holds():
    data = manifest()
    data["truth_status"] = "PARTIAL"

    result = validate_run_manifest(data)

    assert result["status"] == "HOLD"
    assert "qualification_truth_not_valid" in result["hold_reasons"]


def test_raw_capture_consistency():
    data = manifest()
    data["files"] = [
        item
        for item in data["files"]
        if item["kind"] != "raw_capture"
    ]

    result = validate_run_manifest(data)

    assert result["status"] == "INVALID"
    assert "raw_capture_enabled_without_file" in result["errors"]


def test_reference_ladder_ready():
    manifests = []

    for range_m in (50, 100, 150, 200, 250, 300):
        manifests.append(
            manifest(
                run_id=f"EVM-E2-R{range_m:03d}-001",
                range_m=float(range_m),
            )
        )

    result = validate_reference_ladder(manifests)

    assert result["status"] == "DATA_READY"
    assert result["missing_ranges_m"] == []
    assert result["profile_ids"] == ["PF-TRACK-CFG-001"]
    assert result["target_ids"] == ["REF-TARGET-001"]


def test_reference_ladder_rejects_mixed_profile():
    manifests = []

    for range_m in (50, 100, 150, 200, 250, 300):
        item = manifest(
            run_id=f"EVM-E2-R{range_m:03d}-001",
            range_m=float(range_m),
        )

        if range_m == 300:
            item["profile_id"] = "PF-LR1-CFG-001"

        manifests.append(item)

    result = validate_reference_ladder(manifests)

    assert result["status"] == "INCOMPLETE"
    assert "mixed_profiles" in result["reason_codes"]
