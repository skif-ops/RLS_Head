import json
from pathlib import Path

from tools.altium_production_release_status import REQUIRED, evaluate


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def test_release_status_initially_waits_for_equivalence(tmp_path):
    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_EQUIVALENCE_PASS"
    assert result["equivalence_ready"] is False
    assert result["production_authorized"] is False


def test_release_status_waits_for_release_evidence(tmp_path):
    path = tmp_path / REQUIRED["equivalence_result"]
    _write_json(
        path,
        {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
        },
    )

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_RELEASE_EVIDENCE"
    assert result["equivalence_ready"] is True
    assert result["release_evidence_complete"] is False


def test_release_status_waits_for_non_pass_review(tmp_path):
    payloads = {
        "equivalence_result": {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
        },
        "native_drc_result": {
            "schema": "ALTIUM-NATIVE-DRC-RESULT-001",
            "status": "PASS",
        },
        "mechanical_review": {
            "schema": "ALTIUM-MECHANICAL-REVIEW-001",
            "status": "PASS",
        },
        "fabricator_binding": {
            "schema": "ALTIUM-FABRICATOR-BINDING-001",
            "status": "PENDING",
        },
        "return_path_si_review": {
            "schema": "ALTIUM-RETURN-PATH-SI-REVIEW-001",
            "status": "PASS",
        },
        "dfm_result": {
            "schema": "ALTIUM-DFM-RESULT-001",
            "status": "PASS",
        },
        "outjob_release_manifest": {
            "schema": "ALTIUM-OUTJOB-RELEASE-MANIFEST-001",
            "status": "PASS",
        },
    }

    for artifact_id, payload in payloads.items():
        _write_json(tmp_path / REQUIRED[artifact_id], payload)

    result = evaluate(tmp_path)

    assert result["status"] == "WAITING_RELEASE_REVIEWS"
    assert "fabricator_binding" in result["non_pass_artifacts"]


def test_release_status_ready_only_after_manifest(tmp_path):
    payloads = {
        "equivalence_result": {
            "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
            "status": "PASS",
        },
        "native_drc_result": {
            "schema": "ALTIUM-NATIVE-DRC-RESULT-001",
            "status": "PASS",
        },
        "mechanical_review": {
            "schema": "ALTIUM-MECHANICAL-REVIEW-001",
            "status": "PASS",
        },
        "fabricator_binding": {
            "schema": "ALTIUM-FABRICATOR-BINDING-001",
            "status": "PASS",
        },
        "return_path_si_review": {
            "schema": "ALTIUM-RETURN-PATH-SI-REVIEW-001",
            "status": "PASS",
        },
        "dfm_result": {
            "schema": "ALTIUM-DFM-RESULT-001",
            "status": "PASS",
        },
        "outjob_release_manifest": {
            "schema": "ALTIUM-OUTJOB-RELEASE-MANIFEST-001",
            "status": "PASS",
        },
    }

    for artifact_id, payload in payloads.items():
        _write_json(tmp_path / REQUIRED[artifact_id], payload)

    result = evaluate(tmp_path)
    assert result["status"] == "WAITING_RELEASE_MANIFEST"

    manifest = tmp_path / REQUIRED["manifest"]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")

    result = evaluate(tmp_path)
    assert result["status"] == "READY_TO_RUN_PRODUCTION_RELEASE_GATE"
