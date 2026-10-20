from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-IMPORT-PACKAGE-VERIFY-001"
PACKAGE_SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha256(value: object) -> bool:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return False
    try:
        int(text, 16)
    except ValueError:
        return False
    return True


def verify(
    *,
    package_root: str | Path,
    manifest_path: str | Path | None = None,
) -> dict:
    root = Path(package_root)
    manifest = (
        Path(manifest_path)
        if manifest_path is not None
        else root / "manifest.json"
    )

    errors: list[str] = []
    verified_files: list[dict] = []

    if not root.is_dir():
        errors.append("missing_package_root")
    if not manifest.is_file():
        errors.append("missing_manifest")

    payload: dict = {}
    if not errors:
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"manifest_parse:{exc}")

    if payload:
        if payload.get("schema") != PACKAGE_SCHEMA:
            errors.append("manifest_schema")
        if payload.get("status") != "READY_FOR_ALTIUM_IMPORT":
            errors.append("manifest_status")
        if payload.get("path_mode") != "PACKAGE_ROOT_RELATIVE":
            errors.append("manifest_path_mode")

    files = payload.get("files") if isinstance(payload, dict) else None
    if payload and not isinstance(files, list):
        errors.append("manifest_files")
        files = []
    elif not isinstance(files, list):
        files = []

    expected_count = payload.get("file_count")
    if payload and expected_count != len(files):
        errors.append("manifest_file_count")

    seen: set[str] = set()
    root_resolved = root.resolve() if root.exists() else root.absolute()

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"file_record:{index}")
            continue

        relative = str(item.get("path", "")).strip().replace("\\", "/")
        if not relative:
            errors.append(f"file_path:{index}")
            continue
        if relative in seen:
            errors.append(f"duplicate_path:{relative}")
            continue
        seen.add(relative)

        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"unsafe_path:{relative}")
            continue

        path = (root / rel).resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError:
            errors.append(f"path_escape:{relative}")
            continue

        if not path.is_file():
            errors.append(f"missing_file:{relative}")
            continue

        claimed_hash = str(item.get("sha256", "")).strip().lower()
        actual_hash = sha256_file(path)
        if not valid_sha256(claimed_hash):
            errors.append(f"invalid_sha256:{relative}")
        elif claimed_hash != actual_hash:
            errors.append(f"sha256_mismatch:{relative}")

        claimed_size = item.get("size")
        actual_size = path.stat().st_size
        if not isinstance(claimed_size, int) or claimed_size < 0:
            errors.append(f"invalid_size:{relative}")
        elif claimed_size != actual_size:
            errors.append(f"size_mismatch:{relative}")

        verified_files.append(
            {
                "path": relative,
                "size": actual_size,
                "sha256": actual_hash,
            }
        )

    manifest_hash = sha256_file(manifest) if manifest.is_file() else ""
    status = "PASS" if not errors else "FAIL"

    return {
        "schema": SCHEMA,
        "status": status,
        "board_id": payload.get("board_id"),
        "hardware_revision": payload.get("hardware_revision"),
        "source_commit": payload.get("source_commit"),
        "package_manifest": {
            "path": "manifest.json",
            "sha256": manifest_hash,
        },
        "expected_file_count": len(files),
        "verified_file_count": len(verified_files),
        "verified_files": verified_files,
        "errors": sorted(set(errors)),
        "notes": [
            (
                "PASS means every manifest-listed import-package file exists "
                "under package_root and matches its recorded SHA-256 and size."
            ),
            (
                "Run this verifier again after downloading/extracting the CI "
                "artifact and before opening the source in Altium Designer."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = verify(
        package_root=args.package_root,
        manifest_path=args.manifest,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
