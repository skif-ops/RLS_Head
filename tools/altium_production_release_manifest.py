from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001"


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
