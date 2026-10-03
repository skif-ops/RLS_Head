from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.antenna_map_validate import (
    load_config as load_map_config,
    load_csv as load_map_csv,
    validate_rows,
)


MANIFEST_SCHEMA = "ANT-D1-EM-MANIFEST-001"
RESULT_SCHEMA = "ANT-D1-EM-EVIDENCE-001"

REQUIRED_KINDS = {
    "solver_export",
    "model_input",
    "material_definition",
    "antenna_map",
}

REAL_LEVELS = {
    "SIMULATED_EM",
    "SIMULATED_EM_CORRELATED",
    "MEASURED_EM",
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe artifact path")

    root_resolved = root.resolve()
    candidate = (root / rel).resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            "artifact path escapes repository root"
        ) from exc

    return candidate


def evaluate_em_evidence(
    *,
    manifest: dict,
    map_validation_config: str | Path,
    repository_root: str | Path,
) -> dict:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unexpected D1 EM manifest schema")

    root = Path(repository_root)
    errors: list[str] = []

    model_id = str(manifest.get("model_id", "")).strip()
    model_revision = str(
        manifest.get("model_revision", "")
    ).strip()
    solver_name = str(
        manifest.get("solver_name", "")
    ).strip()
    solver_version = str(
        manifest.get("solver_version", "")
    ).strip()

    for name, value in {
        "model_id": model_id,
        "model_revision": model_revision,
        "solver_name": solver_name,
        "solver_version": solver_version,
    }.items():
        if not value:
            errors.append(f"missing_{name}")

    synthetic = bool(
        manifest.get("synthetic_fixture", False)
    )
    evidence_level = str(
        manifest.get("evidence_level", "")
    ).strip()

    artifacts_raw = manifest.get("artifacts")

    if not isinstance(artifacts_raw, list):
        errors.append("artifacts_not_list")
        artifacts_raw = []

    artifacts: dict[str, dict] = {}

    for index, item in enumerate(artifacts_raw):
        if not isinstance(item, dict):
            errors.append(f"artifact_invalid:{index}")
            continue

        kind = str(item.get("kind", "")).strip()

        if not kind:
            errors.append(f"artifact_missing_kind:{index}")
            continue

        if kind in artifacts:
            errors.append(f"duplicate_artifact_kind:{kind}")
            continue

        artifacts[kind] = item

    for kind in sorted(REQUIRED_KINDS - set(artifacts)):
        errors.append(f"missing_artifact:{kind}")

    verified: dict[str, dict] = {}
    resolved: dict[str, Path] = {}

    for kind in REQUIRED_KINDS:
        item = artifacts.get(kind)

        if item is None:
            continue

        relative = str(item.get("path", "")).strip()
        expected = str(
            item.get("sha256", "")
        ).strip().lower()

        if not relative:
            errors.append(f"{kind}:missing_path")
            continue

        if (
            len(expected) != 64
            or any(
                ch not in "0123456789abcdef"
                for ch in expected
            )
        ):
            errors.append(f"{kind}:invalid_sha256")
            continue

        try:
            path = safe_path(root, relative)
        except ValueError as exc:
            errors.append(f"{kind}:{exc}")
            continue

        if not path.is_file():
            errors.append(f"{kind}:missing_file")
            continue

        actual = sha256_file(path)

        if actual != expected:
            errors.append(f"{kind}:hash_mismatch")

        verified[kind] = {
            "path": relative,
            "sha256_expected": expected,
            "sha256_actual": actual,
            "hash_ok": actual == expected,
        }
        resolved[kind] = path

    map_validation = None

    if "antenna_map" in resolved and not errors:
        map_validation = validate_rows(
            load_map_csv(resolved["antenna_map"]),
            load_map_config(map_validation_config),
        )

    if errors:
        status = "INVALID"
    elif map_validation is None:
        status = "INVALID"
        errors.append("map_validation_missing")
    elif map_validation.get("status") != "DATA_READY":
        status = "FAIL"
    elif synthetic:
        status = "TEST_READY"
    elif evidence_level not in REAL_LEVELS:
        status = "HOLD"
    else:
        status = "DATA_READY"

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "model_id": model_id,
        "model_revision": model_revision,
        "solver_name": solver_name,
        "solver_version": solver_version,
        "synthetic_fixture": synthetic,
        "evidence_level": evidence_level,
        "errors": errors,
        "verified_artifacts": verified,
        "map_validation": map_validation,
        "notes": [
            "No production Tx/Rx physical coordinates are encoded by this evidence contract.",
            "TEST_READY is synthetic CI only.",
            "DATA_READY requires real solver/model/material/map artifacts and a real simulation evidence level.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate D1 EM solver/model/material/map provenance"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--map-config", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = evaluate_em_evidence(
        manifest=load_json(args.manifest),
        map_validation_config=args.map_config,
        repository_root=args.repository_root,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {
        "TEST_READY",
        "DATA_READY",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
