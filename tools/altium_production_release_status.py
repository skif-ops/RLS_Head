from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "ALTIUM-PRODUCTION-RELEASE-STATUS-001"

REQUIRED = {
    "equivalence_result": "hardware/system_carrier/altium/equivalence/altium_equivalence_result.json",
    "native_drc_result": "hardware/system_carrier/altium/release/native_drc_result.json",
    "mechanical_review": "hardware/system_carrier/altium/release/mechanical_review.json",
    "fabricator_binding": "hardware/system_carrier/altium/release/fabricator_binding.json",
    "return_path_si_review": "hardware/system_carrier/altium/release/return_path_si_review.json",
    "dfm_result": "hardware/system_carrier/altium/release/dfm_result.json",
    "outjob_release_manifest": "hardware/system_carrier/altium/release/outjob_release_manifest.json",
    "manifest": "hardware/system_carrier/altium/release/manifest.json",
}

EXPECTED_SCHEMAS = {
    "equivalence_result": "ALTIUM-EQUIVALENCE-RESULT-001",
    "native_drc_result": "ALTIUM-NATIVE-DRC-RESULT-001",
    "mechanical_review": "ALTIUM-MECHANICAL-REVIEW-001",
    "fabricator_binding": "ALTIUM-FABRICATOR-BINDING-001",
    "return_path_si_review": "ALTIUM-RETURN-PATH-SI-REVIEW-001",
    "dfm_result": "ALTIUM-DFM-RESULT-001",
    "outjob_release_manifest": "ALTIUM-OUTJOB-RELEASE-MANIFEST-001",
}


def evaluate(repository_root: str | Path = ".") -> dict:
    root = Path(repository_root)
    evidence: dict[str, dict] = {}
    missing: list[str] = []
    invalid: list[str] = []
    non_pass: list[str] = []

    for artifact_id, relative in REQUIRED.items():
        path = root / relative
        item = {"path": relative, "present": path.is_file()}
        evidence[artifact_id] = item
        if not path.is_file():
            missing.append(artifact_id)
            continue
        if artifact_id == "manifest":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append(artifact_id)
            continue
        item["schema"] = payload.get("schema")
        item["status"] = payload.get("status")
        if payload.get("schema") != EXPECTED_SCHEMAS[artifact_id]:
            invalid.append(artifact_id)
        if payload.get("status") != "PASS":
            non_pass.append(artifact_id)

    equivalence_ready = (
        evidence["equivalence_result"]["present"]
        and "equivalence_result" not in invalid
        and "equivalence_result" not in non_pass
    )

    release_evidence_ids = [
        "native_drc_result",
        "mechanical_review",
        "fabricator_binding",
        "return_path_si_review",
        "dfm_result",
        "outjob_release_manifest",
    ]
    release_evidence_complete = all(
        evidence[name]["present"] for name in release_evidence_ids
    )
    release_reviews_pass = all(
        name not in invalid and name not in non_pass
        for name in release_evidence_ids
    ) and release_evidence_complete

    manifest_ready = evidence["manifest"]["present"]

    if not equivalence_ready:
        status = "WAITING_EQUIVALENCE_PASS"
        next_action = "COMPLETE_NATIVE_EQUIVALENCE"
    elif not release_evidence_complete:
        status = "WAITING_RELEASE_EVIDENCE"
        next_action = "COMPLETE_DRC_MECHANICAL_FABRICATOR_SI_DFM_OUTJOB_EVIDENCE"
    elif invalid:
        status = "INVALID_RELEASE_EVIDENCE"
        next_action = "FIX_RELEASE_EVIDENCE_SCHEMA_OR_FORMAT"
    elif not release_reviews_pass:
        status = "WAITING_RELEASE_REVIEWS"
        next_action = "CLOSE_NON_PASS_RELEASE_REVIEWS"
    elif not manifest_ready:
        status = "WAITING_RELEASE_MANIFEST"
        next_action = "BUILD_PRODUCTION_RELEASE_MANIFEST"
    else:
        status = "READY_TO_RUN_PRODUCTION_RELEASE_GATE"
        next_action = "RUN_ALTIUM_PRODUCTION_RELEASE_GATE"

    return {
        "schema": SCHEMA,
        "status": status,
        "next_action": next_action,
        "equivalence_ready": equivalence_ready,
        "release_evidence_complete": release_evidence_complete,
        "release_reviews_pass": release_reviews_pass,
        "manifest_ready": manifest_ready,
        "missing_artifacts": sorted(missing),
        "invalid_artifacts": sorted(set(invalid)),
        "non_pass_artifacts": sorted(set(non_pass)),
        "evidence": evidence,
        "production_authorized": False,
        "notes": [
            "This status tool never grants production authority.",
            "Production authority is granted only by ALTIUM_PRODUCTION_RELEASE_GATE PASS.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(args.repository_root)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
