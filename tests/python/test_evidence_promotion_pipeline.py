import json
from copy import deepcopy
from pathlib import Path

from tools.evidence_status import load_json
from tools.evidence_promotion_pipeline import run_pipeline


MANIFEST = "evidence/project_evidence_manifest.json"


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def make_hil_bundle(tmp_path: Path, *, gate_status: str = "PASS") -> dict:
    write_json(
        tmp_path / "result.json",
        {
            "schema": "HIL-R2-BENCH-EVIDENCE-001",
            "gate_status": gate_status,
            "reason_codes": [],
        },
    )
    (tmp_path / "timing_capture.csv").write_text(
        "kind,value_us,count\nradar_imu,1.0,1\npps,1.0,1\n",
        encoding="utf-8",
    )
    return {
        "schema": "EXTERNAL-EVIDENCE-BUNDLE-001",
        "kind": "hil_r2_bench",
        "item_id": "HIL_R2_BENCH_MEASURED",
        "evidence_level": "MEASURED_BENCH",
        "synthetic": False,
        "result": {
            "path": "result.json",
            "schema": "HIL-R2-BENCH-EVIDENCE-001",
        },
        "artifacts": [
            {
                "kind": "timing_capture",
                "path": "timing_capture.csv",
            }
        ],
    }


def test_pass_bundle_returns_candidate_manifest_and_recalculates_readiness(tmp_path):
    manifest = load_json(MANIFEST)
    bundle = make_hil_bundle(tmp_path)

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
    )

    assert result["status"] == "CANDIDATE_READY"
    assert candidate is not None

    hil = next(
        item
        for item in candidate["items"]
        if item["id"] == "HIL_R2_BENCH_MEASURED"
    )
    assert hil["status"] == "PASS"
    assert hil["synthetic"] is False

    sys_err = next(
        row
        for row in result["readiness"]["items"]
        if row["item_id"] == "SYS_ERR_MEASURED"
    )
    assert sys_err["readiness"] == "READY_FOR_EXTERNAL_EXECUTION"


def test_ingest_failure_does_not_create_candidate(tmp_path):
    manifest = load_json(MANIFEST)
    bundle = make_hil_bundle(tmp_path)
    bundle["synthetic"] = True

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
    )

    assert result["status"] == "REJECTED"
    assert candidate is None
    assert result["promotion"] is None


def test_promotion_hold_still_returns_candidate_manifest(tmp_path):
    manifest = load_json(MANIFEST)
    bundle = make_hil_bundle(tmp_path, gate_status="INSUFFICIENT")

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
    )

    assert result["status"] == "CANDIDATE_READY"
    assert candidate is not None

    hil = next(
        item
        for item in candidate["items"]
        if item["id"] == "HIL_R2_BENCH_MEASURED"
    )
    assert hil["status"] == "HOLD"


def test_authoritative_manifest_object_is_not_mutated(tmp_path):
    manifest = load_json(MANIFEST)
    original = deepcopy(manifest)
    bundle = make_hil_bundle(tmp_path)

    _, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
    )

    assert candidate is not None
    assert manifest == original
