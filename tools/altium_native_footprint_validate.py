from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-FOOTPRINT-RESULT-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _footprint_name(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if ":" in text:
        text = text.rsplit(":", 1)[1]
    if "/" in text:
        text = text.rsplit("/", 1)[1]
    return text.strip()


def validate(
    *,
    system_root: str | Path,
    component_inventory: str | Path,
) -> dict:
    system = Path(system_root)
    inventory_path = Path(component_inventory)
    contract_path = system / "FOOTPRINT_ASSIGNMENT_SYS_002.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (contract_path, "footprint_contract"),
        (inventory_path, "component_inventory"),
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

    expected = {
        str(row.get("ref", "")).strip(): _footprint_name(
            row.get("footprint_id")
        )
        for row in contract_rows
        if str(row.get("ref", "")).strip()
        and str(row.get("status", "")).strip() == "LOCKED"
    }

    with inventory_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        inventory_rows = list(csv.DictReader(handle))

    actual = {
        str(row.get("designator", "")).strip(): _footprint_name(
            row.get("pattern")
        )
        for row in inventory_rows
        if str(row.get("designator", "")).strip()
    }

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatch = sorted(
        f"{ref}:{expected[ref]}!={actual[ref]}"
        for ref in set(expected) & set(actual)
        if expected[ref] != actual[ref]
    )
    blank = sorted(
        ref
        for ref, pattern in actual.items()
        if ref in expected and not pattern
    )

    if missing:
        errors.append("missing_footprint_refs:" + ",".join(missing))
    if extra:
        warnings.append("extra_component_refs:" + ",".join(extra))
    if blank:
        errors.append("blank_footprints:" + ",".join(blank))
    if mismatch:
        errors.append("footprint_mismatch:" + ",".join(mismatch))

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "expected_footprint_count": len(expected),
        "actual_component_count": len(actual),
        "input_sha256": {
            "component_inventory": sha256_file(inventory_path),
            "footprint_contract": sha256_file(contract_path),
        },
        "verified_checks": {
            "footprint_equivalence": (
                "PASS" if not errors else "FAIL"
            ),
        },
        "notes": [
            (
                "Comparison uses the footprint pattern name, stripping "
                "library prefixes such as KiCad library-name:pattern."
            ),
            (
                "IPCB_Component.Pattern is the native PCB footprint name."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--component-inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        component_inventory=args.component_inventory,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
