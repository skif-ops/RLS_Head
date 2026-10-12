from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "CARRIER-SCHEMATIC-CONTRACT-001"

FILES = {
    "blocks": "SCHEMATIC_BLOCKS_SYS_001.csv",
    "components": "SCHEMATIC_COMPONENTS_SYS_001.csv",
    "connectors": "CONNECTOR_PINOUT_SYS_001.csv",
    "power_budget": "POWER_BUDGET_SYS_001.csv",
}

REQUIRED_BLOCKS = {
    "00": "TOP",
    "10": "POWER_INPUT",
    "20": "MCU_CORE",
    "30": "TIME_GNSS",
    "40": "IMU",
    "50": "RADAR_IO_CAN",
    "60": "ETHERNET",
    "70": "DEBUG_BOOT",
}

REQUIRED_COMPONENTS = {
    "U5": "TPS62132RGTR",
    "R_U6_ILIM": "665R 1%",
    "R_U7_ILIM": "1.05k 1%",
    "C_VCAP1;C_VCAP2": "2.2uF X7R ESR_lt_100mR",
    "R_BOOT0": "10k 1%",
    "R_ETH_RBIAS": "12.1k 1%",
    "R_CAN_TERM": "120R 1%",
    "D_GNSS": "ESD0P2RF-02LS",
}

REQUIRED_CONNECTOR_SIGNALS = {
    ("J1_POWER", "12V_IN"),
    ("J1_POWER", "GND"),
    ("J_RADAR_PWR", "RADAR_12V"),
    ("J_RADAR_PWR", "GND"),
    ("J_RADAR_IO", "RADAR_CANL"),
    ("J_RADAR_IO", "RADAR_CANH"),
    ("J_RADAR_IO", "RADAR_CAN_GND"),
    ("J_RADAR_IO", "RADAR_REF"),
    ("J_RADAR_IO", "RADAR_REF_GND"),
    ("J_GNSS_ANT", "GNSS_RF"),
    ("J_SWD", "SWDIO"),
    ("J_SWD", "SWCLK"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        return list(reader)


def validate_blocks(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []
    by_id = {
        str(row.get("block_id", "")).strip(): row
        for row in rows
    }

    for block_id, sheet_name in REQUIRED_BLOCKS.items():
        row = by_id.get(block_id)
        if row is None:
            findings.append(f"missing_block:{block_id}")
            continue
        if str(row.get("sheet_name", "")).strip() != sheet_name:
            findings.append(f"sheet_name:{block_id}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_components(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []
    by_ref = {
        str(row.get("ref_or_pattern", "")).strip(): row
        for row in rows
    }

    for ref, expected in REQUIRED_COMPONENTS.items():
        row = by_ref.get(ref)
        if row is None:
            findings.append(f"missing_component:{ref}")
            continue
        actual = str(row.get("value_or_mpn", "")).strip()
        if actual != expected:
            findings.append(
                f"component_value:{ref}:{actual}!={expected}"
            )

    for row in rows:
        if not str(row.get("placement_rule", "")).strip():
            findings.append(
                f"missing_placement_rule:{row.get('ref_or_pattern','')}"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_connectors(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []

    pairs = {
        (
            str(row.get("connector", "")).strip(),
            str(row.get("signal", "")).strip(),
        )
        for row in rows
    }

    for pair in sorted(REQUIRED_CONNECTOR_SIGNALS):
        if pair not in pairs:
            findings.append(
                f"missing_connector_signal:{pair[0]}:{pair[1]}"
            )

    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (
            str(row.get("connector", "")).strip(),
            str(row.get("pin", "")).strip(),
        )
        if key in seen:
            findings.append(
                f"duplicate_connector_pin:{key[0]}:{key[1]}"
            )
        seen.add(key)

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_power_budget(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []
    by_rail: dict[str, dict[str, float]] = {}

    for row in rows:
        rail = str(row.get("rail", "")).strip()
        try:
            capacity = float(row.get("capacity", ""))
            allocation = float(row.get("allocation", ""))
        except ValueError:
            findings.append(f"parse:{rail}")
            continue

        entry = by_rail.setdefault(
            rail,
            {"capacity": capacity, "allocation": 0.0},
        )

        if abs(entry["capacity"] - capacity) > 1.0e-9:
            findings.append(f"capacity_mismatch:{rail}")

        entry["allocation"] += allocation

    for rail in {"12V_IN", "RADAR_12V", "3V3"}:
        if rail not in by_rail:
            findings.append(f"missing_rail:{rail}")

    for rail, value in by_rail.items():
        if value["allocation"] > value["capacity"] + 1.0e-9:
            findings.append(
                f"over_budget:{rail}:{value['allocation']}>{value['capacity']}"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "rails": by_rail,
        "findings": findings,
    }


def validate_contract(directory: str | Path) -> dict:
    root = Path(directory)
    errors: list[str] = []
    paths: dict[str, Path] = {}

    for key, filename in FILES.items():
        path = root / filename
        paths[key] = path
        if not path.is_file():
            errors.append(f"missing_file:{filename}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": errors,
        }

    try:
        blocks = validate_blocks(paths["blocks"])
        components = validate_components(paths["components"])
        connectors = validate_connectors(paths["connectors"])
        power_budget = validate_power_budget(paths["power_budget"])
    except (ValueError, KeyError) as exc:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": [f"parse:{exc}"],
        }

    sections = {
        "blocks": blocks,
        "components": components,
        "connectors": connectors,
        "power_budget": power_budget,
    }
    failed = [
        name
        for name, result in sections.items()
        if result["status"] != "PASS"
    ]

    return {
        "schema": SCHEMA,
        "status": (
            "SCHEMATIC_CAPTURE_READY"
            if not failed
            else "FAIL"
        ),
        "errors": [],
        "failed_sections": failed,
        **sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the System Carrier schematic-capture contract"
    )
    parser.add_argument("directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate_contract(args.directory)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])

    return 0 if result["status"] == "SCHEMATIC_CAPTURE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
