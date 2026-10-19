from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-PRODUCTION-RELEASE-STATUS-001"
NATIVE_PCB_PATH = "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"

REQUIRED = {
    "native_schematic": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc",
    "native_pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
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

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



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
        if artifact_id in {"native_schematic", "native_pcb"}:
            item["sha256"] = sha256_file(path)
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

    equivalence_ready = False
    equivalence_schematic_stale = False
    approved_schematic_sha256 = ""
    current_schematic_sha256 = str(
        evidence.get("native_schematic", {}).get("sha256", "")
    ).lower()
    equivalence_path = root / REQUIRED["equivalence_result"]
    if (
        evidence["equivalence_result"]["present"]
        and "equivalence_result" not in invalid
        and "equivalence_result" not in non_pass
    ):
        try:
            equivalence_payload = json.loads(
                equivalence_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append("equivalence_result")
        else:
            equivalence_ready = (
                equivalence_payload.get("layout_authority") == "AUTHORIZED"
                and equivalence_payload.get("production_authority")
                == "NOT_AUTHORIZED"
            )

            integrity = equivalence_payload.get("integrity")
            if isinstance(integrity, dict):
                schematic_integrity = integrity.get("schematic")
                if isinstance(schematic_integrity, dict):
                    approved_schematic_sha256 = str(
                        schematic_integrity.get("sha256_actual", "")
                    ).strip().lower()

            if equivalence_ready:
                if (
                    len(current_schematic_sha256) != 64
                    or len(approved_schematic_sha256) != 64
                    or current_schematic_sha256
                    != approved_schematic_sha256
                ):
                    equivalence_schematic_stale = True
                    equivalence_ready = False

    release_evidence_ids = [
        "native_schematic",
        "native_pcb",
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

    source_binding_errors: list[str] = []
    native_pcb_hash = str(
        evidence.get("native_pcb", {}).get("sha256", "")
    ).lower()
    for artifact_id in (
        "native_drc_result",
        "mechanical_review",
        "fabricator_binding",
        "return_path_si_review",
        "dfm_result",
        "outjob_release_manifest",
    ):
        item = evidence.get(artifact_id, {})
        if not item.get("present"):
            continue
        path = root / REQUIRED[artifact_id]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        source_pcb = str(payload.get("source_pcb", "")).strip()
        source_hash = str(
            payload.get("source_pcb_sha256", "")
        ).strip().lower()
        if source_pcb != NATIVE_PCB_PATH:
            source_binding_errors.append(
                f"{artifact_id}:source_pcb"
            )
        if (
            not native_pcb_hash
            or len(source_hash) != 64
            or source_hash != native_pcb_hash
        ):
            source_binding_errors.append(
                f"{artifact_id}:source_pcb_sha256"
            )

    release_reviews_pass = all(
        name not in invalid and name not in non_pass
        for name in release_evidence_ids
    ) and release_evidence_complete and not source_binding_errors

    manifest_ready = False
    manifest_path = root / REQUIRED["manifest"]
    manifest_errors: list[str] = []
    if evidence["manifest"]["present"]:
        try:
            release_manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append("manifest")
        else:
            if (
                release_manifest.get("schema")
                != "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001"
            ):
                invalid.append("manifest")
            else:
                artifacts_raw = release_manifest.get("artifacts")
                if not isinstance(artifacts_raw, list):
                    manifest_errors.append("artifacts")
                else:
                    artifacts: dict[str, dict] = {}
                    for item in artifacts_raw:
                        if not isinstance(item, dict):
                            manifest_errors.append("artifact_entry")
                            continue
                        artifact_id = str(item.get("id", "")).strip()
                        if not artifact_id:
                            manifest_errors.append("artifact_without_id")
                            continue
                        if artifact_id in artifacts:
                            manifest_errors.append(
                                f"duplicate_artifact:{artifact_id}"
                            )
                            continue
                        artifacts[artifact_id] = item

                    expected_ids = set(REQUIRED) - {"manifest"}
                    missing_ids = sorted(expected_ids - set(artifacts))
                    if missing_ids:
                        manifest_errors.append(
                            "missing_artifacts:" + ",".join(missing_ids)
                        )

                    for artifact_id in sorted(expected_ids & set(artifacts)):
                        item = artifacts[artifact_id]
                        expected_path = REQUIRED[artifact_id]
                        actual_path = str(item.get("path", "")).strip()
                        if actual_path != expected_path:
                            manifest_errors.append(
                                f"artifact_path:{artifact_id}"
                            )
                            continue

                        file_path = root / expected_path
                        expected_hash = str(
                            item.get("sha256", "")
                        ).strip().lower()
                        if (
                            not file_path.is_file()
                            or len(expected_hash) != 64
                            or expected_hash != sha256_file(file_path)
                        ):
                            manifest_errors.append(
                                f"artifact_hash:{artifact_id}"
                            )

                    manifest_ready = not manifest_errors
                    if manifest_errors:
                        invalid.append("manifest")

    if "equivalence_result" in invalid:
        status = "INVALID_EQUIVALENCE_EVIDENCE"
        next_action = "FIX_EQUIVALENCE_RESULT"
    elif equivalence_schematic_stale:
        status = "STALE_EQUIVALENCE"
        next_action = "RERUN_NATIVE_ALTIUM_EQUIVALENCE_GATE"
    elif not equivalence_ready:
        status = "WAITING_EQUIVALENCE_PASS"
        next_action = "COMPLETE_NATIVE_EQUIVALENCE"
    elif not release_evidence_complete:
        status = "WAITING_RELEASE_EVIDENCE"
        next_action = "COMPLETE_DRC_MECHANICAL_FABRICATOR_SI_DFM_OUTJOB_EVIDENCE"
    elif "manifest" in invalid:
        status = "INVALID_RELEASE_MANIFEST"
        next_action = "FIX_PRODUCTION_RELEASE_MANIFEST"
    elif invalid:
        status = "INVALID_RELEASE_EVIDENCE"
        next_action = "FIX_RELEASE_EVIDENCE_SCHEMA_OR_FORMAT"
    elif source_binding_errors:
        status = "INVALID_RELEASE_SOURCE_BINDING"
        next_action = "REBIND_RELEASE_EVIDENCE_TO_FINAL_NATIVE_PCBDOC"
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
        "equivalence_schematic_stale": equivalence_schematic_stale,
        "approved_schematic_sha256": approved_schematic_sha256,
        "current_schematic_sha256": current_schematic_sha256,
        "release_evidence_complete": release_evidence_complete,
        "release_reviews_pass": release_reviews_pass,
        "source_binding_errors": sorted(set(source_binding_errors)),
        "final_native_pcb_sha256": native_pcb_hash,
        "manifest_ready": manifest_ready,
        "manifest_errors": sorted(set(manifest_errors)),
        "missing_artifacts": sorted(missing),
        "invalid_artifacts": sorted(set(invalid)),
        "non_pass_artifacts": sorted(set(non_pass)),
        "evidence": evidence,
        "production_authorized": False,
        "notes": [
            "This status tool never grants production authority.",
            "Production authority is granted only by ALTIUM_PRODUCTION_RELEASE_GATE PASS.",
            "All post-routing evidence must be SHA-256-bound to the same final native PcbDoc.",
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
