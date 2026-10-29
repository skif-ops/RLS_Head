from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


MANIFEST_SCHEMA = "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001"
RESULT_SCHEMA = "ALTIUM-PRODUCTION-RELEASE-RESULT-001"
NATIVE_PCB_PATH = "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"
NATIVE_SCHEMATIC_PATH = "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"

REQUIRED_ARTIFACTS = {
    "native_schematic",
    "native_pcb",
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


def _int_or_default(value: object, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _valid_text(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and not text.startswith("<")


def _validate_source_pcb_binding(
    payload: dict,
    *,
    artifact_id: str,
    actual_pcb_hash: str,
    errors: list[str],
) -> None:
    source_pcb = str(payload.get("source_pcb", "")).strip()
    claimed_hash = str(
        payload.get("source_pcb_sha256", "")
    ).strip().lower()

    if source_pcb != NATIVE_PCB_PATH:
        errors.append(f"{artifact_id}_source_pcb")
    if (
        len(claimed_hash) != 64
        or claimed_hash != actual_pcb_hash
    ):
        errors.append(f"{artifact_id}_source_pcb_hash")


def _validate_evidence_refs(
    root: Path,
    value: object,
    prefix: str,
    errors: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}_evidence_refs")
        return

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{prefix}_evidence_ref_entry:{index}")
            continue
        relative = str(item.get("path", "")).strip()
        expected_hash = str(item.get("sha256", "")).strip().lower()
        try:
            path = safe_repo_path(root, relative)
        except ValueError as exc:
            errors.append(
                f"{prefix}_evidence_ref_path:{index}:{exc}"
            )
            continue
        if not path.is_file():
            errors.append(
                f"{prefix}_evidence_ref_missing:{index}"
            )
            continue
        actual_hash = sha256_file(path)
        if len(expected_hash) != 64 or expected_hash != actual_hash:
            errors.append(
                f"{prefix}_evidence_ref_hash:{index}"
            )


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
        canonical_path = {
            "native_schematic": NATIVE_SCHEMATIC_PATH,
            "native_pcb": NATIVE_PCB_PATH,
        }.get(artifact_id)
        if canonical_path is not None and relative != canonical_path:
            errors.append(f"{artifact_id}_canonical_path")
            continue

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

    native_schematic_hash = str(
        integrity.get("native_schematic", {}).get(
            "sha256_actual",
            "",
        )
    ).lower()
    native_pcb_hash = str(
        integrity.get("native_pcb", {}).get(
            "sha256_actual",
            "",
        )
    ).lower()

    for artifact_id, path in resolved.items():
        if artifact_id in {"native_schematic", "native_pcb"}:
            continue
        result = _read_json(path, artifact_id, errors)
        evidence[artifact_id] = result
        if not isinstance(result, dict):
            continue
        if result.get("schema") != EXPECTED_SCHEMAS[artifact_id]:
            errors.append(f"{artifact_id}_schema")
        if result.get("status") != "PASS":
            reasons.append(f"{artifact_id.upper()}_NOT_PASS")

    if not native_schematic_hash:
        errors.append("native_schematic_hash")
    if not native_pcb_hash:
        errors.append("native_pcb_hash")

    for artifact_id in (
        "native_drc_result",
        "mechanical_review",
        "fabricator_binding",
        "return_path_si_review",
        "dfm_result",
        "outjob_release_manifest",
    ):
        payload = evidence.get(artifact_id)
        if isinstance(payload, dict):
            _validate_source_pcb_binding(
                payload,
                artifact_id=artifact_id,
                actual_pcb_hash=native_pcb_hash,
                errors=errors,
            )

    equivalence = evidence.get("equivalence_result")
    if isinstance(equivalence, dict):
        if equivalence.get("layout_authority") != "AUTHORIZED":
            reasons.append("LAYOUT_AUTHORITY_NOT_AUTHORIZED")

        eq_integrity = equivalence.get("integrity")
        approved_schematic_hash = ""
        if isinstance(eq_integrity, dict):
            schematic_integrity = eq_integrity.get("schematic")
            if isinstance(schematic_integrity, dict):
                approved_schematic_hash = str(
                    schematic_integrity.get("sha256_actual", "")
                ).strip().lower()

        if (
            len(native_schematic_hash) != 64
            or len(approved_schematic_hash) != 64
            or native_schematic_hash != approved_schematic_hash
        ):
            errors.append("equivalence_schematic_hash_mismatch")
        if equivalence.get("production_authority") != "NOT_AUTHORIZED":
            errors.append("equivalence_premature_production_authority")
        if equivalence.get("preserve_kicad") is not True:
            reasons.append("KICAD_NOT_PRESERVED")

    drc = evidence.get("native_drc_result")
    if isinstance(drc, dict):
        if _int_or_default(drc.get("blocking_errors")) != 0:
            reasons.append("DRC_BLOCKING_ERRORS")
        if _int_or_default(drc.get("unrouted_nets")) != 0:
            reasons.append("UNROUTED_NETS")
        source_report = str(drc.get("source_report", "")).strip()
        expected_report_hash = str(
            drc.get("source_report_sha256", "")
        ).strip().lower()
        if not source_report:
            errors.append("drc_source_report")
        else:
            try:
                report_path = safe_repo_path(root, source_report)
            except ValueError as exc:
                errors.append(f"drc_source_report_path:{exc}")
            else:
                if not report_path.is_file():
                    errors.append("drc_source_report_missing")
                else:
                    actual_report_hash = sha256_file(report_path)
                    if (
                        len(expected_report_hash) != 64
                        or expected_report_hash != actual_report_hash
                    ):
                        errors.append("drc_source_report_hash")

    mechanical = evidence.get("mechanical_review")
    if isinstance(mechanical, dict):
        for field in (
            "board_outline_frozen",
            "mounting_geometry_frozen",
            "connector_access_verified",
        ):
            if mechanical.get(field) is not True:
                reasons.append(f"MECHANICAL_{field.upper()}")
        if not _valid_text(mechanical.get("reviewer")):
            errors.append("mechanical_reviewer")
        _validate_evidence_refs(
            root,
            mechanical.get("evidence_refs"),
            "mechanical",
            errors,
        )

    fabricator = evidence.get("fabricator_binding")
    if isinstance(fabricator, dict):
        for field in (
            "stackup_bound",
            "copper_weight_bound",
            "min_trace_clearance_bound",
            "via_rules_bound",
        ):
            if fabricator.get(field) is not True:
                reasons.append(f"FAB_{field.upper()}")
        if not _valid_text(fabricator.get("fabricator")):
            errors.append("fabricator_name")
        _validate_evidence_refs(
            root,
            fabricator.get("evidence_refs"),
            "fabricator",
            errors,
        )

    si_review = evidence.get("return_path_si_review")
    if isinstance(si_review, dict):
        if _int_or_default(si_review.get("p0_open_findings")) != 0:
            reasons.append("SI_P0_OPEN_FINDINGS")
        if si_review.get("l2_ground_continuity_verified") is not True:
            reasons.append("L2_GROUND_CONTINUITY")
        if si_review.get("timing_return_paths_verified") is not True:
            reasons.append("TIMING_RETURN_PATHS")
        if si_review.get("host_uart_routes_verified") is not True:
            reasons.append("HOST_UART_ROUTES")
        if si_review.get("gnss_connector_routes_verified") is not True:
            reasons.append("GNSS_CONNECTOR_ROUTES")
        if si_review.get("power_hot_loop_verified") is not True:
            reasons.append("POWER_HOT_LOOP")
        if si_review.get("power_branch_widths_verified") is not True:
            reasons.append("POWER_BRANCH_WIDTHS")
        if si_review.get("five_volt_gnss_route_verified") is not True:
            reasons.append("FIVE_VOLT_GNSS_ROUTE")
        if si_review.get("no_mmwave_post_route_verified") is not True:
            reasons.append("NO_MMWAVE_POST_ROUTE")
        if not _valid_text(si_review.get("reviewer")):
            errors.append("si_reviewer")
        _validate_evidence_refs(
            root,
            si_review.get("evidence_refs"),
            "si",
            errors,
        )

    dfm = evidence.get("dfm_result")
    if isinstance(dfm, dict):
        if _int_or_default(dfm.get("p0_open_items")) != 0:
            reasons.append("DFM_P0_OPEN_ITEMS")

        dfm_profile_path = (
            root
            / "hardware/system_carrier/altium/ALTIUM_DFM_PROFILE_SYS_001.csv"
        )
        if not dfm_profile_path.is_file():
            errors.append("dfm_profile_missing")
        else:
            profile_hash = sha256_file(dfm_profile_path)
            if (
                str(dfm.get("profile_sha256", "")).strip().lower()
                != profile_hash
            ):
                errors.append("dfm_profile_hash")

            with dfm_profile_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                profile_rows = list(csv.DictReader(handle))
            expected_p0_ids = {
                str(row.get("dfm_id", "")).strip()
                for row in profile_rows
                if str(row.get("criticality", "")).strip() == "P0"
                and str(row.get("dfm_id", "")).strip()
            }
            closed_raw = dfm.get("closed_p0_ids")
            closed_p0_ids = (
                {
                    str(item).strip()
                    for item in closed_raw
                    if str(item).strip()
                }
                if isinstance(closed_raw, list)
                else set()
            )
            if closed_p0_ids != expected_p0_ids:
                reasons.append("DFM_P0_SET_INCOMPLETE")

        _validate_evidence_refs(
            root,
            dfm.get("evidence_refs"),
            "dfm",
            errors,
        )

    outjob = evidence.get("outjob_release_manifest")
    if isinstance(outjob, dict):
        if outjob.get("required_outputs_complete") is not True:
            reasons.append("OUTJOB_REQUIRED_OUTPUTS_INCOMPLETE")
        if outjob.get("source_is_native_altium") is not True:
            reasons.append("OUTJOB_SOURCE_NOT_NATIVE_ALTIUM")
        if outjob.get("all_schematics_from_native_altium") is not True:
            reasons.append("SCHEMATICS_NOT_FROM_NATIVE_ALTIUM")
        if outjob.get("all_production_outputs_from_native_altium") is not True:
            reasons.append("PRODUCTION_OUTPUTS_NOT_FROM_NATIVE_ALTIUM")

        contract_path = (
            root
            / "hardware/system_carrier/altium/ALTIUM_OUTJOB_CONTRACT_SYS_001.csv"
        )
        if not contract_path.is_file():
            errors.append("outjob_contract_missing")
        else:
            with contract_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                contract_rows = list(csv.DictReader(handle))
            required_ids = {
                str(row.get("output_id", "")).strip()
                for row in contract_rows
                if str(row.get("required", "")).strip() == "YES"
            }

            outputs_raw = outjob.get("outputs")
            if not isinstance(outputs_raw, list):
                errors.append("outjob_outputs")
                outputs_raw = []

            outputs: dict[str, dict] = {}
            for item in outputs_raw:
                if not isinstance(item, dict):
                    errors.append("outjob_output_entry")
                    continue
                output_id = str(item.get("output_id", "")).strip()
                if not output_id:
                    errors.append("outjob_output_without_id")
                    continue
                if output_id in outputs:
                    errors.append(f"outjob_duplicate:{output_id}")
                    continue
                outputs[output_id] = item

            missing_outputs = sorted(required_ids - set(outputs))
            if missing_outputs:
                errors.append(
                    "outjob_missing_required:"
                    + ",".join(missing_outputs)
                )

            for output_id in sorted(required_ids & set(outputs)):
                item = outputs[output_id]
                relative = str(item.get("path", "")).strip()
                expected_hash = str(
                    item.get("sha256", "")
                ).strip().lower()
                try:
                    output_path = safe_repo_path(root, relative)
                except ValueError as exc:
                    errors.append(
                        f"outjob_path:{output_id}:{exc}"
                    )
                    continue
                if not output_path.is_file():
                    errors.append(f"outjob_missing_file:{output_id}")
                    continue
                actual_hash = sha256_file(output_path)
                if (
                    len(expected_hash) != 64
                    or expected_hash != actual_hash
                ):
                    errors.append(f"outjob_hash:{output_id}")

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
        "native_schematic_sha256": native_schematic_hash,
        "native_pcb_sha256": native_pcb_hash,
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
                "A production PASS requires the current native SchDoc to "
                "match the equivalence-approved electrical baseline, plus zero "
                "blocking DRC/unrouted nets, compact-board mechanical review, "
                "fabricator baseline binding, return-path review, DFM closure and complete "
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
