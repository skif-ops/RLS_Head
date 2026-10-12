from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-ICM42688-FOOTPRINT-001"

EXPECTED = {
    1: (-1.0125, 0.75, 0.0),
    2: (-1.0125, 0.25, 0.0),
    3: (-1.0125, -0.25, 0.0),
    4: (-1.0125, -0.75, 0.0),
    5: (-0.5, -1.2625, 90.0),
    6: (0.0, -1.2625, 90.0),
    7: (0.5, -1.2625, 90.0),
    8: (1.0125, -0.75, 0.0),
    9: (1.0125, -0.25, 0.0),
    10: (1.0125, 0.25, 0.0),
    11: (1.0125, 0.75, 0.0),
    12: (0.5, 1.2625, 90.0),
    13: (0.0, 1.2625, 90.0),
    14: (-0.5, 1.2625, 90.0),
}

PAD_RE = re.compile(
    r'\(pad "(\d+)" smd rect '
    r'\(at (-?[0-9.]+) (-?[0-9.]+)(?: ([0-9.]+))?\) '
    r'\(size ([0-9.]+) ([0-9.]+)\)'
)


def validate(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []
    pads: dict[int, tuple[float, float, float, float, float]] = {}

    for match in PAD_RE.finditer(text):
        number = int(match.group(1))
        pads[number] = (
            float(match.group(2)),
            float(match.group(3)),
            float(match.group(4) or 0.0),
            float(match.group(5)),
            float(match.group(6)),
        )

    if set(pads) != set(EXPECTED):
        errors.append("pad_number_set")

    for number, expected in EXPECTED.items():
        if number not in pads:
            continue

        x, y, rot, sx, sy = pads[number]
        ex, ey, erot = expected

        if abs(x - ex) > 1e-6 or abs(y - ey) > 1e-6:
            errors.append(f"pad_position:{number}")

        if abs(rot - erot) > 1e-6:
            errors.append(f"pad_rotation:{number}")

        if abs(sx - 0.475) > 1e-6 or abs(sy - 0.25) > 1e-6:
            errors.append(f"pad_size:{number}")

    if text.count("(solder_mask_margin 0.05)") != 14:
        errors.append("solder_mask_margin_count")

    if "2.5x3mm_P0.5mm" not in text:
        errors.append("footprint_identity")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "pad_count": len(pads),
        "land_size_mm": [0.475, 0.25],
        "pitch_mm": 0.5,
        "body_mm": [2.5, 3.0],
        "notes": [
            "Nominal copper land follows the TDK LGA nominal solder-pad dimensions.",
            "Each pad uses +0.05 mm solder-mask expansion per side, matching the +0.10 mm opening guidance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("footprint")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.footprint)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
