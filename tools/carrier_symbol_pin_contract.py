from __future__ import annotations

import csv
from pathlib import Path


EXPECTED_COUNTS = {
    "U2": 14,
    "U3": 25,
    "U4": 9,
    "U5": 17,
    "U6": 10,
    "U7": 10,
    "U8": 24,
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("missing CSV header")
        return list(reader)


def validate_symbol_pin_contract(directory: str | Path) -> dict:
    root = Path(directory)
    contract_path = root / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    package_path = root / "PACKAGE_CONTRACT_SYS_001.csv"

    errors: list[str] = []

    if not contract_path.is_file():
        return {
            "schema": "SYSTEM-CARRIER-SYMBOL-PIN-CONTRACT-001",
            "status": "FAIL",
            "errors": ["missing_symbol_pin_contract"],
        }

    rows = _read(contract_path)
    packages = _read(package_path)

    package_mpn = {
        str(row.get("ref", "")).strip(): str(row.get("mpn", "")).strip()
        for row in packages
    }

    grouped: dict[str, list[dict[str, str]]] = {}

    for row in rows:
        ref = str(row.get("ref", "")).strip()
        pin = str(row.get("pin_number", "")).strip()
        mpn = str(row.get("mpn", "")).strip()
        connection = str(row.get("connection", "")).strip()
        policy = str(row.get("policy", "")).strip()

        if not ref or not pin:
            errors.append("blank_ref_or_pin")
            continue

        grouped.setdefault(ref, []).append(row)

        if package_mpn.get(ref) != mpn:
            errors.append(f"mpn_mismatch:{ref}")

        if not connection:
            errors.append(f"blank_connection:{ref}:{pin}")

        if "TBD" in connection.upper():
            errors.append(f"tbd_connection:{ref}:{pin}")

        if policy not in {
            "CONNECT",
            "NC_ALLOWED",
            "INTERNAL_STRAP",
            "DNP_OPTION",
        }:
            errors.append(f"invalid_policy:{ref}:{pin}")

    for ref, expected in EXPECTED_COUNTS.items():
        group = grouped.get(ref, [])
        if len(group) != expected:
            errors.append(
                f"pin_count:{ref}:{len(group)}!={expected}"
            )

        pins = [
            str(row.get("pin_number", "")).strip()
            for row in group
        ]
        if len(set(pins)) != len(pins):
            errors.append(f"duplicate_pin:{ref}")

    missing = sorted(set(EXPECTED_COUNTS) - set(grouped))
    errors.extend(f"missing_ref:{ref}" for ref in missing)

    return {
        "schema": "SYSTEM-CARRIER-SYMBOL-PIN-CONTRACT-001",
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "row_count": len(rows),
        "refs": sorted(grouped),
    }
