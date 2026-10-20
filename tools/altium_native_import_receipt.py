from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-IMPORT-RECEIPT-001"
PACKAGE_SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"
PACKAGE_VERIFY_SCHEMA = "ALTIUM-IMPORT-PACKAGE-VERIFY-001"

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
    package_verification: str | Path,
    import_preflight: str | Path,
    altium_version: str,
    importer_version: str,
) -> dict:
    root = Path(repository_root)
    package_path = Path(package_manifest)
    if not package_path.is_absolute():
        package_path = root / package_path

    verification_path = Path(package_verification)
    if not verification_path.is_absolute():
        verification_path = root / verification_path

    preflight_path = Path(import_preflight)
    if not preflight_path.is_absolute():
        preflight_path = root / preflight_path

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

    package_verification_data = None
    if not verification_path.is_file():
        errors.append("missing_import_package_verification")
    else:
        try:
            package_verification_data = json.loads(
                verification_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_package_verification_parse:{exc}")
        else:
            if (
                package_verification_data.get("schema")
                != PACKAGE_VERIFY_SCHEMA
            ):
                errors.append("import_package_verification_schema")
            if package_verification_data.get("status") != "PASS":
                errors.append("import_package_verification_status")
            if package_verification_data.get("errors") not in ([], None):
                errors.append("import_package_verification_errors")

            package_record = package_verification_data.get(
                "package_manifest"
            )
            if not isinstance(package_record, dict):
                errors.append("import_package_verification_manifest_record")
            elif package_path.is_file():
                recorded_hash = str(
                    package_record.get("sha256", "")
                ).strip().lower()
                if recorded_hash != sha256_file(package_path):
                    errors.append(
                        "import_package_verification_manifest_hash"
                    )

            verified_source = str(
                package_verification_data.get("source_commit", "")
            ).strip().lower()
            package_source = str(
                package.get("source_commit", "")
            ).strip().lower()
            if not verified_source or verified_source != package_source:
                errors.append("import_package_verification_source_commit")

            expected_count = package_verification_data.get(
                "expected_file_count"
            )
            verified_count = package_verification_data.get(
                "verified_file_count"
            )
            if (
                not isinstance(expected_count, int)
                or not isinstance(verified_count, int)
                or expected_count != verified_count
                or expected_count != package.get("file_count")
            ):
                errors.append("import_package_verification_file_count")

    source_commit = str(package.get("source_commit", "")).strip()
    if source_commit and not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
        errors.append("source_commit")

    altium_version = altium_version.strip()
    importer_version = importer_version.strip()
    if not altium_version:
        errors.append("altium_version")
    if not importer_version:
        errors.append("importer_version")

    import_preflight = None
    if not preflight_path.is_file():
        errors.append("missing_import_native_file_preflight")
    else:
        try:
            import_preflight = json.loads(
                preflight_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_preflight_parse:{exc}")
        else:
            if (
                import_preflight.get("schema")
                != "ALTIUM-NATIVE-FILE-PREFLIGHT-001"
            ):
                errors.append("import_preflight_schema")
            if import_preflight.get("status") != "PASS":
                errors.append("import_preflight_status")

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

    if isinstance(import_preflight, dict):
        preflight_artifacts = import_preflight.get("artifacts")
        if not isinstance(preflight_artifacts, dict):
            errors.append("import_preflight_artifacts")
        else:
            for artifact_id in ("schematic", "pcb"):
                record = preflight_artifacts.get(artifact_id)
                current = artifacts.get(artifact_id)
                if not isinstance(record, dict):
                    errors.append(
                        f"import_preflight_record:{artifact_id}"
                    )
                    continue
                if not isinstance(current, dict):
                    continue
                claimed_path = str(record.get("path", "")).strip()
                claimed_hash = str(
                    record.get("sha256", "")
                ).strip().lower()
                if claimed_path != current["path"]:
                    errors.append(
                        f"import_preflight_path:{artifact_id}"
                    )
                if claimed_hash != current["sha256"]:
                    errors.append(
                        f"import_preflight_hash:{artifact_id}"
                    )

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

    package_verification_record = None
    if verification_path.is_file():
        try:
            verification_relative = _repo_relative(root, verification_path)
        except ValueError:
            errors.append("import_package_verification_outside_repository")
        else:
            package_verification_record = {
                "path": verification_relative,
                "size": verification_path.stat().st_size,
                "sha256": sha256_file(verification_path),
            }

    preflight_record = None
    if preflight_path.is_file():
        try:
            preflight_relative = _repo_relative(root, preflight_path)
        except ValueError:
            errors.append("import_preflight_outside_repository")
        else:
            preflight_record = {
                "path": preflight_relative,
                "size": preflight_path.stat().st_size,
                "sha256": sha256_file(preflight_path),
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
        "snapshot_role": "POST_IMPORT_NATIVE_SNAPSHOT",
        "altium_version": altium_version,
        "importer_version": importer_version,
        "import_package_manifest": package_record,
        "import_package_verification": package_verification_record,
        "import_native_file_preflight": preflight_record,
        "native_artifacts": artifacts,
        "errors": sorted(set(errors)),
        "layout_authority": "NOT_AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "This receipt records the import-time native snapshot, import "
                "log and CI import package used for the Altium conversion."
            ),
            (
                "The native SchDoc/PcbDoc may evolve after import while applying "
                "approved pre-routing stack/rule preparation. The later native "
                "file preflight and equivalence manifest bind the actual "
                "pre-routing snapshot used for layout authority."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--package-manifest", required=True)
    parser.add_argument("--package-verification", required=True)
    parser.add_argument("--import-preflight", required=True)
    parser.add_argument("--altium-version", required=True)
    parser.add_argument("--importer-version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = build_receipt(
        repository_root=args.repository_root,
        package_manifest=args.package_manifest,
        package_verification=args.package_verification,
        import_preflight=args.import_preflight,
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
