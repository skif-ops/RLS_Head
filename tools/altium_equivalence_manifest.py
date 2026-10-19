from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-EQUIVALENCE-MANIFEST-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    *,
    template_path: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    template = Path(template_path)
    root = Path(repository_root)

    manifest = json.loads(template.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema") != SCHEMA:
        errors.append("schema")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")

    for item in artifacts:
        if not isinstance(item, dict):
            errors.append("artifact_entry")
            continue
        artifact_id = str(item.get("id", "")).strip()
        relative = str(item.get("path", "")).strip()
        if not artifact_id or not relative:
            errors.append("artifact_identity")
            continue

        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"artifact_path:{artifact_id}")
            continue

        path = root / rel
        if not path.is_file():
            errors.append(f"missing_artifact:{artifact_id}")
            continue

        item["sha256"] = sha256_file(path)

    checks = manifest.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks")
    else:
        audit_item = next(
            (
                item
                for item in artifacts
                if isinstance(item, dict)
                and item.get("id") == "native_audit_result"
            ),
            None,
        )
        if isinstance(audit_item, dict):
            audit_path = root / str(audit_item.get("path", ""))
            if audit_path.is_file():
                try:
                    audit = json.loads(
                        audit_path.read_text(encoding="utf-8")
                    )
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
                else:
                    if (
                        audit.get("schema")
                        == "ALTIUM-NATIVE-AUDIT-RESULT-001"
                        and audit.get("status") == "PASS"
                    ):
                        verified = audit.get("verified_checks", {})
                        if isinstance(verified, dict):
                            for check_name in (
                                "native_pcb_audit",
                                "pinmap_equivalence",
                                "rules_equivalence",
                                "stackup_equivalence",
                            ):
                                if (
                                    check_name in checks
                                    and verified.get(check_name) == "PASS"
                                ):
                                    checks[check_name] = "PASS"
                        else:
                            checks["native_pcb_audit"] = "PASS"

    if isinstance(checks, dict):
        for artifact_id, schema, check_name in (
            (
                "bom_validation_result",
                "ALTIUM-NATIVE-BOM-RESULT-001",
                "bom_designator_mpn_equivalence",
            ),
            (
                "footprint_report",
                "ALTIUM-NATIVE-FOOTPRINT-RESULT-001",
                "footprint_equivalence",
            ),
            (
                "connector_validation_result",
                "ALTIUM-NATIVE-CONNECTOR-RESULT-001",
                "connector_pinout_equivalence",
            ),
            (
                "netlist_validation_result",
                "ALTIUM-NATIVE-NETLIST-RESULT-001",
                "netlist_equivalence",
            ),
            (
                "hierarchy_validation_result",
                "ALTIUM-NATIVE-HIERARCHY-RESULT-001",
                "hierarchy_equivalence",
            ),
        ):
            item = next(
                (
                    artifact
                    for artifact in artifacts
                    if isinstance(artifact, dict)
                    and artifact.get("id") == artifact_id
                ),
                None,
            )
            if not isinstance(item, dict):
                continue
            result_path = root / str(item.get("path", ""))
            if not result_path.is_file():
                continue
            try:
                result = json.loads(
                    result_path.read_text(encoding="utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            verified = result.get("verified_checks", {})
            if (
                result.get("schema") == schema
                and result.get("status") == "PASS"
                and isinstance(verified, dict)
                and verified.get(check_name) == "PASS"
                and check_name in checks
            ):
                checks[check_name] = "PASS"

    return {
        "status": "READY" if not errors else "INCOMPLETE",
        "errors": sorted(set(errors)),
        "manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = build_manifest(
        template_path=args.template,
        repository_root=args.repository_root,
    )

    if result["status"] == "READY":
        Path(args.output).write_text(
            json.dumps(result["manifest"], indent=2) + "\n",
            encoding="utf-8",
        )

    print(result["status"])
    return 0 if result["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
