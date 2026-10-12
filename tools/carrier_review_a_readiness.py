from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import kicad_sch_api as ksa

from tools.generate_system_carrier_schematic import build


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
    generated_dir: str | Path,
) -> dict:
    repo = Path(repository_root)
    out = Path(generated_dir)

    build(out)

    manifest = json.loads(
        (out / "cad_scaffold_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    blockers_path = (
        repo
        / "hardware"
        / "system_carrier"
        / "EXTERNAL_DOCUMENT_BLOCKERS_SYS_001.csv"
    )

    footprint_path = (
        repo
        / "hardware"
        / "system_carrier"
        / "FOOTPRINT_PLAN_SYS_001.csv"
    )

    errors: list[str] = []
    warnings: list[str] = []

    placeholders = manifest.get(
        "symbol_placeholders",
        []
    )

    if placeholders:
        for item in placeholders:
            ref = str(item.get("reference", "")).strip()
            value = str(item.get("value", "")).strip()
            errors.append(
                f"symbol_placeholder:{ref}:{value}"
            )

    if not blockers_path.is_file():
        errors.append("missing_external_document_blockers")
        open_blockers = []
    else:
        rows = _read_csv(blockers_path)
        open_blockers = [
            row
            for row in rows
            if str(row.get("status", "")).strip() != "CLOSED"
        ]
        for row in open_blockers:
            errors.append(
                "external_document_blocker:"
                + str(row.get("blocker_id", "")).strip()
            )

    if not footprint_path.is_file():
        errors.append("missing_footprint_plan")
        footprint_rows = []
    else:
        footprint_rows = _read_csv(footprint_path)

    unresolved_footprints = [
        row
        for row in footprint_rows
        if str(row.get("status", "")).strip()
        not in {"LOCKED"}
    ]

    for row in unresolved_footprints:
        warnings.append(
            "footprint_not_locked:"
            + str(row.get("ref", "")).strip()
            + ":"
            + str(row.get("mpn", "")).strip()
        )

    parsed = []
    for name in [
        "EVT_SYS_CARRIER.kicad_sch",
        *manifest.get("child_sheets", []),
    ]:
        path = out / name
        try:
            ksa.load_schematic(str(path))
        except Exception as exc:
            errors.append(
                f"schematic_parse:{name}:{type(exc).__name__}"
            )
        else:
            parsed.append(name)

    status = (
        "READY_FOR_REVIEW_A"
        if not errors
        else "BLOCKED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "placeholder_count": len(placeholders),
        "open_external_blocker_count": len(open_blockers),
        "unresolved_footprint_count": len(unresolved_footprints),
        "parsed_schematic_count": len(parsed),
        "notes": [
            (
                "READY_FOR_REVIEW_A is a precondition only; "
                "it does not close CARRIER_REVIEW_A."
            ),
            (
                "External connector pinouts and package/footprint data "
                "must never be guessed to force readiness."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate System Carrier readiness for real Review A"
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(
        repository_root=args.repository_root,
        generated_dir=args.generated_dir,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    return 0 if result["status"] == "READY_FOR_REVIEW_A" else 2


if __name__ == "__main__":
    raise SystemExit(main())
