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

    queue = result["execution_queue"]
    assert queue is not None
    assert queue["schema"] == "EXTERNAL-EXECUTION-QUEUE-001"

    queued_ids = {
        row["item_id"]
        for row in queue["queue"]
    }
    assert "SYS_ERR_MEASURED" in queued_ids

    recipes = result["execution_recipes"]
    assert recipes is not None
    assert recipes["schema"] == "EXTERNAL-EXECUTION-RECIPE-001"

    sys_err_recipe = next(
        row
        for row in recipes["recipes"]
        if row["item_id"] == "SYS_ERR_MEASURED"
    )
    assert sys_err_recipe["status"] == "READY"
    assert sys_err_recipe["result_schema"] == "SYS-ERR-GATE-001"


def test_recipes_match_queue_order(tmp_path):
    manifest = load_json(MANIFEST)
    bundle = make_hil_bundle(tmp_path)

    result, candidate = run_pipeline(
        project_manifest=manifest,
        bundle=bundle,
        bundle_root=tmp_path,
    )

    assert candidate is not None
    queue_ids = [
        row["item_id"]
        for row in result["execution_queue"]["queue"]
    ]
    recipe_ids = [
        row["item_id"]
        for row in result["execution_recipes"]["recipes"]
    ]
    assert recipe_ids == queue_ids


def test_ingest_failure_does_not_create_candidate_queue_or_recipes(tmp_path):
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
    assert result["execution_queue"] is None
    assert result["execution_recipes"] is None


def test_promotion_hold_still_returns_candidate_manifest_queue_and_recipes(tmp_path):
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
    assert result["execution_queue"] is not None
    assert result["execution_recipes"] is not None


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
