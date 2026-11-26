from __future__ import annotations

import argparse
import csv
from pathlib import Path


def convert(source: Path, destination: Path) -> int:
    rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    index = 0
    in_component = False
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if line == "[":
            if in_component:
                raise ValueError(f"nested component at line {index}")
            in_component = True
            continue
        if line == "]":
            if not in_component:
                raise ValueError(f"orphan component end at line {index}")
            in_component = False
            continue
        if in_component:
            continue
        if line != "(":
            raise ValueError(f"unexpected text at line {index}: {line}")
        if index >= len(lines):
            raise ValueError("net name missing")
        net_name = lines[index].strip()
        index += 1
        if not net_name:
            raise ValueError(f"net name missing at line {index}")
        while index < len(lines) and lines[index].strip() != ")":
            endpoint = lines[index].strip()
            index += 1
            if not endpoint:
                continue
            if "-" not in endpoint:
                raise ValueError(f"invalid endpoint: {endpoint}")
            designator, pin = endpoint.rsplit("-", 1)
            if not designator or not pin:
                raise ValueError(f"invalid endpoint: {endpoint}")
            key = (designator, pin)
            if key in seen:
                raise ValueError(f"duplicate endpoint: {endpoint}")
            seen.add(key)
            rows.append((designator, pin, net_name))
        if index >= len(lines):
            raise ValueError(f"unterminated net: {net_name}")
        index += 1
    if in_component:
        raise ValueError("unterminated component")
    if not rows:
        raise ValueError("no net endpoints")
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("designator", "pad_name", "net_name"))
        writer.writerows(sorted(rows))
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(convert(args.netlist, args.output))


if __name__ == "__main__":
    main()
