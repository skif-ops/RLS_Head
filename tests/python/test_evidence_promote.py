import hashlib
import json
from pathlib import Path

from tools.evidence_promote import promote_claim


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_manifest(*ids: str) -> dict:
    return {
        "schema": "PROJECT-EVIDENCE-MANIFEST-001",
        "items": [
            {
                "id": item_id,
                "status": "OPEN",
                "evidence_level": "OPEN",
                "synthetic": False,
                "requires_measured_evidence": True,
            }
            for item_id in ids
        ],
        "milestones": {},
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def measured_evm_manifest(
    *,
    synthetic: bool = False,
) -> dict:
    return {
        "schema": "EVM-RUN-MANIFEST-001",
        "run_id": "MEAS-EVM-A300-001",
        "mode": "QUALIFY",
        "profile_id": "PF-TRACK-CFG-001",
        "profile_config_sha256": "a" * 64,
        "source_commit": "b" * 40,
        "target_id": "RCS-A-001",
        "range_nominal_m": 300.0,
        "rcs_m2": 0.01,
        "start_time_us": 1_000_000,
        "end_time_us": 2_000_000,
        "truth_status": "VALID",
        "time_alignment_valid": True,
        "config_locked": True,
        "evidence_level": "MEASURED_EVM",
        "synthetic_fixture": synthetic,
        "raw_capture_enabled": False,
        "environment": {
            "temperature_c": 20.0,
            "precipitation_state": "DRY",
        },
        "files": [
            {
                "path": "truth.csv",
                "sha256": "c" * 64,
                "kind": "truth",
            },
            {
                "path": "radar.bin",
                "sha256": "d" * 64,
                "kind": "radar",
            },
            {
                "path": "diag.json",
                "sha256": "e" * 64,
                "kind": "diagnostics",
            },
        ],
    }


def test_m300_measured_promotion_pass(tmp_path):
    result_path = tmp_path / "m300.json"
    write_json(
        result_path,
        {
            "schema": "M300-REPORT-001",
            "track_status": "TRACK_PASS",
            "m300_track_db": 1.5,
        },
    )

    run_path = tmp_path / "run.json"
    write_json(
        run_path,
        measured_evm_manifest(),
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "M300_MEASURED",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "M300-REPORT-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_EVM",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "evm_run_manifest",
                    "path": run_path.name,
                    "sha256": sha256(run_path),
                }
            ],
        },
    }

    result, updated = promote_claim(
        project_manifest=project_manifest(
            "M300_MEASURED"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is True
    assert result["derived_status"] == "PASS"
    assert result["errors"] == []

    item = updated["items"][0]

    assert item["status"] == "PASS"
    assert item["evidence_level"] == "MEASURED_EVM"
    assert item["synthetic"] is False
    assert item["evidence_claim"]["result_sha256"] == sha256(
        result_path
    )


def test_checked_in_m300_ci_fixture_rejected(tmp_path):
    source = Path(
        "tests/fixtures/m300_measured_gate_pass.json"
    )
    result_path = tmp_path / "m300_fixture.json"
    result_path.write_bytes(source.read_bytes())

    run_path = tmp_path / "run.json"
    write_json(
        run_path,
        measured_evm_manifest(),
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "M300_MEASURED",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "M300-REPORT-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_EVM",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "evm_run_manifest",
                    "path": run_path.name,
                    "sha256": sha256(run_path),
                }
            ],
        },
    }

    result, updated = promote_claim(
        project_manifest=project_manifest(
            "M300_MEASURED"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is False
    assert result["derived_status"] == "INVALID"
    assert any(
        item.startswith(
            "result_fixture_marker:fixture_note"
        )
        for item in result["errors"]
    )
    assert updated["items"][0]["status"] == "OPEN"


def test_synthetic_evm_manifest_rejected(tmp_path):
    result_path = tmp_path / "m300.json"
    write_json(
        result_path,
        {
            "schema": "M300-REPORT-001",
            "track_status": "TRACK_PASS",
        },
    )

    run_path = tmp_path / "run.json"
    write_json(
        run_path,
        measured_evm_manifest(
            synthetic=True
        ),
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "M300_MEASURED",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "M300-REPORT-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_EVM",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "evm_run_manifest",
                    "path": run_path.name,
                    "sha256": sha256(run_path),
                }
            ],
        },
    }

    result, _ = promote_claim(
        project_manifest=project_manifest(
            "M300_MEASURED"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is False
    assert any(
        "provenance_fixture_marker" in item
        or "provenance_synthetic" in item
        for item in result["errors"]
    )


def test_hash_mismatch_rejected(tmp_path):
    result_path = tmp_path / "sys_err.json"
    write_json(
        result_path,
        {
            "schema": "SYS-ERR-GATE-001",
            "status": "PASS",
        },
    )

    capture = tmp_path / "capture.csv"
    capture.write_text(
        "kind,value_us,count\npps,10,\n",
        encoding="utf-8",
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "SYS_ERR_MEASURED",
        "result": {
            "path": result_path.name,
            "sha256": "0" * 64,
            "schema": "SYS-ERR-GATE-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_BENCH",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "bench_capture",
                    "path": capture.name,
                    "sha256": sha256(capture),
                }
            ],
        },
    }

    result, _ = promote_claim(
        project_manifest=project_manifest(
            "SYS_ERR_MEASURED"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is False
    assert "result:hash_mismatch" in result["errors"]


def test_sys_err_bench_promotion_pass(tmp_path):
    result_path = tmp_path / "sys_err.json"
    write_json(
        result_path,
        {
            "schema": "SYS-ERR-GATE-001",
            "status": "PASS",
        },
    )

    capture = tmp_path / "capture.csv"
    capture.write_text(
        "kind,value_us,count\n"
        "radar_imu,10,\n"
        "pps,5,\n",
        encoding="utf-8",
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "SYS_ERR_MEASURED",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "SYS-ERR-GATE-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_BENCH",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "bench_capture",
                    "path": capture.name,
                    "sha256": sha256(capture),
                }
            ],
        },
    }

    result, updated = promote_claim(
        project_manifest=project_manifest(
            "SYS_ERR_MEASURED"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is True
    assert result["derived_status"] == "PASS"
    assert updated["items"][0]["status"] == "PASS"


def test_carrier_review_a_promotion_pass(tmp_path):
    result_path = tmp_path / "carrier.json"
    write_json(
        result_path,
        {
            "schema": "CARRIER-REVIEW-A-RESULT-001",
            "status": "PASS",
            "synthetic_fixture": False,
            "evidence_level": "CAD_REVIEW",
        },
    )

    erc = tmp_path / "erc.json"
    write_json(
        erc,
        {
            "kicad_version": "9.0.9",
            "sheets": [
                {
                    "path": "/",
                    "violations": [],
                }
            ],
        },
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "CARRIER_REVIEW_A",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "CARRIER-REVIEW-A-RESULT-001",
        },
        "provenance": {
            "evidence_level": "CAD_REVIEW",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "erc_json",
                    "path": erc.name,
                    "sha256": sha256(erc),
                }
            ],
        },
    }

    manifest = project_manifest(
        "CARRIER_REVIEW_A"
    )
    manifest["items"][0][
        "requires_measured_evidence"
    ] = False

    result, updated = promote_claim(
        project_manifest=manifest,
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is True
    assert result["derived_status"] == "PASS"
    assert updated["items"][0]["evidence_level"] == "CAD_REVIEW"


def test_unsupported_physical_antenna_item_rejected(
    tmp_path,
):
    result_path = tmp_path / "ant.json"
    write_json(
        result_path,
        {
            "schema": "ANT-MEASUREMENT-001",
            "status": "PASS",
        },
    )

    capture = tmp_path / "pattern.csv"
    capture.write_text(
        "az_deg,gain_db\n0,10\n",
        encoding="utf-8",
    )

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": "PHYSICAL_ANT_MEASUREMENT",
        "result": {
            "path": result_path.name,
            "sha256": sha256(result_path),
            "schema": "ANT-MEASUREMENT-001",
        },
        "provenance": {
            "evidence_level": "MEASURED_EM",
            "synthetic": False,
            "artifacts": [
                {
                    "kind": "pattern_capture",
                    "path": capture.name,
                    "sha256": sha256(capture),
                }
            ],
        },
    }

    result, _ = promote_claim(
        project_manifest=project_manifest(
            "PHYSICAL_ANT_MEASUREMENT"
        ),
        claim=claim,
        repository_root=tmp_path,
    )

    assert result["promotion_allowed"] is False
    assert "unsupported_item" in result["errors"]
