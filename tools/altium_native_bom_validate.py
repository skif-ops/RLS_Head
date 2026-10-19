from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-BOM-RESULT-001"

DESIGNATOR_HEADERS = (
    "designator",
    "designators",
)
MPN_HEADERS = (
    "mpn",
    "manufacturer part number",
    "manufacturer part number 1",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _find_header(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    by_norm = {_norm_header(name): name for name in fieldnames}
    for candidate in candidates:
        found = by_norm.get(_norm_header(candidate))
        if found is not None:
            return found
    return None


def _split_designators(value: str) -> list[str]:
    return [
        item
        for item in re.split(r"[,;\s]+", value.strip())
        if item
    ]


def validate(
    *,
    system_root: str | Path,
    bom_export: str | Path,
) -> dict:
    system = Path(system_root)
    export_path = Path(bom_export)
    contract_path = system / "BOM_SYS_CARRIER_LAYOUT_004.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (contract_path, "bom_contract"),
        (export_path, "bom_export"),
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

    with contract_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        contract_rows = list(csv.DictReader(handle))

    expected: dict[str, str] = {}
    duplicate_contract: list[str] = []
    for row in contract_rows:
        ref = str(row.get("ref", "")).strip()
        mpn = str(row.get("value_or_mpn", "")).strip()
        if not ref:
            continue
        if ref in expected:
            duplicate_contract.append(ref)
        expected[ref] = mpn

    if duplicate_contract:
        errors.append(
            "duplicate_contract_designator:"
            + ",".join(sorted(set(duplicate_contract)))
        )

    with export_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            errors.append("bom_export_header")
            rows: list[dict[str, str]] = []
            designator_header = None
            mpn_header = None
        else:
            designator_header = _find_header(
                reader.fieldnames,
                DESIGNATOR_HEADERS,
            )
            mpn_header = _find_header(
                reader.fieldnames,
                MPN_HEADERS,
            )
            rows = list(reader)

    if designator_header is None:
        errors.append("bom_export_designator_column")
    if mpn_header is None:
        errors.append("bom_export_mpn_column")

    actual: dict[str, str] = {}
    duplicate_actual: list[str] = []
    conflicting_actual: list[str] = []

    if designator_header is not None and mpn_header is not None:
        for row in rows:
            raw_designators = str(
                row.get(designator_header, "")
            ).strip()
            mpn = str(row.get(mpn_header, "")).strip()
            for ref in _split_designators(raw_designators):
                previous = actual.get(ref)
                if previous is not None:
                    duplicate_actual.append(ref)
                    if previous != mpn:
                        conflicting_actual.append(
                            f"{ref}:{previous}|{mpn}"
                        )
                actual[ref] = mpn

    if duplicate_actual:
        warnings.append(
            "duplicate_export_designator:"
            + ",".join(sorted(set(duplicate_actual)))
        )
    if conflicting_actual:
        errors.append(
            "conflicting_export_mpn:"
            + ",".join(sorted(set(conflicting_actual)))
        )

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatch = sorted(
        f"{ref}:{expected[ref]}!={actual[ref]}"
        for ref in set(expected) & set(actual)
        if expected[ref] != actual[ref]
    )

    if missing:
        errors.append("missing_designators:" + ",".join(missing))
    if extra:
        errors.append("extra_designators:" + ",".join(extra))
    if mismatch:
        errors.append("mpn_mismatch:" + ",".join(mismatch))

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "expected_designator_count": len(expected),
        "actual_designator_count": len(actual),
        "input_sha256": {
            "bom_export": sha256_file(export_path),
            "bom_contract": sha256_file(contract_path),
        },
        "verified_checks": {
            "bom_designator_mpn_equivalence": (
                "PASS" if not errors else "FAIL"
            ),
        },
        "notes": [
            (
                "The native Altium BOM export must contain Designator(s) "
                "and MPN/Manufacturer Part Number columns."
            ),
            (
                "Grouped designator cells are expanded before exact "
                "designator-to-MPN comparison."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--bom-export", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        bom_export=args.bom_export,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
