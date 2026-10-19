from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-HIERARCHY-RESULT-001"

ROOT_SCHEMATIC = "EVT_SYS_CARRIER.SchDoc"

SHEET_TO_FILE = {
    "POWER_INPUT": "10_POWER_INPUT.SchDoc",
    "MCU_CORE": "20_MCU_CORE.SchDoc",
    "TIME_GNSS": "30_TIME_GNSS.SchDoc",
    "IMU": "40_IMU.SchDoc",
    "RADAR_IO_CAN": "50_RADAR_IO_CAN.SchDoc",
    "ETHERNET": "60_ETHERNET.SchDoc",
    "DEBUG_BOOT": "70_DEBUG_BOOT.SchDoc",
}

DIRECTION_MAP = {
    "input": "input",
    "output": "output",
    "bidirectional": "bidirectional",
    "passive": "unspecified",
}


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


def basename(value: object) -> str:
    return Path(clean(value).replace("\\", "/")).name


def validate(
    *,
    system_root: str | Path,
    audit_dir: str | Path,
) -> dict:
    system = Path(system_root)
    audit = Path(audit_dir)

    contract_path = system / "HIERARCHY_INTERFACE_SYS_001.csv"
    port_path = audit / "hierarchy_port_inventory.csv"
    entry_path = audit / "hierarchy_sheet_entry_inventory.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (contract_path, "hierarchy_contract"),
        (port_path, "hierarchy_port_inventory"),
        (entry_path, "hierarchy_sheet_entry_inventory"),
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

    contract_rows = read_csv(contract_path)
    port_rows = read_csv(port_path)
    entry_rows = read_csv(entry_path)

    expected_ports: set[tuple[str, str, str]] = set()
    expected_entries: set[tuple[str, str, str, str]] = set()
    contract_keys: set[tuple[str, str]] = set()

    for row in contract_rows:
        sheet = clean(row.get("sheet"))
        net = clean(row.get("net_name"))
        pin_type = clean(row.get("pin_type")).lower()

        child_file = SHEET_TO_FILE.get(sheet)
        if child_file is None:
            errors.append(f"unknown_contract_sheet:{sheet}")
            continue

        direction = DIRECTION_MAP.get(pin_type)
        if direction is None:
            errors.append(
                f"unsupported_contract_direction:{sheet}:{net}:{pin_type}"
            )
            continue

        key = (sheet, net)
        if key in contract_keys:
            errors.append(f"duplicate_contract_port:{sheet}:{net}")
        contract_keys.add(key)

        expected_ports.add((child_file, net, direction))
        expected_entries.add(
            (ROOT_SCHEMATIC, child_file, net, direction)
        )

    expected_child_files = set(SHEET_TO_FILE.values())

    actual_ports: set[tuple[str, str, str]] = set()
    for row in port_rows:
        doc = basename(row.get("document_file"))
        if doc not in expected_child_files:
            continue
        name = clean(row.get("port_name"))
        io_type = clean(row.get("io_type")).lower()
        if name:
            actual_ports.add((doc, name, io_type))

    actual_entries: set[tuple[str, str, str, str]] = set()
    for row in entry_rows:
        parent = basename(row.get("parent_document_file"))
        child = basename(row.get("child_document_file"))
        if parent != ROOT_SCHEMATIC or child not in expected_child_files:
            continue
        name = clean(row.get("entry_name"))
        io_type = clean(row.get("io_type")).lower()
        if name:
            actual_entries.add((parent, child, name, io_type))

    missing_ports = sorted(expected_ports - actual_ports)
    extra_ports = sorted(actual_ports - expected_ports)
    missing_entries = sorted(expected_entries - actual_entries)
    extra_entries = sorted(actual_entries - expected_entries)

    if missing_ports:
        errors.append(
            "missing_native_ports:"
            + ",".join(
                f"{doc}:{name}:{io}"
                for doc, name, io in missing_ports
            )
        )
    if extra_ports:
        errors.append(
            "unexpected_native_ports:"
            + ",".join(
                f"{doc}:{name}:{io}"
                for doc, name, io in extra_ports
            )
        )
    if missing_entries:
        errors.append(
            "missing_native_sheet_entries:"
            + ",".join(
                f"{parent}->{child}:{name}:{io}"
                for parent, child, name, io in missing_entries
            )
        )
    if extra_entries:
        errors.append(
            "unexpected_native_sheet_entries:"
            + ",".join(
                f"{parent}->{child}:{name}:{io}"
                for parent, child, name, io in extra_entries
            )
        )

    port_by_child_name = {
        (doc, name): io
        for doc, name, io in actual_ports
    }
    entry_direction_mismatch: list[str] = []
    for _parent, child, name, entry_io in actual_entries:
        port_io = port_by_child_name.get((child, name))
        if port_io is not None and port_io != entry_io:
            entry_direction_mismatch.append(
                f"{child}:{name}:{port_io}!={entry_io}"
            )

    if entry_direction_mismatch:
        errors.append(
            "port_sheet_entry_direction_mismatch:"
            + ",".join(sorted(entry_direction_mismatch))
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "expected_child_sheet_count": len(expected_child_files),
        "contract_port_count": len(expected_ports),
        "native_port_count": len(actual_ports),
        "native_sheet_entry_count": len(actual_entries),
        "input_sha256": {
            "hierarchy_contract": sha256_file(contract_path),
            "hierarchy_port_inventory": sha256_file(port_path),
            "hierarchy_sheet_entry_inventory": sha256_file(entry_path),
        },
        "verified_checks": {
            "hierarchy_equivalence": status,
        },
        "notes": [
            (
                "Contract passive ports map to Altium unspecified TPortIO; "
                "input/output/bidirectional map directly."
            ),
            (
                "PASS requires an exact port set on all seven child SchDocs "
                "and matching root sheet entries linked to the correct child."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        audit_dir=args.audit_dir,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
