from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.measurement_pack import PACKS


BUNDLE_SCHEMA = "EXTERNAL-EVIDENCE-BUNDLE-001"
RESULT_SCHEMA = "EXTERNAL-EVIDENCE-INGEST-RESULT-001"
CLAIM_SCHEMA = "MEASURED-EVIDENCE-CLAIM-001"


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
            f"path escapes bundle root:{relative}"
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


def _scan_placeholders(path: Path) -> bool:
    if path.suffix.lower() not in {".json", ".csv", ".txt", ".md"}:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return "<FILL" in text


def ingest_bundle(
    bundle: dict,
    *,
    bundle_root: str | Path,
) -> tuple[dict, dict | None]:
    root = Path(bundle_root)
    errors: list[str] = []

    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected external evidence bundle schema")

    kind = str(bundle.get("kind", "")).strip()
    if kind not in PACKS:
        errors.append("unsupported_kind")
        spec = None
    else:
        spec = PACKS[kind]

    item_id = str(bundle.get("item_id", "")).strip()
    evidence_level = str(
        bundle.get("evidence_level", "")
    ).strip()

    if spec is not None:
        if item_id != spec["item_id"]:
            errors.append("item_id_mismatch")
        if evidence_level != spec["evidence_level"]:
            errors.append("evidence_level_mismatch")

    if bundle.get("synthetic") is not False:
        errors.append("synthetic_not_explicitly_false")

    result_entry = bundle.get("result")
    if not isinstance(result_entry, dict):
        errors.append("missing_result")
        result_entry = {}

    result_rel = str(result_entry.get("path", "")).strip()
    result_schema = str(
        result_entry.get("schema", "")
    ).strip()

    if spec is not None and result_schema != spec["result_schema"]:
        errors.append("result_schema_mismatch")

    result_path: Path | None = None
    result_data: dict | None = None

    if not result_rel:
        errors.append("result_missing_path")
    else:
        try:
            result_path = safe_path(root, result_rel)
        except ValueError as exc:
            errors.append(str(exc))

    if result_path is not None:
        if not result_path.is_file():
            errors.append("result_missing_file")
        else:
            if _scan_placeholders(result_path):
                errors.append("result_contains_placeholder")
            try:
                result_data = load_json(result_path)
            except (OSError, json.JSONDecodeError):
                errors.append("result_invalid_json")

    if result_data is not None:
        if result_data.get("schema") != result_schema:
            errors.append("result_embedded_schema_mismatch")
        for marker in sorted(set(_fixture_markers(result_data))):
            errors.append(f"result_fixture_marker:{marker}")

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("missing_artifacts")
        artifacts = []

    verified = []
    for index, entry in enumerate(artifacts):
        if not isinstance(entry, dict):
            errors.append(f"artifact_invalid:{index}")
            continue

        kind_name = str(entry.get("kind", "")).strip()
        relative = str(entry.get("path", "")).strip()

        if not kind_name:
            errors.append(f"artifact_missing_kind:{index}")
        if not relative:
            errors.append(f"artifact_missing_path:{index}")
            continue

        try:
            path = safe_path(root, relative)
        except ValueError as exc:
            errors.append(f"artifact:{index}:{exc}")
            continue

        if not path.is_file():
            errors.append(f"artifact_missing_file:{index}")
            continue

        if _scan_placeholders(path):
            errors.append(f"artifact_contains_placeholder:{index}")

        if path.suffix.lower() == ".json":
            try:
                data = load_json(path)
            except (OSError, json.JSONDecodeError):
                errors.append(f"artifact_invalid_json:{index}")
                data = None
            if data is not None:
                for marker in sorted(set(_fixture_markers(data))):
                    errors.append(
                        f"artifact_fixture_marker:{index}:{marker}"
                    )

        verified.append(
            {
                "kind": kind_name,
                "path": relative,
                "sha256": sha256_file(path),
            }
        )

    claim = None
    if not errors and result_path is not None:
        claim = {
            "schema": CLAIM_SCHEMA,
            "item_id": item_id,
            "result": {
                "path": result_rel,
                "sha256": sha256_file(result_path),
                "schema": result_schema,
            },
            "provenance": {
                "evidence_level": evidence_level,
                "synthetic": False,
                "artifacts": verified,
            },
        }

    result = {
        "schema": RESULT_SCHEMA,
        "status": "CANDIDATE_READY" if claim is not None else "REJECTED",
        "kind": kind,
        "item_id": item_id,
        "errors": sorted(set(errors)),
        "verified_artifacts": verified,
        "notes": [
            (
                "CANDIDATE_READY means bundle integrity passed; "
                "domain validation and tools.evidence_promote are still required."
            ),
            (
                "This tool does not update the authoritative project evidence manifest."
            ),
        ],
    }
    return result, claim


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest an external measurement bundle into a candidate evidence claim"
    )
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--output-result", required=True)
    parser.add_argument("--output-claim", required=True)
    args = parser.parse_args()

    result, claim = ingest_bundle(
        load_json(args.bundle),
        bundle_root=args.bundle_root,
    )

    Path(args.output_result).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if claim is not None:
        Path(args.output_claim).write_text(
            json.dumps(claim, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(result["status"])
    return 0 if claim is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
