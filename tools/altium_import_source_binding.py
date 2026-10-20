from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-IMPORT-SOURCE-BINDING-001"
PACKAGE_SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: object) -> Path | None:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return None
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def validate(
    *,
    package_manifest: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    manifest_path = Path(package_manifest)
    root = Path(repository_root)
    errors: list[str] = []

    if not manifest_path.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": ["missing_package_manifest"],
            "checked_count": 0,
            "bindings": [],
        }

    try:
        package = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"package_manifest_parse:{exc}"],
            "checked_count": 0,
            "bindings": [],
        }

    if package.get("schema") != PACKAGE_SCHEMA:
        errors.append("package_manifest_schema")
    if package.get("current_source_binding_required") is not True:
        errors.append("current_source_binding_not_required")

    files_raw = package.get("files")
    if not isinstance(files_raw, list):
        errors.append("package_files")
        files_raw = []

    file_records: dict[str, dict] = {}
    for index, item in enumerate(files_raw):
        if not isinstance(item, dict):
            errors.append(f"package_file_record:{index}")
            continue
        package_path = str(item.get("path", "")).strip().replace("\\", "/")
        if not package_path:
            errors.append(f"package_file_path:{index}")
            continue
        if package_path in file_records:
            errors.append(f"package_file_duplicate:{package_path}")
            continue
        file_records[package_path] = item

    bindings_raw = package.get("source_bindings")
    if not isinstance(bindings_raw, list):
        errors.append("source_bindings")
        bindings_raw = []

    expected_count = package.get("source_binding_count")
    if expected_count != len(bindings_raw):
        errors.append("source_binding_count")
    if not bindings_raw:
        errors.append("source_bindings_empty")

    seen_package: set[str] = set()
    seen_repository: set[str] = set()
    checked: list[dict] = []

    for index, item in enumerate(bindings_raw):
        if not isinstance(item, dict):
            errors.append(f"source_binding_record:{index}")
            continue

        package_rel = safe_relative_path(item.get("package_path"))
        repo_rel = safe_relative_path(item.get("repository_path"))
        if package_rel is None:
            errors.append(f"source_binding_package_path:{index}")
            continue
        if repo_rel is None:
            errors.append(f"source_binding_repository_path:{index}")
            continue

        package_key = package_rel.as_posix()
        repo_key = repo_rel.as_posix()
        if package_key in seen_package:
            errors.append(f"source_binding_duplicate_package:{package_key}")
        if repo_key in seen_repository:
            errors.append(f"source_binding_duplicate_repository:{repo_key}")
        seen_package.add(package_key)
        seen_repository.add(repo_key)

        record = file_records.get(package_key)
        if not isinstance(record, dict):
            errors.append(f"source_binding_missing_package_file:{package_key}")
            continue

        claimed_hash = str(record.get("sha256", "")).strip().lower()
        claimed_size = record.get("size")
        source_path = root / repo_rel
        if not source_path.is_file():
            errors.append(f"source_binding_missing_repository_file:{repo_key}")
            continue

        current_hash = sha256_file(source_path)
        current_size = source_path.stat().st_size
        hash_ok = len(claimed_hash) == 64 and claimed_hash == current_hash
        size_ok = isinstance(claimed_size, int) and claimed_size == current_size

        if not hash_ok:
            errors.append(f"source_binding_hash:{repo_key}")
        if not size_ok:
            errors.append(f"source_binding_size:{repo_key}")

        checked.append(
            {
                "package_path": package_key,
                "repository_path": repo_key,
                "package_sha256": claimed_hash,
                "current_sha256": current_hash,
                "package_size": claimed_size,
                "current_size": current_size,
                "match": hash_ok and size_ok,
            }
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "package_manifest_sha256": sha256_file(manifest_path),
        "source_commit": package.get("source_commit"),
        "expected_count": len(bindings_raw),
        "checked_count": len(checked),
        "bindings": checked,
        "notes": [
            (
                "PASS proves that every source-binding entry in the verified "
                "Altium import package still matches the current repository "
                "checkout byte-for-byte at import-receipt time."
            ),
            (
                "This content binding is stronger than requiring an exact Git "
                "commit hash after squash/rebase, while still rejecting stale "
                "artifacts after an electrical or mechanical source ECO."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-manifest", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        package_manifest=args.package_manifest,
        repository_root=args.repository_root,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
