from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-HIERARCHY-RESULT-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def clean(value: object) -> str:
    return str(value or "").strip()


def normalize_pin_type(value: object) -> str:
    text = clean(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "in": "input",
        "out": "output",
        "bidir": "bidirectional",
        "bi_directional": "bidirectional",
        "bidirectional": "bidirectional",
        "passive": "passive",
        "unspecified": "passive",
    }
    return aliases.get(text, text)


def row_key(row: dict[str, str]) -> tuple[str, str]:
    return (
        clean(row.get("sheet")).upper(),
        clean(row.get("net_name")),
    )


def validate(
    *,
    system_root: str | Path,
    hierarchy_export: str | Path,
    pad_net_inventory: str | Path,
) -> dict:
    system = Path(system_root)
    export_path = Path(hierarchy_export)
    pad_path = Path(pad_net_inventory)
    contract_path = system / "HIERARCHY_INTERFACE_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (contract_path, "hierarchy_contract"),
        (export_path, "hierarchy_export"),
        (pad_path, "pad_net_inventory"),
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

    expected_rows = read_csv(contract_path)
    actual_rows = read_csv(export_path)

    expected: dict[tuple[str, str], dict[str, str]] = {}
    actual: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[str] = []

    for row in expected_rows:
        key = row_key(row)
        if not all(key):
            errors.append("blank_contract_key:" + "|".join(key))
            continue
        if key in expected:
            errors.append("duplicate_contract_key:" + "|".join(key))
        expected[key] = row

    for row in actual_rows:
        key = row_key(row)
        if not all(key):
            errors.append("blank_export_key:" + "|".join(key))
            continue
        if key in actual:
            duplicates.append("|".join(key))
        actual[key] = row

    if duplicates:
        errors.append(
            "duplicate_export_key:" + ",".join(sorted(set(duplicates)))
        )

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))

    if missing:
        errors.append(
            "missing_hierarchy_rows:"
            + ",".join("|".join(key) for key in missing)
        )
    if extra:
        errors.append(
            "extra_hierarchy_rows:"
            + ",".join("|".join(key) for key in extra)
        )

    type_mismatches: list[str] = []
    for key in sorted(set(expected) & set(actual)):
        expected_type = normalize_pin_type(expected[key].get("pin_type"))
        actual_type = normalize_pin_type(actual[key].get("pin_type"))
        if expected_type != actual_type:
            type_mismatches.append(
                "|".join(key) + f":{expected_type}!={actual_type}"
            )

    if type_mismatches:
        errors.append(
            "pin_type_mismatch:" + ",".join(type_mismatches)
        )

    pad_rows = read_csv(pad_path)
    pad_map = {
        (
            clean(row.get("designator")),
            clean(row.get("pad_name")),
        ): clean(row.get("net_name"))
        for row in pad_rows
        if clean(row.get("designator")) and clean(row.get("pad_name"))
    }

    anchor_mismatches: list[str] = []
    for key, row in expected.items():
        ref = clean(row.get("anchor_ref"))
        pin = clean(row.get("anchor_pin"))
        expected_net = clean(row.get("net_name"))
        actual_net = pad_map.get((ref, pin), "")
        if actual_net != expected_net:
            anchor_mismatches.append(
                f"{ref}.{pin}:{expected_net}!={actual_net or 'MISSING'}"
            )

    if anchor_mismatches:
        errors.append(
            "anchor_net_mismatch:"
            + ",".join(sorted(anchor_mismatches))
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "expected_row_count": len(expected),
        "native_row_count": len(actual),
        "input_sha256": {
            "hierarchy_contract": sha256_file(contract_path),
            "hierarchy_export": sha256_file(export_path),
            "pad_net_inventory": sha256_file(pad_path),
        },
        "verified_checks": {
            "hierarchy_equivalence": status,
        },
        "notes": [
            (
                "Rows are matched by sheet, net name and native anchor "
                "reference/pin; port direction is compared after normalization."
            ),
            (
                "The hierarchy export must come from the compiled native "
                "Altium schematic project."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--hierarchy-export", required=True)
    parser.add_argument("--pad-net-inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        hierarchy_export=args.hierarchy_export,
        pad_net_inventory=args.pad_net_inventory,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
