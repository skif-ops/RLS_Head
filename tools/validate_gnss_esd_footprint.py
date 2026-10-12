from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-GNSS-ESD-FOOTPRINT-001"

PAD_RE = re.compile(
    r'\(pad "(\d+)" smd rect\s*'
    r'\(at (-?[0-9.]+) (-?[0-9.]+)\)\s*'
    r'\(size ([0-9.]+) ([0-9.]+)\)'
)


def validate(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []
    pads = {}

    for match in PAD_RE.finditer(text):
        pads[int(match.group(1))] = (
            float(match.group(2)),
            float(match.group(3)),
            float(match.group(4)),
            float(match.group(5)),
        )

    expected = {
        1: (0.0, -0.19),
        2: (0.0, 0.19),
    }

    if set(pads) != {1, 2}:
        errors.append("pad_number_set")

    for number, (ex, ey) in expected.items():
        if number not in pads:
            continue

        x, y, sx, sy = pads[number]

        if abs(x - ex) > 1e-6 or abs(y - ey) > 1e-6:
            errors.append(f"pad_position:{number}")

        if abs(sx - 0.32) > 1e-6 or abs(sy - 0.24) > 1e-6:
            errors.append(f"pad_size:{number}")

    if text.count("(solder_paste_margin -0.025)") != 2:
        errors.append("paste_margin_count")

    if "PG-TSSLP-2-1" not in text:
        errors.append("footprint_identity")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "pad_count": len(pads),
        "copper_land_mm": [0.32, 0.24],
        "copper_gap_mm": 0.14,
        "pad_pitch_mm": 0.38,
        "stencil_aperture_mm": [0.27, 0.19],
        "body_mm": [0.32, 0.62],
        "notes": [
            "Copper and stencil dimensions follow Infineon PG-TSSLP-2-1 package drawing.",
            "The footprint is intended for the low-capacitance GNSS RF ESD shunt device.",
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
