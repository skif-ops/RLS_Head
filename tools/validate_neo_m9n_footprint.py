from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-NEO-M9N-FOOTPRINT-001"

RIGHT_Y = [-7.0, -5.9, -4.8, -3.7, -2.6, -1.5, 1.5, 2.6, 3.7, 4.8, 5.9, 7.0]
LEFT_Y = [7.0, 5.9, 4.8, 3.7, 2.6, 1.5, -1.5, -2.6, -3.7, -4.8, -5.9, -7.0]

EXPECTED = {
    **{number: (5.6, y) for number, y in enumerate(RIGHT_Y, start=1)},
    **{number: (-5.6, y) for number, y in enumerate(LEFT_Y, start=13)},
}

PAD_RE = re.compile(
    r'\(pad "(\d+)" smd rect '
    r'\(at (-?[0-9.]+) (-?[0-9.]+)\) '
    r'\(size ([0-9.]+) ([0-9.]+)\)'
)


def validate(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []
    pads: dict[int, tuple[float, float, float, float]] = {}

    for match in PAD_RE.finditer(text):
        number = int(match.group(1))
        pads[number] = (
            float(match.group(2)),
            float(match.group(3)),
            float(match.group(4)),
            float(match.group(5)),
        )

    if set(pads) != set(EXPECTED):
        errors.append("pad_number_set")

    for number, (expected_x, expected_y) in EXPECTED.items():
        if number not in pads:
            continue

        x, y, sx, sy = pads[number]

        if abs(x - expected_x) > 1e-6 or abs(y - expected_y) > 1e-6:
            errors.append(f"pad_position:{number}")

        if abs(sx - 1.0) > 1e-6 or abs(sy - 0.8) > 1e-6:
            errors.append(f"pad_size:{number}")

    if "12.2x16mm" not in text:
        errors.append("footprint_identity")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "pad_count": len(pads),
        "land_size_mm": [1.0, 0.8],
        "pitch_mm": 1.1,
        "center_gap_mm": 3.0,
        "body_mm": [12.2, 16.0],
        "notes": [
            "Pad geometry and numbering follow the u-blox NEO-M9N suggested footprint and pin assignment.",
            "The footprint is for the receiver module only; RF_IN routing/ESD remain separate layout constraints.",
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
