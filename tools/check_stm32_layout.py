#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

SECTION_RE = re.compile(
    r"^\s*\d+\s+(\S+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)"
)

REGIONS = {
    ".isr_vector": (0x08000000, 0x08200000),
    ".text": (0x08000000, 0x08200000),
    ".dtcm_bss": (0x20000000, 0x20020000),
    ".dma_rx": (0x30000000, 0x30020000),
    ".dma_tx": (0x30020000, 0x30040000),
    ".sram4_status": (0x38000000, 0x38010000),
}


def parse(path: Path) -> dict[str, tuple[int, int, int]]:
    sections: dict[str, tuple[int, int, int]] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        match = SECTION_RE.match(line)

        if not match:
            continue

        name, size_hex, vma_hex, lma_hex = match.groups()
        sections[name] = (
            int(size_hex, 16),
            int(vma_hex, 16),
            int(lma_hex, 16),
        )

    return sections


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_stm32_layout.py <objdump-sections.txt>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    sections = parse(path)

    failures: list[str] = []

    for name, (start, end) in REGIONS.items():
        if name not in sections:
            failures.append(f"missing required section {name}")
            continue

        size, vma, _lma = sections[name]

        if size == 0:
            failures.append(f"required section {name} is empty")
            continue

        if not (start <= vma < end):
            failures.append(
                f"{name} VMA 0x{vma:08X} outside "
                f"0x{start:08X}..0x{end - 1:08X}"
            )

        if vma + size > end:
            failures.append(
                f"{name} end 0x{vma + size:08X} exceeds region end 0x{end:08X}"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    for name in REGIONS:
        size, vma, lma = sections[name]
        print(
            f"PASS {name}: size={size} "
            f"VMA=0x{vma:08X} LMA=0x{lma:08X}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
