from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from tools.evm_run_manifest import (
    validate_reference_ladder,
    validate_run_manifest,
)


CLAIM_SCHEMA = "MEASURED-EVIDENCE-CLAIM-001"
MANIFEST_SCHEMA = "PROJECT-EVIDENCE-MANIFEST-001"
RESULT_SCHEMA = "EVIDENCE-PROMOTION-RESULT-001"

MEASURED_LEVELS = {
    "MEASURED_EVM",
    "MEASURED_HIL",
    "MEASURED_BENCH",
    "MEASURED_EM",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}

SUPPORTED_ITEMS = {
    "REFERENCE_RANGE_MEASURED",
    "M300_MEASURED",
    "ANT_D1_EM_REAL",
    "ANT_D1_SIM_GATE_REAL",
    "HIL_R2_BENCH_MEASURED",
    "SYS_ERR_MEASURED",
    "CARRIER_REVIEW_A",
    "AWR_EVM_PROFILE_MEASURED",
    "PHYSICAL_ANT_MEASUREMENT",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe path:{relative}")

    root_resolved = root.resolve()
    candidate = (root / rel).resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"path escapes repository root:{relative}"
        ) from exc

    return candidate


def _fixture_markers(data: object) -> list[str]:
    markers: list[str] = []

    if isinstance(data, dict):
        if data.get("synthetic_fixture") is True:
            markers.append("synthetic_fixture")

        fixture_note = data.get("fixture_note")
        if isinstance(fixture_note, str) and fixture_note.strip():
            markers.append("fixture_note")

        for value in data.values():
            markers.extend(_fixture_markers(value))

    elif isinstance(data, list):
        for value in data:
            markers.extend(_fixture_markers(value))

    return markers


def _verify_file(
    root: Path,
    entry: dict,
    *,
    prefix: str,
) -> tuple[Path | None, list[str]]:
    errors: list[str] = []

    relative = str(entry.get("path", "")).strip()
    expected = str(entry.get("sha256", "")).strip().lower()

    if not relative:
        return None, [f"{prefix}:missing_path"]

    if len(expected) != 64 or any(
        ch not in "0123456789abcdef"
        for ch in expected
    ):
        return None, [f"{prefix}:invalid_sha256"]

    try:
        path = safe_path(root, relative)
    except ValueError as exc:
        return None, [f"{prefix}:{exc}"]

    if not path.is_file():
        return None, [f"{prefix}:missing_file"]

    actual = sha256_file(path)

    if actual != expected:
        errors.append(f"{prefix}:hash_mismatch")

    return path, errors


def _status_from_simple(
    value: str,
) -> str:
    if value == "PASS":
        return "PASS"
    if value == "CONDITIONAL":
        return "CONDITIONAL"
    if value in {"HOLD", "INCONCLUSIVE", "INSUFFICIENT"}:
        return "HOLD"
    return "FAIL"


