from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_REFS = {
    "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8",
    "D_GNSS", "D_ETH", "D_CAN", "J_ETH",
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("missing CSV header")
        return list(reader)


def validate_package_contract(directory: str | Path) -> dict:
    root = Path(directory)
    bom_path = root / "BOM_SYS_CARRIER_003.csv"
    contract_path = root / "PACKAGE_CONTRACT_SYS_001.csv"

    errors: list[str] = []

    if not bom_path.is_file():
        errors.append("missing_bom")
        bom_rows = []
    else:
        bom_rows = _read(bom_path)

    if not contract_path.is_file():
        errors.append("missing_package_contract")
        contract_rows = []
    else:
        contract_rows = _read(contract_path)

    bom = {
        str(row.get("ref", "")).strip(): str(row.get("mpn", "")).strip()
        for row in bom_rows
        if str(row.get("ref", "")).strip()
    }
    contract = {
        str(row.get("ref", "")).strip(): row
        for row in contract_rows
        if str(row.get("ref", "")).strip()
    }

    for ref in sorted(REQUIRED_REFS):
        if ref not in contract:
            errors.append(f"missing_contract_ref:{ref}")
            continue

        row = contract[ref]
        if bom.get(ref) != str(row.get("mpn", "")).strip():
            errors.append(f"mpn_mismatch:{ref}")

        if not str(row.get("manufacturer_package", "")).strip():
            errors.append(f"missing_package:{ref}")

        if not str(row.get("pin_count", "")).strip():
            errors.append(f"missing_pin_count:{ref}")

        policy = str(row.get("footprint_policy", "")).strip()
        if policy not in {
            "STOCK_LOCKED",
            "STOCK_VERIFY",
            "VERIFY_OR_CUSTOM",
            "CUSTOM_REQUIRED",
        }:
            errors.append(f"invalid_footprint_policy:{ref}")

        if (
            policy == "STOCK_LOCKED"
            and not str(row.get("footprint_candidate", "")).strip()
        ):
            errors.append(f"missing_locked_footprint:{ref}")

    if bom.get("D_CAN") != "ESD2CANFD24DBZRQ1":
        errors.append("can_esd_not_orderable_mpn")

    return {
        "schema": "SYSTEM-CARRIER-PACKAGE-CONTRACT-001",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "contract_count": len(contract),
    }
