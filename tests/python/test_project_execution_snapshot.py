from copy import deepcopy

from tools.evidence_status import load_json
from tools.project_execution_snapshot import build_snapshot


MANIFEST = "evidence/project_evidence_manifest.json"


def test_snapshot_builds_all_execution_layers():
    manifest = load_json(MANIFEST)
    result = build_snapshot(manifest)

    assert result["schema"] == "PROJECT-EXECUTION-SNAPSHOT-001"
    assert result["status"] == "READY"
    assert result["readiness"]["schema"] == "MEASUREMENT-READINESS-001"
    assert result["execution_queue"]["schema"] == "EXTERNAL-EXECUTION-QUEUE-001"
    assert result["execution_recipes"]["schema"] == "EXTERNAL-EXECUTION-RECIPE-001"
    assert result["summary"]["queue_depth"] == len(
        result["execution_queue"]["queue"]
    )


def test_snapshot_does_not_mutate_manifest():
    manifest = load_json(MANIFEST)
    original = deepcopy(manifest)

    build_snapshot(manifest)

    assert manifest == original


def test_snapshot_can_materialize_next_job_pack(tmp_path):
    manifest = load_json(MANIFEST)
    job_dir = tmp_path / "next_job"

    result = build_snapshot(
        manifest,
        job_pack_dir=job_dir,
    )

    assert result["next_job_pack"] is not None
    assert result["next_job_pack"]["schema"] == "EXTERNAL-EVIDENCE-JOB-PACK-001"
    assert result["next_job_pack_validation"]["status"] == "TEMPLATE_READY"
    assert (job_dir / "job_manifest.json").is_file()


def test_summary_counts_match_readiness():
    manifest = load_json(MANIFEST)
    result = build_snapshot(manifest)
    readiness = result["readiness"]

    assert result["summary"]["ready_for_external_execution"] == len(
        readiness["ready_for_external_execution"]
    )
    assert result["summary"]["blocked_items"] == len(
        readiness["blocked_items"]
    )
    assert result["summary"]["closed_items"] == len(
        readiness["closed_items"]
    )
