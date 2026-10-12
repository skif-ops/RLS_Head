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

    local_library_name = str(
        manifest.get("local_symbol_library", "")
    ).strip()
    local_manifest = manifest.get("local_symbol_manifest")

    if local_library_name != "SystemCarrier_Local.kicad_sym":
        errors.append("local_symbol_library_name")
    elif not (root / local_library_name).is_file():
        errors.append("missing_local_symbol_library")

    local_fp_library = str(
        manifest.get("local_footprint_library", "")
    ).strip()
    fp_lib_table = str(
        manifest.get("fp_lib_table", "")
    ).strip()

    if local_fp_library != "SystemCarrier_Local.pretty":
        errors.append("local_footprint_library_name")
    elif not (root / local_fp_library).is_dir():
        errors.append("missing_local_footprint_library")

    if fp_lib_table != "fp-lib-table":
        errors.append("fp_lib_table_name")
    elif not (root / fp_lib_table).is_file():
        errors.append("missing_fp_lib_table")

    sym_lib_table = str(
        manifest.get("sym_lib_table", "")
    ).strip()
    symbol_bindings = manifest.get(
        "symbol_library_bindings"
    )

    if sym_lib_table != "sym-lib-table":
        errors.append("sym_lib_table_name")
    elif not (root / sym_lib_table).is_file():
        errors.append("missing_sym_lib_table")

    required_symbol_libraries = {
        "SystemCarrier_Local",
        "Device",
        "Connector_Generic",
        "Connector",
        "RF_GPS",
        "Switch",
        "MCU_ST_STM32H7",
        "Interface_Ethernet",
    }

    if not isinstance(symbol_bindings, dict):
        errors.append("missing_symbol_library_bindings")
    elif set(symbol_bindings) != required_symbol_libraries:
        errors.append("symbol_library_binding_set")

    if not isinstance(local_manifest, dict):
        errors.append("missing_local_symbol_manifest")
        local_symbol_count = 0
    else:
        local_symbol_count = int(
            local_manifest.get("symbol_count", 0)
        )
        if local_symbol_count != 7:
            errors.append(
                f"local_symbol_count:{local_symbol_count}!=7"
            )

    pending_refs = {
        str(item.get("reference", "")).strip()
        for item in manifest.get("symbol_placeholders", [])
        if isinstance(item, dict)
    }
    for ref in {"U2", "U4", "U5", "U6", "U7", "Y2", "D3", "D4"}:
        if ref in pending_refs:
            errors.append(
                f"local_symbol_fell_back:{ref}"
            )

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
        "local_symbol_count": local_symbol_count,
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
