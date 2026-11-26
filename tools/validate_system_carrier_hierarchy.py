from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-HIERARCHY-CAD-001"
CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "hardware"
    / "system_carrier"
    / "HIERARCHY_INTERFACE_SYS_001.csv"
)


def balanced_blocks(text: str, token: str) -> list[str]:
    blocks: list[str] = []
    start = 0
    while True:
        idx = text.find(token, start)
        if idx < 0:
            break
        depth = 0
        in_string = False
        escaped = False
        end = idx
        for pos in range(idx, len(text)):
            ch = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        blocks.append(text[idx:end])
        start = end
    return blocks


def load_contract(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_root(root_path: Path) -> dict[str, dict[str, str]]:
    text = root_path.read_text(encoding="utf-8")
    result: dict[str, dict[str, str]] = {}
    for block in balanced_blocks(text, "(sheet"):
        name_match = re.search(
            r'\(property\s+"Sheetname"\s+"([^"]+)"',
            block,
        )
        if name_match is None:
            continue
        sheet = name_match.group(1)
        pins: dict[str, str] = {}
        for match in re.finditer(
            r'\(pin\s+"([^"]+)"\s+'
            r'(input|output|bidirectional|tri_state|passive)',
            block,
        ):
            pins[match.group(1)] = match.group(2)
        result[sheet] = pins
    return result


def parse_child(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    labels: dict[str, str] = {}
    for block in balanced_blocks(text, "(hierarchical_label"):
        name_match = re.match(
            r'\(hierarchical_label\s+"([^"]+)"',
            block,
        )
        shape_match = re.search(
            r'\(shape\s+'
            r'(input|output|bidirectional|tri_state|passive)\)',
            block,
        )
        if name_match and shape_match:
            labels[name_match.group(1)] = shape_match.group(1)
    return labels


def validate(root_path: str | Path) -> dict:
    root_path = Path(root_path)
    rows = load_contract(CONTRACT)
    root = parse_root(root_path)
    errors: list[str] = []
    validated = 0

    child_cache: dict[str, dict[str, str]] = {}

    for row in rows:
        sheet = row["sheet"].strip()
        net = row["net_name"].strip()
        expected = row["pin_type"].strip()

        root_actual = root.get(sheet, {}).get(net)
        if root_actual != expected:
            errors.append(
                f"root:{sheet}:{net}:{root_actual!r}!={expected!r}"
            )
            continue

        filename = {
            "POWER_INPUT": "10_POWER_INPUT.kicad_sch",
            "MCU_CORE": "20_MCU_CORE.kicad_sch",
            "TIME_GNSS": "30_TIME_GNSS.kicad_sch",
            "IMU": "40_IMU.kicad_sch",
            "RADAR_IO_CAN": "50_RADAR_IO_CAN.kicad_sch",
            "HOST_UART": "60_HOST_UART.kicad_sch",
            "DEBUG_BOOT": "70_DEBUG_BOOT.kicad_sch",
        }[sheet]
        child_path = root_path.parent / filename
        if filename not in child_cache:
            if not child_path.exists():
                errors.append(f"missing_child:{filename}")
                child_cache[filename] = {}
            else:
                child_cache[filename] = parse_child(child_path)

        child_actual = child_cache[filename].get(net)
        if child_actual != expected:
            errors.append(
                f"child:{filename}:{net}:{child_actual!r}!={expected!r}"
            )
            continue

        validated += 1

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "connection_count": len(rows),
        "validated_connection_count": validated,
        "notes": [
            (
                "PASS means every authoritative hierarchy contract row "
                "matches both the native root sheet pin and the native "
                "child hierarchical label. kicad-cli ERC remains the "
                "electrical authority."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root_schematic")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.root_schematic)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
