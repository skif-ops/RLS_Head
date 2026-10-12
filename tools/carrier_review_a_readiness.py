from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-REVIEW-A-READINESS-001"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def evaluate(
    *,
    repository_root: str | Path,
    scaffold_manifest: str | Path,
) -> dict:
    repo = Path(repository_root)
    manifest_path = Path(scaffold_manifest)

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    errors: list[str] = []
    warnings: list[str] = []

    if (
        manifest.get("schema")
        != "SYSTEM-CARRIER-CAD-SCAFFOLD-001"
    ):
        errors.append("scaffold_manifest_schema")

    child_sheets = manifest.get(
        "child_sheets",
        [],
    )
    if (
        not isinstance(child_sheets, list)
        or len(child_sheets) != 7
    ):
        errors.append("child_sheet_count")

    placeholders = manifest.get(
        "symbol_placeholders",
        [],
    )

    if not isinstance(placeholders, list):
        errors.append("symbol_placeholders_not_list")
        placeholders = []

    if placeholders:
        for item in placeholders:
            if not isinstance(item, dict):
                errors.append("invalid_symbol_placeholder")
                continue

            ref = str(
                item.get("reference", "")
            ).strip()
            value = str(
                item.get("value", "")
            ).strip()

            errors.append(
                f"symbol_placeholder:{ref}:{value}"
            )

    blockers_path = (
        repo
        / "hardware"
        / "system_carrier"
        / "EXTERNAL_DOCUMENT_BLOCKERS_SYS_001.csv"
    )

    if not blockers_path.is_file():
        errors.append(
            "missing_external_document_blockers"
        )
        open_blockers = []
    else:
        rows = _read_csv(blockers_path)
        open_blockers = [
            row
            for row in rows
            if str(
                row.get("status", "")
            ).strip()
            != "CLOSED"
        ]

        for row in open_blockers:
            errors.append(
                "external_document_blocker:"
                + str(
                    row.get(
                        "blocker_id",
                        "",
                    )
                ).strip()
            )

    footprint_path = (
        repo
        / "hardware"
        / "system_carrier"
        / "FOOTPRINT_PLAN_SYS_001.csv"
    )

    if not footprint_path.is_file():
        errors.append("missing_footprint_plan")
        footprint_rows = []
    else:
        footprint_rows = _read_csv(
            footprint_path
        )

    unresolved_footprints = [
        row
        for row in footprint_rows
        if str(
            row.get("status", "")
        ).strip()
        != "LOCKED"
    ]

    for row in unresolved_footprints:
        warnings.append(
            "footprint_not_locked:"
            + str(
                row.get("ref", "")
            ).strip()
            + ":"
            + str(
                row.get("mpn", "")
            ).strip()
        )

    status = (
        "READY_FOR_REVIEW_A"
        if not errors
        else "BLOCKED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(
            set(errors)
        ),
        "warnings": sorted(
            set(warnings)
        ),
        "placeholder_count": len(
            placeholders
        ),
        "open_external_blocker_count":
            len(open_blockers),
        "unresolved_footprint_count":
            len(unresolved_footprints),
        "sheet_count":
            1 + len(child_sheets),
        "notes": [
            (
                "READY_FOR_REVIEW_A is a precondition only; "
                "it does not close CARRIER_REVIEW_A."
            ),
            (
                "KiCad generation/ERC/parsing remain the "
                "responsibility of the dedicated CAD CI job."
            ),
            (
                "External connector pinouts and package/footprint data "
                "must never be guessed to force readiness."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate System Carrier readiness "
            "for real Review A"
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--scaffold-manifest",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = evaluate(
        repository_root=
            args.repository_root,
        scaffold_manifest=
            args.scaffold_manifest,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        result["status"]
    )
    return (
        0
        if result["status"]
        == "READY_FOR_REVIEW_A"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
