from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MANIFEST_SCHEMA = "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001"
RESULT_SCHEMA = "ALTIUM-PRODUCTION-RELEASE-RESULT-001"

REQUIRED_ARTIFACTS = {
    "equivalence_result",
    "native_drc_result",
    "mechanical_review",
    "fabricator_binding",
    "return_path_si_review",
    "dfm_result",
    "outjob_release_manifest",
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


def safe_repo_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe artifact path: {relative}")
    root_resolved = root.resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"artifact escapes repository root: {relative}"
        ) from exc
    return path


def _read_json(path: Path, artifact_id: str, errors: list[str]) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{artifact_id}_parse:{exc}")
        return None


def validate_manifest(
    manifest_path: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    manifest_file = Path(manifest_path)
    root = Path(repository_root)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    errors: list[str] = []
    reasons: list[str] = []

    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("schema")
    if manifest.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")
    if manifest.get("hardware_revision") != "A":
        errors.append("hardware_revision")
    if manifest.get("primary_cad") != "Altium Designer":
        errors.append("primary_cad")

    artifacts_raw = manifest.get("artifacts")
    if not isinstance(artifacts_raw, list):
        raise ValueError("artifacts must be a list")

    artifacts: dict[str, dict] = {}
    for item in artifacts_raw:
        if not isinstance(item, dict):
            errors.append("artifact_entry")
            continue
        artifact_id = str(item.get("id", "")).strip()
        if not artifact_id:
            errors.append("artifact_without_id")
            continue
        if artifact_id in artifacts:
            errors.append(f"duplicate_artifact:{artifact_id}")
            continue
        artifacts[artifact_id] = item

    for missing in sorted(REQUIRED_ARTIFACTS - set(artifacts)):
        errors.append(f"missing_artifact:{missing}")

    integrity: dict[str, dict] = {}
    resolved: dict[str, Path] = {}
    evidence: dict[str, dict | None] = {}

    for artifact_id in sorted(REQUIRED_ARTIFACTS):
        item = artifacts.get(artifact_id)
        if item is None:
            continue
        relative = str(item.get("path", "")).strip()
        expected_hash = str(item.get("sha256", "")).strip().lower()
        try:
            path = safe_repo_path(root, relative)
        except ValueError as exc:
            errors.append(f"artifact_path:{artifact_id}:{exc}")
            continue
        if not path.is_file():
            errors.append(f"artifact_missing:{artifact_id}")
            continue
        actual_hash = sha256_file(path)
        hash_ok = len(expected_hash) == 64 and expected_hash == actual_hash
        integrity[artifact_id] = {
            "path": relative,
            "sha256_expected": expected_hash,
            "sha256_actual": actual_hash,
            "hash_ok": hash_ok,
        }
        resolved[artifact_id] = path
        if not hash_ok:
            errors.append(f"hash_mismatch:{artifact_id}")

    for artifact_id, path in resolved.items():
        result = _read_json(path, artifact_id, errors)
        evidence[artifact_id] = result
        if not isinstance(result, dict):
            continue
        if result.get("schema") != EXPECTED_SCHEMAS[artifact_id]:
            errors.append(f"{artifact_id}_schema")
        if result.get("status") != "PASS":
            reasons.append(f"{artifact_id.upper()}_NOT_PASS")

    equivalence = evidence.get("equivalence_result")
    if isinstance(equivalence, dict):
        if equivalence.get("layout_authority") != "AUTHORIZED":
            reasons.append("LAYOUT_AUTHORITY_NOT_AUTHORIZED")
        if equivalence.get("production_authority") != "NOT_AUTHORIZED":
            errors.append("equivalence_premature_production_authority")
        if equivalence.get("preserve_kicad") is not True:
            reasons.append("KICAD_NOT_PRESERVED")

    drc = evidence.get("native_drc_result")
    if isinstance(drc, dict):
        if int(drc.get("blocking_errors", -1)) != 0:
            reasons.append("DRC_BLOCKING_ERRORS")
        if int(drc.get("unrouted_nets", -1)) != 0:
            reasons.append("UNROUTED_NETS")

    mechanical = evidence.get("mechanical_review")
    if isinstance(mechanical, dict):
        for field in (
            "board_outline_frozen",
            "mounting_geometry_frozen",
            "connector_access_verified",
            "step_enclosure_verified",
        ):
            if mechanical.get(field) is not True:
                reasons.append(f"MECHANICAL_{field.upper()}")

    fabricator = evidence.get("fabricator_binding")
    if isinstance(fabricator, dict):
        for field in (
            "stackup_bound",
            "copper_weight_bound",
            "impedance_50r_bound",
            "impedance_100r_bound",
            "min_trace_clearance_bound",
            "via_rules_bound",
        ):
            if fabricator.get(field) is not True:
                reasons.append(f"FAB_{field.upper()}")

    si_review = evidence.get("return_path_si_review")
    if isinstance(si_review, dict):
        if int(si_review.get("p0_open_findings", -1)) != 0:
            reasons.append("SI_P0_OPEN_FINDINGS")
        if si_review.get("l2_ground_continuity_verified") is not True:
            reasons.append("L2_GROUND_CONTINUITY")
        if si_review.get("timing_return_paths_verified") is not True:
            reasons.append("TIMING_RETURN_PATHS")
        if si_review.get("ethernet_mdi_return_path_verified") is not True:
            reasons.append("ETH_MDI_RETURN_PATH")

    dfm = evidence.get("dfm_result")
    if isinstance(dfm, dict):
        if int(dfm.get("p0_open_items", -1)) != 0:
            reasons.append("DFM_P0_OPEN_ITEMS")

    outjob = evidence.get("outjob_release_manifest")
    if isinstance(outjob, dict):
        if outjob.get("required_outputs_complete") is not True:
            reasons.append("OUTJOB_REQUIRED_OUTPUTS_INCOMPLETE")
        if outjob.get("source_is_native_altium") is not True:
            reasons.append("OUTJOB_SOURCE_NOT_NATIVE_ALTIUM")

    synthetic = bool(manifest.get("synthetic_fixture", False))
    evidence_level = str(manifest.get("evidence_level", "")).strip()

    if errors:
        status = "INVALID"
    elif reasons:
        status = "FAIL"
    elif synthetic:
        status = "TEST_READY"
    elif evidence_level != "NATIVE_ALTIUM_RELEASE":
        status = "HOLD"
        reasons.append("EVIDENCE_LEVEL")
    else:
        status = "PASS"

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "board_id": manifest.get("board_id"),
        "hardware_revision": manifest.get("hardware_revision"),
        "primary_cad": manifest.get("primary_cad"),
        "synthetic_fixture": synthetic,
        "evidence_level": evidence_level,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "integrity": integrity,
        "evidence": evidence,
        "layout_authority": (
            "AUTHORIZED"
            if isinstance(equivalence, dict)
            and equivalence.get("layout_authority") == "AUTHORIZED"
            else "NOT_AUTHORIZED"
        ),
        "production_authority": (
            "AUTHORIZED"
            if status == "PASS"
            else "NOT_AUTHORIZED"
        ),
        "notes": [
            (
                "PASS is the repository manufacturing-release authority for "
                "EVT System Carrier Rev.A."
            ),
            (
                "A production PASS requires native Altium equivalence, zero "
                "blocking DRC/unrouted nets, mechanical freeze, fabricator "
                "binding, return-path/SI review, DFM closure and complete "
                "native-Altium manufacturing outputs."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate_manifest(
        args.manifest,
        repository_root=args.repository_root,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] in {"PASS", "TEST_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
