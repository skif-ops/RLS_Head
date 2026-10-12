from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.carrier_review_a import (
    REQUIRED_AUDITS,
    validate_bom,
    validate_pinmap,
)


SCHEMA = "CARRIER-REVIEW-A-EXTERNAL-PREFLIGHT-001"


def _safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe_path")
    root_resolved = root.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("path_escapes_root") from exc
    return candidate


def evaluate_preflight(
    *,
    manifest: dict,
    repository_root: str | Path,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    root = Path(repository_root)

    if manifest.get("schema") != "CARRIER-REVIEW-A-MANIFEST-001":
        errors.append("manifest_schema")
    if manifest.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")
    if manifest.get("hardware_revision") != "A":
        errors.append("hardware_revision")
    if manifest.get("cad_tool") != "KiCad":
        errors.append("cad_tool")
    if manifest.get("synthetic_fixture") is not False:
        errors.append("synthetic_fixture_not_false")
    if manifest.get("evidence_level") != "CAD_REVIEW":
        errors.append("evidence_level")

    erc_policy = manifest.get("erc_policy")
    if not isinstance(erc_policy, dict):
        errors.append("erc_policy")
    else:
        for field in ("errors_allowed", "warnings_allowed"):
            try:
                value = int(erc_policy.get(field))
                if value < 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"erc_policy:{field}")

    raw = manifest.get("artifacts")
    if not isinstance(raw, list):
        errors.append("artifacts_not_list")
        raw = []

    artifacts: dict[str, dict] = {}
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            errors.append(f"artifact_invalid:{index}")
            continue
        artifact_id = str(entry.get("id", "")).strip()
        if not artifact_id:
            errors.append(f"artifact_missing_id:{index}")
            continue
        if artifact_id in artifacts:
            errors.append(f"duplicate_artifact:{artifact_id}")
            continue
        artifacts[artifact_id] = entry

    for required in ("schematic", "erc_json", "pinmap", "bom"):
        if required not in artifacts:
            errors.append(f"missing_artifact:{required}")

    resolved: dict[str, Path] = {}
    for artifact_id, entry in artifacts.items():
        relative = str(entry.get("path", "")).strip()
        if not relative or "<FILL" in relative:
            errors.append(f"{artifact_id}:missing_or_placeholder_path")
            continue
        try:
            path = _safe_path(root, relative)
        except ValueError as exc:
            errors.append(f"{artifact_id}:{exc}")
            continue
        resolved[artifact_id] = path

    for input_id in ("pinmap", "bom"):
        path = resolved.get(input_id)
        if path is None or not path.is_file():
            errors.append(f"{input_id}:missing_input_file")

    schematic = resolved.get("schematic")
    if schematic is not None:
        if not str(schematic).endswith(".kicad_sch"):
            errors.append("schematic_extension")
        elif not schematic.is_file():
            warnings.append("schematic:not_present_yet")

    erc_json = resolved.get("erc_json")
    if erc_json is not None and not erc_json.is_file():
        warnings.append("erc_json:not_present_yet")

    if not errors:
        try:
            pinmap_result = validate_pinmap(resolved["pinmap"])
            if pinmap_result["status"] != "PASS":
                errors.append("pinmap_not_ready")
        except ValueError:
            errors.append("pinmap_parse")

        try:
            bom_result = validate_bom(resolved["bom"])
            if bom_result["status"] != "PASS":
                errors.append("bom_not_ready")
        except ValueError:
            errors.append("bom_parse")

    audits = manifest.get("audits")
    if not isinstance(audits, dict):
        errors.append("audits")
        audits = {}

    for audit in sorted(REQUIRED_AUDITS):
        if audit not in audits:
            errors.append(f"missing_audit:{audit}")
            continue
        value = str(audits[audit]).strip().upper()
        if value not in {"PENDING", "PASS"}:
            errors.append(f"audit_state:{audit}")
        elif value == "PENDING":
            warnings.append(f"audit_pending:{audit}")

    status = (
        "READY_FOR_CAD_REVIEW_EXECUTION"
        if not errors
        else "BLOCKED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "notes": [
            (
                "READY_FOR_CAD_REVIEW_EXECUTION means authoritative pinmap/BOM "
                "inputs and Review A structure are ready for KiCad capture/ERC."
            ),
            (
                "Schematic, ERC output and audit PASS states may still be pending "
                "until the actual CAD Review A execution."
            ),
            "This preflight does not authorize fabrication.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight System Carrier Review A external CAD execution"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(
        Path(args.manifest).read_text(encoding="utf-8")
    )
    result = evaluate_preflight(
        manifest=manifest,
        repository_root=args.repository_root,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY_FOR_CAD_REVIEW_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
