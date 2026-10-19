from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MANIFEST_SCHEMA = "ALTIUM-EQUIVALENCE-MANIFEST-001"
RESULT_SCHEMA = "ALTIUM-EQUIVALENCE-RESULT-001"

REQUIRED_ARTIFACTS = {
    "project",
    "schematic",
    "pcb",
    "import_log",
    "compile_report",
    "bom_export",
    "netlist_export",
    "footprint_report",
    "component_inventory",
    "net_inventory",
    "rule_inventory",
    "native_audit_result",
}

REQUIRED_CHECKS = {
    "bom_designator_mpn_equivalence",
    "pinmap_equivalence",
    "connector_pinout_equivalence",
    "netlist_equivalence",
    "footprint_equivalence",
    "hierarchy_equivalence",
    "rules_equivalence",
    "stackup_equivalence",
    "no_76_81GHz_rf_on_system_carrier",
    "native_pcb_audit",
}

EXPECTED_EXTENSIONS = {
    "project": ".PrjPcb",
    "schematic": ".SchDoc",
    "pcb": ".PcbDoc",
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


def validate_manifest(
    manifest_path: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    manifest_path = Path(manifest_path)
    root = Path(repository_root)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

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

    for artifact_id in REQUIRED_ARTIFACTS:
        item = artifacts.get(artifact_id)
        if item is None:
            continue

        relative = str(item.get("path", "")).strip()
        expected_hash = str(
            item.get("sha256", "")
        ).strip().lower()

        try:
            path = safe_repo_path(root, relative)
        except ValueError as exc:
            errors.append(
                f"artifact_path:{artifact_id}:{exc}"
            )
            continue

        if not path.is_file():
            errors.append(
                f"artifact_missing:{artifact_id}"
            )
            continue

        actual_hash = sha256_file(path)
        hash_ok = (
            len(expected_hash) == 64
            and actual_hash == expected_hash
        )
        integrity[artifact_id] = {
            "path": relative,
            "sha256_expected": expected_hash,
            "sha256_actual": actual_hash,
            "hash_ok": hash_ok,
        }
        resolved[artifact_id] = path

        if not hash_ok:
            errors.append(
                f"hash_mismatch:{artifact_id}"
            )

    for artifact_id, extension in EXPECTED_EXTENSIONS.items():
        item = artifacts.get(artifact_id)
        if item is None:
            continue
        if not str(item.get("path", "")).endswith(extension):
            errors.append(
                f"extension:{artifact_id}:{extension}"
            )

    compile_result = None
    compile_path = resolved.get("compile_report")
    if compile_path is not None:
        try:
            compile_result = json.loads(
                compile_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"compile_report_parse:{exc}")
        else:
            if (
                compile_result.get("schema")
                != "ALTIUM-COMPILE-REPORT-001"
            ):
                errors.append("compile_report_schema")
            compile_errors = int(
                compile_result.get("errors", -1)
            )
            compile_warnings = int(
                compile_result.get("warnings", -1)
            )
            if compile_errors != 0:
                reasons.append(
                    f"COMPILE_ERRORS:{compile_errors}"
                )
            if compile_warnings != 0:
                reasons.append(
                    f"COMPILE_WARNINGS:{compile_warnings}"
                )

    native_audit = None
    native_audit_path = resolved.get("native_audit_result")
    if native_audit_path is not None:
        try:
            native_audit = json.loads(
                native_audit_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"native_audit_parse:{exc}")
        else:
            if (
                native_audit.get("schema")
                != "ALTIUM-NATIVE-AUDIT-RESULT-001"
            ):
                errors.append("native_audit_schema")
            if native_audit.get("status") != "PASS":
                reasons.append("NATIVE_AUDIT")

            input_sha256 = native_audit.get("input_sha256")
            if not isinstance(input_sha256, dict):
                errors.append("native_audit_input_sha256")
            else:
                for artifact_id in (
                    "component_inventory",
                    "net_inventory",
                    "rule_inventory",
                ):
                    actual = str(
                        integrity.get(artifact_id, {}).get(
                            "sha256_actual",
                            "",
                        )
                    ).lower()
                    claimed = str(
                        input_sha256.get(artifact_id, "")
                    ).lower()
                    if not actual or claimed != actual:
                        errors.append(
                            f"native_audit_input_hash:{artifact_id}"
                        )

    checks_raw = manifest.get("checks")
    checks: dict[str, str] = {}
    if not isinstance(checks_raw, dict):
        errors.append("checks")
    else:
        for name in sorted(REQUIRED_CHECKS):
            value = str(
                checks_raw.get(name, "MISSING")
            ).strip()
            checks[name] = value
            if value != "PASS":
                reasons.append(
                    f"CHECK_{name.upper()}"
                )

    preserved_kicad = bool(
        manifest.get("preserve_kicad", False)
    )
    if not preserved_kicad:
        reasons.append("KICAD_NOT_PRESERVED")

    review_a = str(
        manifest.get("review_a_status", "")
    ).strip()
    if review_a != "PASS":
        reasons.append("REVIEW_A_NOT_PASS")

    synthetic = bool(
        manifest.get("synthetic_fixture", False)
    )
    evidence_level = str(
        manifest.get("evidence_level", "")
    ).strip()

    if errors:
        status = "INVALID"
    elif reasons:
        status = "FAIL"
    elif synthetic:
        status = "TEST_READY"
    elif evidence_level != "NATIVE_ALTIUM":
        status = "HOLD"
        reasons.append("EVIDENCE_LEVEL")
    else:
        status = "PASS"

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "board_id": manifest.get("board_id"),
        "hardware_revision": manifest.get(
            "hardware_revision"
        ),
        "primary_cad": manifest.get("primary_cad"),
        "synthetic_fixture": synthetic,
        "evidence_level": evidence_level,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "integrity": integrity,
        "compile": compile_result,
        "native_audit": native_audit,
        "checks": checks,
        "preserve_kicad": preserved_kicad,
        "review_a_status": review_a,
        "layout_authority": (
            "AUTHORIZED"
            if status == "PASS"
            else "NOT_AUTHORIZED"
        ),
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "PASS authorizes native Altium PCB implementation "
                "as the layout authority for System Carrier Rev.A."
            ),
            (
                "PASS does not authorize production; DRC, SI/return-path, "
                "DFM and manufacturing release gates remain separate."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = validate_manifest(
        args.manifest,
        args.repository_root,
    )
    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] in {"PASS", "TEST_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
