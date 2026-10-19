from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath

from tools.altium_native_file_preflight import inspect_cfb


SCHEMA = "ALTIUM-PROJECT-MEMBERSHIP-001"


def sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


DOCUMENT_PATH_RE = re.compile(
    r"^\s*DocumentPath\s*=\s*(.*?)\s*$",
    re.IGNORECASE,
)


def _normalize_project_path(value: str) -> str:
    text = value.strip().strip('"').replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return PurePosixPath(text).as_posix()


def expected_documents(profile: dict) -> list[str]:
    source = profile.get("source")
    target = profile.get("target")
    if not isinstance(source, dict) or not isinstance(target, dict):
        raise ValueError("import profile missing source/target")

    root_schematic = _normalize_project_path(
        str(target.get("schematic", ""))
    )
    pcb = _normalize_project_path(
        str(target.get("pcb", ""))
    )
    if not root_schematic or not pcb:
        raise ValueError("import profile target documents missing")

    target_children = target.get("child_sheets")
    children: list[str] = []
    if isinstance(target_children, list) and target_children:
        children = [
            _normalize_project_path(str(item))
            for item in target_children
        ]
    else:
        native_dir = PurePosixPath(root_schematic).parent
        child_sheets = source.get("child_sheets")
        if not isinstance(child_sheets, list):
            raise ValueError("import profile child_sheets must be a list")
        for item in child_sheets:
            source_name = PurePosixPath(str(item)).name
            if not source_name.endswith(".kicad_sch"):
                raise ValueError(
                    f"unexpected child sheet extension: {source_name}"
                )
            native_name = (
                source_name[: -len(".kicad_sch")] + ".SchDoc"
            )
            children.append(
                (native_dir / native_name).as_posix()
            )

    if len(children) != 7:
        raise ValueError(
            f"expected seven native child SchDocs, got {len(children)}"
        )

    return [root_schematic, *children, pcb]


def parse_document_paths(project_path: Path) -> list[str]:
    text = project_path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )
    paths: list[str] = []
    for line in text.splitlines():
        match = DOCUMENT_PATH_RE.match(line)
        if match:
            value = _normalize_project_path(match.group(1))
            if value:
                paths.append(value)
    return paths


def validate(
    *,
    project: str | Path,
    import_profile: str | Path,
) -> dict:
    project_path = Path(project)
    profile_path = Path(import_profile)
    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (project_path, "project"),
        (profile_path, "import_profile"),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    try:
        profile = json.loads(
            profile_path.read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"import_profile_parse:{exc}"],
            "warnings": warnings,
        }

    if profile.get("schema") != "ALTIUM-IMPORT-PROFILE-SYS-001":
        errors.append("import_profile_schema")

    try:
        expected = expected_documents(profile)
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"import_profile:{exc}"],
            "warnings": warnings,
        }

    try:
        actual = parse_document_paths(project_path)
    except UnicodeDecodeError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"project_decode:{exc}"],
            "warnings": warnings,
        }

    counts: dict[str, int] = {}
    for item in actual:
        key = item.casefold()
        counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(
        item
        for item, count in counts.items()
        if count > 1
    )
    if duplicates:
        errors.append(
            "duplicate_document_paths:" + ",".join(duplicates)
        )

    actual_lookup = {
        item.casefold(): item
        for item in actual
    }

    missing_membership = [
        item
        for item in expected
        if item.casefold() not in actual_lookup
    ]
    if missing_membership:
        errors.append(
            "missing_project_documents:"
            + ",".join(missing_membership)
        )

    project_dir = project_path.parent
    document_results: dict[str, dict] = {}
    for expected_path in expected:
        full_path = project_dir / Path(expected_path)
        suffix = Path(expected_path).suffix

        if suffix not in {".SchDoc", ".PcbDoc"}:
            errors.append(
                f"unexpected_native_suffix:{expected_path}"
            )
            continue

        result = inspect_cfb(
            full_path,
            expected_suffix=suffix,
        )
        document_results[expected_path] = result

        if result.get("status") != "PASS":
            for error in result.get("errors", []):
                errors.append(
                    f"native_document:{expected_path}:{error}"
                )

    expected_set = {
        item.casefold()
        for item in expected
    }
    extra_native = sorted(
        item
        for item in actual
        if (
            Path(item).suffix in {".SchDoc", ".PcbDoc"}
            and item.casefold() not in expected_set
        )
    )
    if extra_native:
        warnings.append(
            "extra_native_project_documents:"
            + ",".join(extra_native)
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "project": project_path.as_posix(),
        "expected_document_count": len(expected),
        "project_document_count": len(actual),
        "expected_documents": expected,
        "project_documents": actual,
        "document_results": document_results,
        "input_sha256": {
            "project": sha256_file(project_path),
            "import_profile": sha256_file(profile_path),
            "documents": {
                item: document_results[item]["sha256"]
                for item in expected
                if item in document_results
                and document_results[item].get("status") == "PASS"
            },
        },
        "verified_checks": {
            "native_project_membership": status,
        },
        "notes": [
            (
                "PASS requires the root SchDoc, all seven numbered child "
                "SchDocs and the PcbDoc to be explicit PrjPcb members."
            ),
            (
                "Every required native document must independently pass "
                "the CFB/OLE container preflight."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--import-profile", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        project=args.project,
        import_profile=args.import_profile,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
