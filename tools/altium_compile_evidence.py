from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-COMPILE-REPORT-001"

PROJECT_REL = Path(
    "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb"
)
SCHEMATIC_REL = Path(
    "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build(
    *,
    repository_root: str | Path,
    raw_report: str | Path,
    errors: int,
    warnings: int,
) -> dict:
    root = Path(repository_root)
    raw = Path(raw_report)
    if not raw.is_absolute():
        raw = root / raw

    project = root / PROJECT_REL
    schematic = root / SCHEMATIC_REL

    build_errors: list[str] = []
    for label, path in (
        ("raw_report", raw),
        ("project", project),
        ("schematic", schematic),
    ):
        if not path.is_file():
            build_errors.append(f"missing:{label}")

    try:
        error_count = int(errors)
        warning_count = int(warnings)
    except (TypeError, ValueError):
        build_errors.append("compile_counts")
        error_count = -1
        warning_count = -1

    if error_count < 0:
        build_errors.append("errors_negative")
    if warning_count < 0:
        build_errors.append("warnings_negative")

    if build_errors:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": sorted(set(build_errors)),
            "warnings": -1,
        }

    try:
        raw_relative = _repo_relative(root, raw)
    except ValueError:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": ["raw_report_outside_repository"],
            "warnings": warning_count,
        }

    status = (
        "PASS"
        if error_count == 0 and warning_count == 0
        else "FAIL"
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": error_count,
        "warnings": warning_count,
        "source_report": raw_relative,
        "source_report_sha256": sha256_file(raw),
        "source_project": PROJECT_REL.as_posix(),
        "source_project_sha256": sha256_file(project),
        "source_schematic": SCHEMATIC_REL.as_posix(),
        "source_schematic_sha256": sha256_file(schematic),
        "layout_authority": "NOT_AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "Counts are recorded from the native Altium compile/ERC "
                "result and cryptographically bound to the archived raw report."
            ),
            (
                "PASS is compile evidence only; layout authority remains "
                "controlled by ALTIUM_EQUIVALENCE_GATE."
            ),
        ],
    }


def validate(
    *,
    compile_report: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    root = Path(repository_root)
    path = Path(compile_report)
    if not path.is_absolute():
        path = root / path

    result = {
        "schema": "ALTIUM-COMPILE-EVIDENCE-VALIDATION-001",
        "status": "FAIL",
        "errors": [],
        "reason_codes": [],
    }
    errors_out: list[str] = []
    reasons: list[str] = []

    if not path.is_file():
        result["errors"] = ["missing_compile_report"]
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result["errors"] = [f"compile_report_parse:{exc}"]
        return result

    if payload.get("schema") != SCHEMA:
        errors_out.append("compile_report_schema")

    try:
        error_count = int(payload.get("errors", -1))
        warning_count = int(payload.get("warnings", -1))
    except (TypeError, ValueError):
        errors_out.append("compile_report_counts")
        error_count = -1
        warning_count = -1

    if error_count != 0:
        reasons.append(f"COMPILE_ERRORS:{error_count}")
    if warning_count != 0:
        reasons.append(f"COMPILE_WARNINGS:{warning_count}")
    if payload.get("status") != "PASS":
        reasons.append("COMPILE_STATUS_NOT_PASS")

    expected = (
        ("source_report", "source_report_sha256", None),
        (
            "source_project",
            "source_project_sha256",
            PROJECT_REL.as_posix(),
        ),
        (
            "source_schematic",
            "source_schematic_sha256",
            SCHEMATIC_REL.as_posix(),
        ),
    )

    hashes: dict[str, str] = {}
    for path_key, hash_key, fixed_path in expected:
        relative = str(payload.get(path_key, "")).strip()
        if fixed_path is not None and relative != fixed_path:
            errors_out.append(f"{path_key}_path")
            continue
        rel = Path(relative)
        if (
            not relative
            or rel.is_absolute()
            or ".." in rel.parts
        ):
            errors_out.append(f"{path_key}_path")
            continue
        source_path = root / rel
        if not source_path.is_file():
            errors_out.append(f"{path_key}_missing")
            continue
        actual_hash = sha256_file(source_path)
        hashes[path_key] = actual_hash
        claimed = str(payload.get(hash_key, "")).strip().lower()
        if len(claimed) != 64 or claimed != actual_hash:
            errors_out.append(f"{path_key}_hash")

    status = (
        "PASS"
        if not errors_out and not reasons
        else ("INVALID" if errors_out else "FAIL")
    )
    return {
        "schema": "ALTIUM-COMPILE-EVIDENCE-VALIDATION-001",
        "status": status,
        "errors": sorted(set(errors_out)),
        "reason_codes": sorted(set(reasons)),
        "compile_report_sha256": sha256_file(path),
        "source_hashes": hashes,
        "compile": payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--repository-root", default=".")
    build_parser.add_argument("--raw-report", required=True)
    build_parser.add_argument("--errors", required=True, type=int)
    build_parser.add_argument("--warnings", required=True, type=int)
    build_parser.add_argument("--output", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--repository-root", default=".")
    validate_parser.add_argument("--compile-report", required=True)
    validate_parser.add_argument("--output", required=True)

    args = parser.parse_args()

    if args.command == "build":
        result = build(
            repository_root=args.repository_root,
            raw_report=args.raw_report,
            errors=args.errors,
            warnings=args.warnings,
        )
    else:
        result = validate(
            compile_report=args.compile_report,
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
