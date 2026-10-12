from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-TPS259470-FOOTPRINT-001"

SIMPLE = {
    2: (-0.9, -0.225, 0.6, 0.3),
    3: (-0.9, 0.225, 0.6, 0.3),
    5: (-0.25, 0.0, 0.3, 2.4),
    6: (0.25, 0.0, 0.3, 2.4),
    8: (0.9, 0.225, 0.6, 0.3),
    9: (0.9, -0.225, 0.6, 0.3),
}

CUSTOM = {
    1: (-0.725, -0.875),
    4: (-0.725, 0.875),
    7: (0.725, 0.875),
    10: (0.725, -0.875),
}

PAD_NUMBER_RE = re.compile(r'\(pad "(\d*)" smd')
SIMPLE_RE = re.compile(
    r'\(pad "(\d+)" smd roundrect\s*'
    r'\(at (-?[0-9.]+) (-?[0-9.]+)(?: [0-9.]+)?\)\s*'
    r'\(size ([0-9.]+) ([0-9.]+)\)'
)
CUSTOM_RE = re.compile(
    r'\(pad "(\d+)" smd custom\s*'
    r'\(at (-?[0-9.]+) (-?[0-9.]+)(?: [0-9.]+)?\)'
)


def validate(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []

    numbered = {
        int(value)
        for value in PAD_NUMBER_RE.findall(text)
        if value
    }

    if numbered != set(range(1, 11)):
        errors.append("electrical_pad_number_set")

    simple = {}
    for match in SIMPLE_RE.finditer(text):
        number = int(match.group(1))
        if number in SIMPLE:
            simple[number] = tuple(
                float(match.group(index))
                for index in range(2, 6)
            )

    for number, expected in SIMPLE.items():
        actual = simple.get(number)
        if actual is None:
            errors.append(f"missing_simple_pad:{number}")
            continue

        if any(
            abs(actual[index] - expected[index]) > 1e-6
            for index in range(4)
        ):
            errors.append(f"simple_pad_geometry:{number}")

    custom = {}
    for match in CUSTOM_RE.finditer(text):
        number = int(match.group(1))
        if number in CUSTOM:
            custom[number] = (
                float(match.group(2)),
                float(match.group(3)),
            )

    for number, expected in CUSTOM.items():
        actual = custom.get(number)
        if actual is None:
            errors.append(f"missing_custom_pad:{number}")
            continue

        if (
            abs(actual[0] - expected[0]) > 1e-6
            or abs(actual[1] - expected[1]) > 1e-6
        ):
            errors.append(f"custom_pad_position:{number}")

    if text.count('(pad "" smd roundrect') != 4:
        errors.append("long_pad_paste_aperture_count")

    for token in (
        "(xy -0.425 0.275)",
        "(xy -0.425 -0.275)",
        "(size 0.3 2.4)",
        "(start -1.45 -1.45)",
        "(end 1.45 1.45)",
    ):
        if token not in text:
            errors.append(f"missing_geometry_token:{token}")

    if "RPW0010A" not in text:
        errors.append("footprint_identity")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "electrical_pad_numbers": sorted(numbered),
        "custom_corner_pads": sorted(custom),
        "simple_pads": sorted(simple),
        "body_mm": [2.0, 2.0],
        "courtyard_mm": [2.9, 2.9],
        "notes": [
            "Copper geometry follows TI RPW0010A land-pattern dimensions.",
            "Corner custom-pad topology is cross-checked against KiCad footprint MR 4677.",
            "Pads 5 and 6 use split paste apertures matching the TI/KiCad stencil pattern.",
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
