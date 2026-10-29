from __future__ import annotations

import argparse
import json
from pathlib import Path

import kicad_sch_api as ksa

from tools.generate_system_carrier_schematic import (
    load_bom_mpn,
    load_footprint_assignments,
)


EXPECTED_CHILDREN = {
    "10_POWER_INPUT.kicad_sch",
    "20_MCU_CORE.kicad_sch",
    "30_TIME_GNSS.kicad_sch",
    "40_IMU.kicad_sch",
    "50_RADAR_IO_CAN.kicad_sch",
    "60_HOST_UART.kicad_sch",
    "70_DEBUG_BOOT.kicad_sch",
}

EXPECTED_PAPER_SIZE = {
    "EVT_SYS_CARRIER.kicad_sch": "A2",
    "20_MCU_CORE.kicad_sch": "A3",
    "30_TIME_GNSS.kicad_sch": "A5",
    "40_IMU.kicad_sch": "A5",
    "50_RADAR_IO_CAN.kicad_sch": "A5",
    "60_HOST_UART.kicad_sch": "A5",
    "70_DEBUG_BOOT.kicad_sch": "A5",
}


def validate(root: Path) -> dict:
    manifest_path = root / "cad_scaffold_manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    errors: list[str] = []
    parsed: list[str] = []
    footprint_assignments = load_footprint_assignments(
        Path(__file__).resolve().parents[1]
        / "hardware"
        / "system_carrier"
        / "FOOTPRINT_ASSIGNMENT_SYS_002.csv"
    )
    bom_mpn = load_bom_mpn(
        Path(__file__).resolve().parents[1]
        / "hardware"
        / "system_carrier"
        / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    found_footprint_refs: set[str] = set()
    verified_mpn_refs: set[str] = set()

    if manifest.get("footprint_assignment_count") != len(
        footprint_assignments
    ):
        errors.append("footprint_assignment_count")

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
        "Switch",
        "power",
        "MCU_ST_STM32H7",
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
        if local_symbol_count != 8:
            errors.append(
                f"local_symbol_count:{local_symbol_count}!=8"
            )

    pending_refs = {
        str(item.get("reference", "")).strip()
        for item in manifest.get("symbol_placeholders", [])
        if isinstance(item, dict)
    }
    for ref in {"U2", "U4", "U5", "U6", "U7", "U9", "Y1", "D3", "D4", "D8"}:
        if ref in pending_refs:
            errors.append(
                f"local_symbol_fell_back:{ref}"
            )

    assigned_gpio_count = int(
        manifest.get("mcu_assigned_gpio_count", 0)
    )
    unused_gpio_nc_count = int(
        manifest.get(
            "mcu_unused_gpio_no_connect_count",
            0,
        )
    )

    if assigned_gpio_count < 20:
        errors.append(
            "mcu_assigned_gpio_count"
        )

    if unused_gpio_nc_count < 80:
        errors.append(
            "mcu_unused_gpio_no_connect_count"
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
            schematic = ksa.load_schematic(str(path))
        except Exception as exc:
            errors.append(
                f"parse:{path.name}:{type(exc).__name__}"
            )
        else:
            parsed.append(path.name)
            expected_paper = EXPECTED_PAPER_SIZE.get(path.name, "A4")
            if (
                f'(paper "{expected_paper}")'
                not in path.read_text(encoding="utf-8")
            ):
                errors.append(f"paper_size:{path.name}")
            for component in schematic.components:
                reference = component.reference
                if component.get_property("hierarchy_path") and (
                    "hierarchy_path" not in component.hidden_properties
                ):
                    errors.append(f"visible_hierarchy_path:{reference}")
                if reference.startswith("#FLG"):
                    continue
                if reference in found_footprint_refs:
                    errors.append(f"duplicate_reference:{reference}")
                found_footprint_refs.add(reference)
                expected = footprint_assignments.get(reference)
                if expected is None:
                    errors.append(f"uncontracted_reference:{reference}")
                elif component.footprint != expected:
                    errors.append(f"footprint_mismatch:{reference}")
                expected_mpn = bom_mpn.get(reference)
                actual_mpn = component.get_property("MPN", "")
                if isinstance(actual_mpn, dict):
                    actual_mpn = actual_mpn.get("value", "")
                if expected_mpn is None:
                    errors.append(f"missing_bom_reference:{reference}")
                elif actual_mpn != expected_mpn:
                    errors.append(f"bom_mpn_mismatch:{reference}")
                else:
                    verified_mpn_refs.add(reference)
                if "MPN" not in component.hidden_properties:
                    errors.append(f"visible_mpn:{reference}")

    for reference in sorted(set(footprint_assignments) - found_footprint_refs):
        errors.append(f"missing_footprint_reference:{reference}")
    for reference in sorted(set(bom_mpn) - found_footprint_refs):
        errors.append(f"missing_bom_reference:{reference}")

    return {
        "schema": "SYSTEM-CARRIER-CAD-SCAFFOLD-VALIDATION-001",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "parsed_schematics": parsed,
        "verified_footprint_count": len(found_footprint_refs),
        "verified_bom_mpn_count": len(verified_mpn_refs),
        "placeholder_count": len(
            manifest.get("symbol_placeholders", [])
        ),
        "local_symbol_count": local_symbol_count,
        "mcu_assigned_gpio_count": assigned_gpio_count,
        "mcu_unused_gpio_no_connect_count":
            unused_gpio_nc_count,
        "notes": [
            "PASS verifies generated KiCad syntax/hierarchy files parse through kicad-sch-api.",
            "Every physical component must retain its locked footprint assignment after serialization.",
            "Every physical component must retain its authoritative BOM MPN after serialization.",
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