def _evaluate_m300(
    result: dict,
    source_json: list[tuple[str, dict]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if result.get("schema") != "M300-REPORT-001":
        return "INVALID", ["result_schema"]

    manifests = [
        data
        for kind, data in source_json
        if kind == "evm_run_manifest"
    ]

    if not manifests:
        return "HOLD", ["missing_evm_run_manifest"]

    measured_300 = []

    for manifest in manifests:
        try:
            validated = validate_run_manifest(manifest)
        except ValueError:
            return "INVALID", ["invalid_evm_run_manifest"]

        if validated["status"] != "MEASURED_READY":
            reasons.append("evm_manifest_not_measured")
            continue

        if (
            validated["range_nominal_m"] is not None
            and abs(float(validated["range_nominal_m"]) - 300.0)
            <= 1.0e-6
            and validated["rcs_m2"] is not None
            and abs(float(validated["rcs_m2"]) - 0.01)
            <= 1.0e-9
        ):
            measured_300.append(validated)

    if not measured_300:
        reasons.append("missing_measured_300m_rcs001")

    if reasons:
        return "HOLD", sorted(set(reasons))

    track_status = str(
        result.get("track_status", "UNKNOWN")
    )

    if track_status == "TRACK_PASS":
        return "PASS", []

    if track_status in {
        "INCONCLUSIVE",
        "HOLD",
    }:
        return "HOLD", ["m300_inconclusive"]

    return "FAIL", ["mandatory_300m_track_not_passed"]


def _evaluate_reference_range(
    result: dict,
    source_json: list[tuple[str, dict]],
) -> tuple[str, list[str]]:
    if result.get("schema") != "REFERENCE-RANGE-RESULT-001":
        return "INVALID", ["result_schema"]

    manifests = [
        data
        for kind, data in source_json
        if kind == "evm_run_manifest"
    ]

    if len(manifests) < 6:
        return "HOLD", ["insufficient_evm_run_manifests"]

    try:
        ladder = validate_reference_ladder(manifests)
    except ValueError:
        return "INVALID", ["invalid_reference_ladder"]

    if ladder["status"] != "DATA_READY":
        return "HOLD", [
            "reference_ladder_not_measured_complete",
            *ladder.get("reason_codes", []),
        ]

    if result.get("status") == "DATA_READY":
        return "PASS", []

    if result.get("status") in {"INCOMPLETE", "FIT_POOR"}:
        return "FAIL", [
            f"reference_result_{str(result.get('status')).lower()}"
        ]

    return "HOLD", ["reference_result_unknown_status"]


def _evaluate_hil_r2(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "HIL-R2-BENCH-EVIDENCE-001":
        return "INVALID", ["result_schema"]

    value = str(result.get("gate_status", "UNKNOWN"))

    if value == "PASS":
        return "PASS", []
    if value == "INSUFFICIENT":
        return "HOLD", ["bench_evidence_insufficient"]

    return "FAIL", [
        *(
            result.get("reason_codes", [])
            if isinstance(result.get("reason_codes"), list)
            else []
        ),
        "hil_r2_bench_fail",
    ]


def _evaluate_sys_err(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "SYS-ERR-GATE-001":
        return "INVALID", ["result_schema"]

    value = str(result.get("status", "UNKNOWN"))
    status = _status_from_simple(value)

    return (
        status,
        [] if status == "PASS" else [f"sys_err_{value.lower()}"],
    )


def _evaluate_carrier(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "CARRIER-REVIEW-A-RESULT-001":
        return "INVALID", ["result_schema"]

    if result.get("synthetic_fixture") is True:
        return "INVALID", ["carrier_result_synthetic"]

    if result.get("evidence_level") != "CAD_REVIEW":
        return "HOLD", ["carrier_evidence_level"]

    value = str(result.get("status", "UNKNOWN"))

    return (
        _status_from_simple(value),
        [] if value == "PASS" else [f"carrier_{value.lower()}"],
    )


def _evaluate_ant_em(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "ANT-D1-EM-EVIDENCE-001":
        return "INVALID", ["result_schema"]

    if result.get("synthetic_fixture") is True:
        return "INVALID", ["ant_em_result_synthetic"]

    value = str(result.get("status", "UNKNOWN"))

    if value == "DATA_READY":
        return "PASS", []

    if value in {"HOLD", "INCOMPLETE", "TEST_READY"}:
        return "HOLD", [f"ant_em_{value.lower()}"]

    return "FAIL", [f"ant_em_{value.lower()}"]


def _evaluate_ant_gate(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "ANT-SIM-GATE-001":
        return "INVALID", ["result_schema"]

    value = str(result.get("status", "UNKNOWN"))
    status = _status_from_simple(value)

    return (
        status,
        [] if status == "PASS" else [f"ant_sim_{value.lower()}"],
    )


def _evaluate_physical_antenna(
    result: dict,
) -> tuple[str, list[str]]:
    if result.get("schema") != "ANT-MEASUREMENT-001":
        return "INVALID", ["result_schema"]

    if result.get("synthetic_fixture") is True:
        return "INVALID", ["antenna_measurement_synthetic"]

    value = str(result.get("status", "UNKNOWN"))

    if value == "PASS":
        return "PASS", []

    if value == "CONDITIONAL":
        return "CONDITIONAL", [
            "antenna_measurement_conditional"
        ]

    if value in {"HOLD", "INCOMPLETE"}:
        return "HOLD", [
            f"antenna_measurement_{value.lower()}"
        ]

    return "FAIL", [
        f"antenna_measurement_{value.lower()}"
    ]


def _evaluate_evm_profile(
    result: dict,
    source_json: list[tuple[str, dict]],
) -> tuple[str, list[str]]:
    if result.get("schema") != "EVM-PROFILE-RESULT-001":
        return "INVALID", ["result_schema"]

    if result.get("status") != "MEASURED_READY":
        return "HOLD", ["profile_campaign_not_measured_ready"]

    manifests = [
        data
        for kind, data in source_json
        if kind == "evm_run_manifest"
    ]

    if len(manifests) < 4:
        return "HOLD", ["insufficient_profile_manifests"]

    for manifest in manifests:
        try:
            validated = validate_run_manifest(manifest)
        except ValueError:
            return "INVALID", ["invalid_profile_manifest"]

        if validated["status"] != "MEASURED_READY":
            return "HOLD", ["profile_manifest_not_measured"]

    profiles = result.get("profiles")

    if not isinstance(profiles, dict):
        return "INVALID", ["missing_profiles"]

    track = profiles.get("TRACK")

    if not isinstance(track, dict):
        return "INVALID", ["missing_track_profile"]

    track_status = str(track.get("status", "UNKNOWN"))

    if track_status == "OPERATIONAL":
        return "PASS", []

    if track_status == "CONDITIONAL":
        return "CONDITIONAL", ["track_profile_conditional"]

    return "FAIL", ["track_profile_not_operational"]


def _evaluate_claim(
    item_id: str,
    result: dict,
    source_json: list[tuple[str, dict]],
) -> tuple[str, list[str]]:
    if item_id == "M300_MEASURED":
        return _evaluate_m300(result, source_json)

    if item_id == "REFERENCE_RANGE_MEASURED":
        return _evaluate_reference_range(result, source_json)

    if item_id == "HIL_R2_BENCH_MEASURED":
        return _evaluate_hil_r2(result)

    if item_id == "SYS_ERR_MEASURED":
        return _evaluate_sys_err(result)

    if item_id == "CARRIER_REVIEW_A":
        return _evaluate_carrier(result)

    if item_id == "ANT_D1_EM_REAL":
        return _evaluate_ant_em(result)

    if item_id == "ANT_D1_SIM_GATE_REAL":
        return _evaluate_ant_gate(result)

    if item_id == "AWR_EVM_PROFILE_MEASURED":
        return _evaluate_evm_profile(result, source_json)

    if item_id == "PHYSICAL_ANT_MEASUREMENT":
        return _evaluate_physical_antenna(result)

    return "INVALID", ["unsupported_item"]


def _allowed_level(
    item_id: str,
    evidence_level: str,
) -> bool:
    if item_id in {
        "REFERENCE_RANGE_MEASURED",
        "M300_MEASURED",
        "AWR_EVM_PROFILE_MEASURED",
    }:
        return evidence_level in {
            "MEASURED_EVM",
            "MEASURED_INTEGRATED",
            "MEASURED_FIELD",
        }

    if item_id in {
        "HIL_R2_BENCH_MEASURED",
        "SYS_ERR_MEASURED",
    }:
        return evidence_level in {
            "MEASURED_HIL",
            "MEASURED_BENCH",
            "MEASURED_INTEGRATED",
            "MEASURED_FIELD",
        }

    if item_id == "CARRIER_REVIEW_A":
        return evidence_level == "CAD_REVIEW"

    if item_id in {
        "ANT_D1_EM_REAL",
        "ANT_D1_SIM_GATE_REAL",
    }:
        return evidence_level in {
            "SIMULATED_EM",
            "SIMULATED_EM_CORRELATED",
            "MEASURED_EM",
        }

    if item_id == "PHYSICAL_ANT_MEASUREMENT":
        return evidence_level in {
            "MEASURED_EM",
            "MEASURED_INTEGRATED",
            "MEASURED_FIELD",
        }

    return False


def promote_claim(
    *,
    project_manifest: dict,
    claim: dict,
    repository_root: str | Path,
) -> tuple[dict, dict]:
    root = Path(repository_root)
    errors: list[str] = []
    reasons: list[str] = []

    if project_manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unexpected project evidence manifest schema")

    if claim.get("schema") != CLAIM_SCHEMA:
        raise ValueError("unexpected evidence claim schema")

    item_id = str(claim.get("item_id", "")).strip()

    if item_id not in SUPPORTED_ITEMS:
        errors.append("unsupported_item")

    provenance = claim.get("provenance")

    if not isinstance(provenance, dict):
        errors.append("missing_provenance")
        provenance = {}

    if provenance.get("synthetic") is not False:
        errors.append("provenance_not_explicitly_non_synthetic")

    evidence_level = str(
        provenance.get("evidence_level", "")
    ).strip()

    if not _allowed_level(item_id, evidence_level):
        errors.append("evidence_level_not_allowed")

    result_entry = claim.get("result")

    if not isinstance(result_entry, dict):
        errors.append("missing_result")
        result_entry = {}

    result_path, result_errors = _verify_file(
        root,
        result_entry,
        prefix="result",
    )
    errors.extend(result_errors)

    result: dict = {}

    if result_path is not None and not result_errors:
        try:
            result = load_json(result_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"result_json:{exc}")

    if result:
        markers = _fixture_markers(result)

        if markers:
            errors.extend(
                f"result_fixture_marker:{marker}"
                for marker in sorted(set(markers))
            )

        expected_schema = str(
            result_entry.get("schema", "")
        ).strip()

        if expected_schema and result.get("schema") != expected_schema:
            errors.append("result_claim_schema_mismatch")

    artifact_entries = provenance.get("artifacts", [])

    if not isinstance(artifact_entries, list):
        errors.append("provenance_artifacts_not_list")
        artifact_entries = []

    if not artifact_entries:
        errors.append("missing_provenance_artifacts")

    source_json: list[tuple[str, dict]] = []
    verified_artifacts = []

    for index, entry in enumerate(artifact_entries):
        if not isinstance(entry, dict):
            errors.append(
                f"provenance_artifact_invalid:{index}"
            )
            continue

        kind = str(entry.get("kind", "")).strip()

        if not kind:
            errors.append(
                f"provenance_artifact_missing_kind:{index}"
            )
            continue

        path, file_errors = _verify_file(
            root,
            entry,
            prefix=f"provenance:{index}",
        )
        errors.extend(file_errors)

        if path is None or file_errors:
            continue

        artifact_record = {
            "kind": kind,
            "path": str(entry.get("path")),
            "sha256": sha256_file(path),
        }

        verified_artifacts.append(
            artifact_record
        )

        if path.suffix.lower() == ".json":
            try:
                data = load_json(path)
            except (OSError, json.JSONDecodeError):
                errors.append(
                    f"provenance_json_parse:{index}"
                )
                continue

            markers = _fixture_markers(data)

            if markers:
                errors.extend(
                    f"provenance_fixture_marker:{index}:{marker}"
                    for marker in sorted(set(markers))
                )

            if data.get("synthetic_fixture") is True:
                errors.append(
                    f"provenance_synthetic:{index}"
                )

            source_json.append(
                (kind, data)
            )

    if not errors:
        derived_status, derived_reasons = (
            _evaluate_claim(
                item_id,
                result,
                source_json,
            )
        )
        reasons.extend(derived_reasons)
    else:
        derived_status = "INVALID"

    items = project_manifest.get("items")

    if not isinstance(items, list):
        raise ValueError("project evidence items must be a list")

    target = None

    for item in items:
        if item.get("id") == item_id:
            target = item
            break

    if target is None:
        errors.append("item_not_in_project_manifest")
        derived_status = "INVALID"

    promotion_allowed = (
        not errors
        and derived_status
        in {"PASS", "CONDITIONAL", "FAIL", "HOLD"}
    )

    updated = deepcopy(project_manifest)

    if promotion_allowed:
        for item in updated["items"]:
            if item.get("id") != item_id:
                continue

            item["status"] = derived_status
            item["evidence_level"] = evidence_level
            item["synthetic"] = False
            item["evidence_claim"] = {
                "result_path": str(
                    result_entry.get("path", "")
                ),
                "result_sha256": sha256_file(
                    result_path
                ) if result_path else "",
                "provenance_artifacts":
                    verified_artifacts,
            }
            item["note"] = (
                f"Promoted by {CLAIM_SCHEMA}; "
                f"derived status {derived_status}."
            )
            break

    promotion_result = {
        "schema": RESULT_SCHEMA,
        "item_id": item_id,
        "promotion_allowed": promotion_allowed,
        "derived_status": derived_status,
        "evidence_level": evidence_level,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "verified_provenance_artifacts":
            verified_artifacts,
    }

    return promotion_result, updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify and promote one project evidence claim"
    )

    parser.add_argument(
        "--manifest",
        required=True,
    )
    parser.add_argument(
        "--claim",
        required=True,
    )
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--output-manifest",
        required=True,
    )
    parser.add_argument(
        "--output-result",
        required=True,
    )

    args = parser.parse_args()

    result, updated = promote_claim(
        project_manifest=load_json(
            args.manifest
        ),
        claim=load_json(args.claim),
        repository_root=args.repository_root,
    )

    Path(args.output_result).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    Path(args.output_manifest).write_text(
        json.dumps(updated, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "PROMOTED"
        if result["promotion_allowed"]
        else "REJECTED"
    )

    return 0 if result["promotion_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
