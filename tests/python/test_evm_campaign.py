from copy import deepcopy

from tools.evm_campaign import assemble_reference_campaign


SHA256 = "a" * 64
SHA1 = "b" * 40


def run_manifest(
    range_m,
    *,
    run_id=None,
    profile_id="PF-TRACK-CFG-001",
    target_id="REF-TARGET-001",
    evidence_level="SOFTWARE_CI",
    synthetic=True,
):
    run_id = run_id or f"R{int(range_m):03d}"

    return {
        "schema": "EVM-RUN-MANIFEST-001",
        "run_id": run_id,
        "mode": "QUALIFY",
        "profile_id": profile_id,
        "profile_config_sha256": SHA256,
        "source_commit": SHA1,
        "target_id": target_id,
        "range_nominal_m": float(range_m),
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
            "precipitation_state": "DRY",
        },
        "files": [
            {"path": "truth.csv", "sha256": SHA256, "kind": "truth"},
            {"path": "radar.bin", "sha256": SHA256, "kind": "radar"},
            {"path": "diag.json", "sha256": SHA256, "kind": "diagnostics"},
            {"path": "raw.bin", "sha256": SHA256, "kind": "raw_capture"},
        ],
    }


def campaign(
    *,
    evidence_level="SOFTWARE_CI",
    synthetic=True,
):
    return [
        (
            f"manifest_{range_m}.json",
            run_manifest(
                range_m,
                evidence_level=evidence_level,
                synthetic=synthetic,
            ),
        )
        for range_m in (50, 100, 150, 200, 250, 300)
    ]


def test_complete_synthetic_campaign_is_test_ready():
    result = assemble_reference_campaign(campaign())

    assert result["schema"] == "EVM-REFERENCE-CAMPAIGN-001"
    assert result["status"] == "TEST_READY"
    assert result["test_ranges_m"] == [
        50.0, 100.0, 150.0, 200.0, 250.0, 300.0
    ]
    assert result["measured_ranges_m"] == []


def test_complete_measured_campaign_is_measured_ready():
    result = assemble_reference_campaign(
        campaign(
            evidence_level="MEASURED_EVM",
            synthetic=False,
        )
    )

    assert result["status"] == "MEASURED_READY"
    assert result["missing_measured_ranges_m"] == []
    assert result["measured_profile_ids"] == ["PF-TRACK-CFG-001"]
    assert result["measured_target_ids"] == ["REF-TARGET-001"]


def test_missing_measured_range_is_incomplete():
    manifests = campaign(
        evidence_level="MEASURED_EVM",
        synthetic=False,
    )[:-1]

    result = assemble_reference_campaign(manifests)

    assert result["status"] == "INCOMPLETE"
    assert result["missing_measured_ranges_m"] == [300.0]
    assert "missing_measured_ranges" in result["reason_codes"]


def test_mixed_measured_profile_is_incomplete():
    manifests = campaign(
        evidence_level="MEASURED_EVM",
        synthetic=False,
    )

    path, item = manifests[-1]
    item = deepcopy(item)
    item["profile_id"] = "PF-LR1-CFG-001"
    manifests[-1] = (path, item)

    result = assemble_reference_campaign(manifests)

    assert result["status"] == "INCOMPLETE"
    assert "mixed_measured_profiles" in result["reason_codes"]


def test_duplicate_run_id_invalid():
    manifests = campaign()
    manifests[-1][1]["run_id"] = manifests[0][1]["run_id"]

    result = assemble_reference_campaign(manifests)

    assert result["status"] == "INVALID"
    assert "duplicate_run_ids" in result["reason_codes"]


def test_synthetic_measured_manifest_makes_campaign_invalid():
    manifests = campaign()
    manifests[0][1]["evidence_level"] = "MEASURED_EVM"

    result = assemble_reference_campaign(manifests)

    assert result["status"] == "INVALID"
    assert manifests[0][1]["run_id"] in result["invalid_runs"]
