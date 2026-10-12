from __future__ import annotations

import argparse
import json
from pathlib import Path

import kicad_sch_api as ksa


EXPECTED_CHILDREN = {
    "10_POWER_INPUT.kicad_sch",
    "20_MCU_CORE.kicad_sch",
    "30_TIME_GNSS.kicad_sch",
    "40_IMU.kicad_sch",
    "50_RADAR_IO_CAN.kicad_sch",
    "60_ETHERNET.kicad_sch",
    "70_DEBUG_BOOT.kicad_sch",
}


def validate(root: Path) -> dict:
    manifest_path = root / "cad_scaffold_manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    errors: list[str] = []
    parsed: list[str] = []

    if manifest.get("schema") != "SYSTEM-CARRIER-CAD-SCAFFOLD-001":
        errors.append("manifest_schema")

    if set(manifest.get("child_sheets", [])) != EXPECTED_CHILDREN:
        errors.append("child_sheet_set")

    files = [
        root / "EVT_SYS_CARRIER.kicad_sch",
        *[root / name for name in sorted(EXPECTED_CHILDREN)],
    ]

    for path in files:
        if not path.is_file():
            errors.append(f"missing:{path.name}")
            continue
        try:
            ksa.load_schematic(str(path))
        except Exception as exc:
            errors.append(
                f"parse:{path.name}:{type(exc).__name__}"
            )
        else:
            parsed.append(path.name)

    return {
        "schema": "SYSTEM-CARRIER-CAD-SCAFFOLD-VALIDATION-001",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "parsed_schematics": parsed,
        "placeholder_count": len(
            manifest.get("symbol_placeholders", [])
        ),
        "notes": [
            "PASS verifies generated KiCad syntax/hierarchy files parse through kicad-sch-api.",
            "Placeholder count is informational and must reach zero before Review A.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(Path(args.directory))
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
