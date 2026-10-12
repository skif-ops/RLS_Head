from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "ANT-D1-EM-EXTERNAL-PREFLIGHT-001"
REQUIRED_KINDS = {
    "solver_export",
    "model_input",
    "material_definition",
    "antenna_map",
}
INPUT_KINDS = {
    "model_input",
    "material_definition",
}
REAL_LEVELS = {
    "SIMULATED_EM",
    "SIMULATED_EM_CORRELATED",
    "MEASURED_EM",
}


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

    if manifest.get("schema") != "ANT-D1-EM-MANIFEST-001":
        errors.append("manifest_schema")

    for field in (
        "model_id",
        "model_revision",
        "solver_name",
        "solver_version",
    ):
        value = str(manifest.get(field, "")).strip()
        if not value or "<FILL" in value:
            errors.append(f"missing_or_placeholder:{field}")

    if manifest.get("synthetic_fixture") is not False:
        errors.append("synthetic_fixture_not_false")

    level = str(manifest.get("evidence_level", "")).strip()
    if level not in REAL_LEVELS:
        errors.append("unsupported_evidence_level")

    raw = manifest.get("artifacts")
    if not isinstance(raw, list):
        errors.append("artifacts_not_list")
        raw = []

    artifacts: dict[str, dict] = {}
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            errors.append(f"artifact_invalid:{index}")
            continue
        kind = str(entry.get("kind", "")).strip()
        if not kind:
            errors.append(f"artifact_missing_kind:{index}")
            continue
        if kind in artifacts:
            errors.append(f"duplicate_artifact_kind:{kind}")
            continue
        artifacts[kind] = entry

    for kind in sorted(REQUIRED_KINDS - set(artifacts)):
        errors.append(f"missing_artifact:{kind}")

    for kind in sorted(REQUIRED_KINDS & set(artifacts)):
        entry = artifacts[kind]
        relative = str(entry.get("path", "")).strip()
        expected = str(entry.get("sha256", "")).strip().lower()

        if not relative or "<FILL" in relative:
            errors.append(f"{kind}:missing_or_placeholder_path")
            continue

        try:
            path = _safe_path(root, relative)
        except ValueError as exc:
            errors.append(f"{kind}:{exc}")
            continue

        if kind in INPUT_KINDS:
            if not path.is_file():
                errors.append(f"{kind}:missing_input_file")
        elif not path.is_file():
            warnings.append(f"{kind}:output_not_present_yet")

        if (
            not expected
            or "<fill" in expected.lower()
            or len(expected) != 64
            or any(ch not in "0123456789abcdef" for ch in expected)
        ):
            warnings.append(f"{kind}:sha256_not_final")

    status = (
        "READY_FOR_SOLVER_EXECUTION"
        if not errors
        else "BLOCKED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "required_artifact_kinds": sorted(REQUIRED_KINDS),
        "required_input_kinds": sorted(INPUT_KINDS),
        "notes": [
            (
                "READY_FOR_SOLVER_EXECUTION means model/material provenance "
                "is structurally ready for external EM execution."
            ),
            (
                "Solver export and antenna map may be absent before execution; "
                "they must exist and be hash-final before ANT-D1-EM evidence validation."
            ),
            (
                "This preflight does not encode or freeze production Tx/Rx coordinates."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a D1 EM external solver evidence package"
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
    return 0 if result["status"] == "READY_FOR_SOLVER_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
