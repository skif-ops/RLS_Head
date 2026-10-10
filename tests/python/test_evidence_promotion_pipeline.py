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

    sys_err = next(
        row
        for row in result["readiness"]["items"]
        if row["item_id"] == "SYS_ERR_MEASURED"
    )
    assert sys_err["readiness"] == "READY_FOR_EXTERNAL_EXECUTION"

    assert result["execution_queue"]["schema"] == "EXTERNAL-EXECUTION-QUEUE-001"
    assert result["execution_recipes"]["schema"] == "EXTERNAL-EXECUTION-RECIPE-001"
    assert result["priority_job_pack"] is None


def test_materializes_priority_job_pack_when_requested(tmp_path):
    manifest = load_json(MANIFEST)
    bundle_root = tmp_path / "incoming"
    bundle_root.mkdir()
    bundle = make_hil_bundle(bundle_root)
    job_pack_dir = tmp_path / "next_job"

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=bundle_root,
        job_pack_dir=job_pack_dir,
    )

    assert candidate is not None
    job_pack = result["priority_job_pack"]
    assert job_pack is not None
    assert job_pack["schema"] == "EXTERNAL-EVIDENCE-JOB-PACK-001"
    assert (job_pack_dir / "job_manifest.json").is_file()

    validation = result["priority_job_pack_validation"]
    assert validation["status"] == "TEMPLATE_READY"
    assert validation["item_id"] == job_pack["item_id"]


def test_selected_job_pack_matches_queue_priority(tmp_path):
    manifest = load_json(MANIFEST)
    bundle_root = tmp_path / "incoming"
    bundle_root.mkdir()
    bundle = make_hil_bundle(bundle_root)
    job_pack_dir = tmp_path / "priority_two"

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=bundle_root,
        job_pack_dir=job_pack_dir,
        job_pack_priority=2,
    )

    assert candidate is not None
    queue_row = result["execution_queue"]["queue"][1]
    assert result["priority_job_pack"]["item_id"] == queue_row["item_id"]


def test_ingest_failure_does_not_create_candidate_or_job_pack(tmp_path):
    manifest = load_json(MANIFEST)
    bundle = make_hil_bundle(tmp_path)
    bundle["synthetic"] = True

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
        job_pack_dir=tmp_path / "next_job",
    )

    assert result["status"] == "REJECTED"
    assert candidate is None
    assert result["priority_job_pack"] is None
    assert not (tmp_path / "next_job").exists()


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
