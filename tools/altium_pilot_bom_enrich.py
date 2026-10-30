from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


SCHEMA = "ALTIUM-PILOT-BOM-ENRICHMENT-001"
OUTPUT_FIELDS = (
    "Name",
    "Description",
    "Designator",
    "Footprint",
    "LibRef",
    "Quantity",
    "MPN",
    "Manufacturer",
    "Population",
    "DNP Status",
    "Pilot Disposition",
    "Procurement Quantity",
    "Procurement Class",
    "Contract Status",
)

PILOT_DISPOSITION = {
    "POPULATE": "FIT",
    "DNP_DEFAULT": "DNP",
    "DNP_OPTION": "DNP",
    "PCB_ONLY": "PCB_ONLY",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def enrich(
    *,
    system_root: str | Path,
    native_bom: str | Path,
) -> tuple[list[dict[str, str]], dict]:
    system = Path(system_root)
    native_path = Path(native_bom)
    contract_path = system / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    errors: list[str] = []

    for path, label in (
        (native_path, "native_bom"),
        (contract_path, "bom_contract"),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if errors:
        return [], {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
        }

    native_rows = _read_rows(native_path)
    contract_rows = _read_rows(contract_path)
    contract_by_ref: dict[str, dict[str, str]] = {}

    for row in contract_rows:
        ref = row.get("ref", "").strip()
        if not ref:
            errors.append("empty_contract_designator")
            continue
        if ref in contract_by_ref:
            errors.append(f"duplicate_contract_designator:{ref}")
        contract_by_ref[ref] = row

    native_by_ref: dict[str, dict[str, str]] = {}
    for row in native_rows:
        ref = row.get("Designator", "").strip()
        if not ref:
            errors.append("empty_native_designator")
            continue
        if ref in native_by_ref:
            errors.append(f"duplicate_native_designator:{ref}")
        native_by_ref[ref] = row

    missing = sorted(set(contract_by_ref) - set(native_by_ref))
    extra = sorted(set(native_by_ref) - set(contract_by_ref))
    if missing:
        errors.append("missing_designators:" + ",".join(missing))
    if extra:
        errors.append("extra_designators:" + ",".join(extra))

    output_rows: list[dict[str, str]] = []
    for native in native_rows:
        ref = native.get("Designator", "").strip()
        contract = contract_by_ref.get(ref)
        if contract is None:
            continue

        native_mpn = native.get("MPN", "").strip()
        contract_mpn = contract.get("value_or_mpn", "").strip()
        if native_mpn != contract_mpn:
            errors.append(f"mpn_mismatch:{ref}:{native_mpn}!={contract_mpn}")

        native_qty = native.get("Quantity", "").strip()
        contract_qty = contract.get("qty", "").strip()
        if native_qty and native_qty != contract_qty:
            errors.append(f"quantity_mismatch:{ref}:{native_qty}!={contract_qty}")
        effective_qty = native_qty or contract_qty

        manufacturer = contract.get("manufacturer", "").strip()
        population = contract.get("population", "").strip()
        procurement_class = contract.get("procurement_class", "").strip()
        contract_status = contract.get("status", "").strip()
        if not manufacturer:
            errors.append(f"missing_manufacturer:{ref}")
        if population not in PILOT_DISPOSITION:
            errors.append(f"unsupported_population:{ref}:{population}")
            disposition = ""
        else:
            disposition = PILOT_DISPOSITION[population]
        if not procurement_class:
            errors.append(f"missing_procurement_class:{ref}")
        if contract_status != "LOCKED":
            errors.append(f"unlocked_contract:{ref}:{contract_status}")

        output_rows.append({
            "Name": native.get("Name", "").strip() or native_mpn,
            "Description": contract.get("description", "").strip(),
            "Designator": ref,
            "Footprint": (
                native.get("Footprint", "").strip()
                or contract.get("footprint_id", "").strip()
            ),
            "LibRef": native.get("LibRef", ""),
            "Quantity": effective_qty,
            "MPN": native_mpn,
            "Manufacturer": manufacturer,
            "Population": population,
            "DNP Status": (
                "YES" if disposition == "DNP"
                else "NOT_APPLICABLE" if disposition == "PCB_ONLY"
                else "NO"
            ),
            "Pilot Disposition": disposition,
            "Procurement Quantity": effective_qty if disposition == "FIT" else "0",
            "Procurement Class": procurement_class,
            "Contract Status": contract_status,
        })

    counts = Counter(row["Pilot Disposition"] for row in output_rows)
    result = {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "native_designator_count": len(native_by_ref),
        "contract_designator_count": len(contract_by_ref),
        "output_designator_count": len(output_rows),
        "pilot_disposition_counts": dict(sorted(counts.items())),
        "input_sha256": {
            "native_bom": sha256_file(native_path),
            "bom_contract": sha256_file(contract_path),
        },
        "verified_checks": {
            "designator_set_equivalence": "PASS" if not missing and not extra else "FAIL",
            "mpn_equivalence": (
                "FAIL" if any(item.startswith("mpn_mismatch:") for item in errors)
                else "PASS"
            ),
            "manufacturer_population_complete": (
                "FAIL" if any(
                    item.startswith((
                        "missing_manufacturer:",
                        "unsupported_population:",
                    ))
                    for item in errors
                ) else "PASS"
            ),
        },
        "variant_policy": {
            "name": "PILOT_BASE_REV_A",
            "DNP_DEFAULT": "DNP",
            "DNP_OPTION": "DNP",
            "PCB_ONLY": "PCB_ONLY",
            "POPULATE": "FIT",
        },
        "notes": [
            "The native Altium BOM remains the source for designators and MPNs.",
            "Manufacturer, population and procurement fields are joined from BOM_SYS_CARRIER_LAYOUT_004.csv.",
            "When the native audit BOM contains only Designator and MPN, quantity and footprint are filled from the locked contract after exact designator and MPN equivalence passes.",
            "Optional GNSS active-antenna bias parts are DNP in the base pilot variant.",
        ],
    }
    return output_rows, result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--native-bom", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    rows, result = enrich(
        system_root=args.system_root,
        native_bom=args.native_bom,
    )
    if result["status"] == "PASS":
        write_csv(Path(args.output), rows)
        result["output_sha256"] = sha256_file(Path(args.output))
    Path(args.receipt).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
