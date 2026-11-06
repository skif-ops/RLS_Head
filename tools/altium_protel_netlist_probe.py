"""Compare an Altium project Protel netlist with a KiCad endpoint baseline.

This is diagnostic evidence, not the ALTIUM_EQUIVALENCE_GATE. Protel omits
intentionally unconnected pins, so those are reported separately.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def compare(baseline_path: Path, netlist_path: Path) -> dict:
    with baseline_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        (row["designator"], row["pin"]): row["net_name"]
        for row in rows
    }
    if len(expected) != len(rows):
        raise ValueError("Duplicate endpoint in KiCad baseline")

    native = []
    content = netlist_path.read_text(encoding="utf-8-sig", errors="replace")
    for block in re.findall(r"^\(\s*\n(.*?)^\)", content, flags=re.M | re.S):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        pins = set()
        for line in lines[1:]:
            if "-" not in line:
                raise ValueError(f"Malformed Protel endpoint: {line}")
            pins.add(tuple(line.rsplit("-", 1)))
        native.append((lines[0], pins))

    by_native_pin = defaultdict(list)
    by_expected_net = defaultdict(set)
    for pin, net_name in expected.items():
        by_expected_net[net_name].add(pin)
    merged_groups = []
    for index, (name, pins) in enumerate(native):
        for pin in pins:
            by_native_pin[pin].append(index)
        source_nets = sorted({expected[pin] for pin in pins if pin in expected})
        if len(source_nets) > 1:
            merged_groups.append(
                {
                    "native_group_index": index,
                    "native_name": name,
                    "source_nets": source_nets,
                    "pins": sorted(f"{ref}-{number}" for ref, number in pins),
                }
            )

    split_source_nets = []
    for name, pins in by_expected_net.items():
        groups = {index for pin in pins for index in by_native_pin.get(pin, [])}
        if len(groups) > 1:
            split_source_nets.append(
                {
                    "source_net": name,
                    "native_group_indices": sorted(groups),
                    "source_pin_count": len(pins),
                }
            )

    missing = set(expected) - set(by_native_pin)
    missing_connected = sorted(
        f"{ref}-{number}:{expected[(ref, number)]}"
        for ref, number in missing
        if not expected[(ref, number)].startswith("unconnected-(")
    )
    missing_unconnected = sorted(
        f"{ref}-{number}:{expected[(ref, number)]}"
        for ref, number in missing
        if expected[(ref, number)].startswith("unconnected-(")
    )
    extra = sorted(f"{ref}-{number}" for ref, number in set(by_native_pin) - set(expected))
    duplicated = {
        f"{ref}-{number}": indices
        for (ref, number), indices in by_native_pin.items()
        if len(indices) > 1
    }
    names = Counter(name for name, _ in native)
    result = {
        "schema": "ALTIUM-PROTEL-NETLIST-PROBE-001",
        "baseline_pin_count": len(expected),
        "baseline_net_count": len(by_expected_net),
        "native_group_count": len(native),
        "native_assigned_pin_count": len(by_native_pin),
        "missing_connected_pin_count": len(missing_connected),
        "missing_connected_pins": missing_connected,
        "missing_unconnected_pin_count": len(missing_unconnected),
        "missing_unconnected_pins": missing_unconnected,
        "extra_pin_count": len(extra),
        "extra_pins": extra,
        "merged_group_count": len(merged_groups),
        "merged_groups": merged_groups,
        "split_source_net_count": len(split_source_nets),
        "split_source_nets": sorted(split_source_nets, key=lambda row: row["source_net"]),
        "duplicate_native_pin": duplicated,
        "native_name_duplicates": {
            name: count for name, count in sorted(names.items()) if count > 1
        },
    }
    result["status"] = (
        "PASS"
        if not (
            missing_connected or extra or merged_groups or split_source_nets or duplicated
        )
        else "FAIL"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--netlist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.netlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        result["status"],
        "connected missing:", result["missing_connected_pin_count"],
        "merges:", result["merged_group_count"],
        "splits:", result["split_source_net_count"],
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
