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
OUTPUT_KINDS = {
    "solver_export",
    "antenna_map",
}
REAL_LEVELS = {
    "SIMULATED_EM",
    "SIMULATED_EM_CORRELATED",
    "MEASURED_EM",
}


def _filled(value: object) -> bool:
    if not isinstance(value, str):
        return bool(value)
    text = value.strip()
    return bool(text) and "<FILL" not in text


def _safe_relative(path_text: str) -> bool:
    path = Path(path_text)
    return (
        bool(path_text.strip())
        and not path.is_absolute()
        and ".." not in path.parts
    )


def evaluate_preflight(
    *,
    manifest: dict,
    repository_root: str | Path,
    map_config: str | Path,
) -> dict:
    root = Path(repository_root)
    errors: list[str] = []
    warnings: list[str] = []

    if manifest.get("schema") != "ANT-D1-EM-MANIFEST-001":
        errors.append("manifest_schema")

    for field in (
        "model_id",
        "model_revision",
        "solver_name",
        "solver_version",
    ):
        if not _filled(manifest.get(field)):
            errors.append(f"missing_or_placeholder:{field}")

    if manifest.get("synthetic_fixture") is not False:
        errors.append("synthetic_fixture_not_false")

    if manifest.get("evidence_level") not in REAL_LEVELS:
        errors.append("unsupported_evidence_level")

    artifacts_raw = manifest.get("artifacts")
    if not isinstance(artifacts_raw, list):
        errors.append("artifacts_not_list")
        artifacts_raw = []

    artifacts: dict[str, dict] = {}
    for index, entry in enumerate(artifacts_raw):
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

    for kind, entry in artifacts.items():
        if kind not in REQUIRED_KINDS:
            continue

        relative = str(entry.get("path", "")).strip()
        if not _safe_relative(relative):
            errors.append(f"unsafe_or_missing_path:{kind}")
            continue

        path = root / relative

        if kind in INPUT_KINDS:
            if not path.is_file():
                errors.append(f"missing_input_file:{kind}")
        elif kind in OUTPUT_KINDS:
            if not path.is_file():
                warnings.append(f"output_not_generated_yet:{kind}")

    cfg_path = Path(map_config)
    if not cfg_path.is_file():
        errors.append("map_config_missing")
    else:
        try:
            cfg = json.loads(
                cfg_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            errors.append("map_config_invalid_json")
        else:
            if not isinstance(cfg, dict):
                errors.append("map_config_not_object")

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
        "notes": [
            (
                "READY_FOR_SOLVER_EXECUTION means provenance inputs and "
                "paths are structurally ready; solver outputs may still be absent."
            ),
            (
                "This preflight does not validate EM performance and does not "
                "encode or freeze production Tx/Rx coordinates."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a D1 EM external solver evidence package"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--map-config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(
        Path(args.manifest).read_text(encoding="utf-8")
    )

    result = evaluate_preflight(
        manifest=manifest,
        repository_root=args.repository_root,
        map_config=args.map_config,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY_FOR_SOLVER_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
