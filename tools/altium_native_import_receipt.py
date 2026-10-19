from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-IMPORT-RECEIPT-001"
PACKAGE_SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"

NATIVE_ARTIFACTS = {
    "schematic": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc",
    "pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
    "import_log": "hardware/system_carrier/altium/equivalence/import_log.txt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_receipt(
    *,
    repository_root: str | Path,
    package_manifest: str | Path,
    altium_version: str,
    importer_version: str,
) -> dict:
    root = Path(repository_root)
    package_path = Path(package_manifest)
    if not package_path.is_absolute():
        package_path = root / package_path

    errors: list[str] = []

    if not package_path.is_file():
        errors.append("missing_import_package_manifest")
        package = {}
    else:
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_package_manifest_parse:{exc}")
            package = {}

    if package:
        if package.get("schema") != PACKAGE_SCHEMA:
            errors.append("import_package_schema")
        if package.get("status") != "READY_FOR_ALTIUM_IMPORT":
            errors.append("import_package_status")
        if package.get("board_id") != "EVT-SYS-CARRIER":
            errors.append("board_id")
        if package.get("hardware_revision") != "A":
            errors.append("hardware_revision")
        if package.get("target_cad") != "Altium Designer":
            errors.append("target_cad")
        if package.get("preserve_kicad") is not True:
            errors.append("preserve_kicad")

    source_commit = str(package.get("source_commit", "")).strip()
    if source_commit and not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
        errors.append("source_commit")

    altium_version = altium_version.strip()
    importer_version = importer_version.strip()
    if not altium_version:
        errors.append("altium_version")
    if not importer_version:
        errors.append("importer_version")

    artifacts: dict[str, dict] = {}
    for artifact_id, relative in NATIVE_ARTIFACTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
            continue
        artifacts[artifact_id] = {
            "path": relative,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    package_record = None
    if package_path.is_file():
        try:
            package_relative = _repo_relative(root, package_path)
        except ValueError:
            errors.append("import_package_manifest_outside_repository")
        else:
            package_record = {
                "path": package_relative,
                "size": package_path.stat().st_size,
                "sha256": sha256_file(package_path),
            }

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "source_commit": source_commit,
        "source_cad": package.get("source_cad"),
        "target_cad": package.get("target_cad"),
        "import_mechanism": "KiCad Importer / Import Wizard",
        "altium_version": altium_version,
        "importer_version": importer_version,
        "import_package_manifest": package_record,
        "native_artifacts": artifacts,
        "errors": sorted(set(errors)),
        "layout_authority": "NOT_AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "This receipt records the exact native files, import log and "
                "CI import package used for the Altium conversion."
            ),
            (
                "A PASS receipt is provenance evidence only; layout authority "
                "still requires ALTIUM_EQUIVALENCE_GATE PASS."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--package-manifest", required=True)
    parser.add_argument("--altium-version", required=True)
    parser.add_argument("--importer-version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = build_receipt(
        repository_root=args.repository_root,
        package_manifest=args.package_manifest,
        altium_version=args.altium_version,
        importer_version=args.importer_version,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
