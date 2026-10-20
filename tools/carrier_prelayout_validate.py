from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-PRELAYOUT-001"
DESIGNATOR_RE = re.compile(
    r"^(?:[A-Z]{1,3}\d+[A-Z0-9]*|#FLG\d+)$"
)
REFERENCE_RE = re.compile(
    r'\(property "Reference" "([^"]+)"'
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def unique_by(
    rows: list[dict[str, str]],
    field: str,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    result: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for row in rows:
        key = str(row.get(field, "")).strip()
        if not key:
            errors.append(f"blank:{field}")
            continue
        if key in result:
            errors.append(f"duplicate:{field}:{key}")
        result[key] = row
    return result, errors


def schematic_refs(
    generated: Path,
) -> tuple[set[str], dict[str, list[str]], list[str]]:
    physical: set[str] = set()
    locations: dict[str, list[str]] = defaultdict(list)
    errors: list[str] = []

    child_files = sorted(
        path
        for path in generated.glob("*.kicad_sch")
        if path.name != "EVT_SYS_CARRIER.kicad_sch"
    )
    if len(child_files) != 7:
        errors.append(
            f"child_sheet_count:{len(child_files)}!=7"
        )

    for path in child_files:
        text = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
        refs = {
            match.group(1)
            for match in REFERENCE_RE.finditer(text)
            if DESIGNATOR_RE.fullmatch(
                match.group(1)
            )
        }

        for ref in refs:
            locations[ref].append(path.name)
            if not ref.startswith("#"):
                physical.add(ref)

    duplicates = {
        ref: files
        for ref, files in locations.items()
        if len(files) > 1
        and not ref.startswith("#")
    }
    for ref, files in sorted(duplicates.items()):
        errors.append(
            "duplicate_designator:"
            + ref
            + ":"
            + ",".join(files)
        )

    return physical, dict(locations), errors


def validate(
    *,
    system_root: str | Path,
    generated_dir: str | Path,
) -> dict:
    system = Path(system_root)
    generated = Path(generated_dir)
    errors: list[str] = []
    warnings: list[str] = []

    bom_path = (
        system
        / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    footprint_path = (
        system
        / "FOOTPRINT_ASSIGNMENT_SYS_002.csv"
    )
    hierarchy_path = (
        system
        / "HIERARCHY_INTERFACE_SYS_001.csv"
    )
    power_tree_path = (
        system
        / "POWER_TREE_SYS_001.csv"
    )
    mechanical_path = (
        system
        / "altium"
        / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv"
    )
    placement_path = (
        system
        / "altium"
        / "ALTIUM_PLACEMENT_COORD_SYS_002.csv"
    )

    required = [
        bom_path,
        footprint_path,
        hierarchy_path,
        power_tree_path,
        mechanical_path,
        placement_path,
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    physical_refs, locations, ref_errors = (
        schematic_refs(generated)
    )
    errors.extend(ref_errors)

    bom_rows = read_csv(bom_path)
    footprint_rows = read_csv(footprint_path)
    hierarchy_rows = read_csv(hierarchy_path)
    power_rows = read_csv(power_tree_path)
    mechanical_rows = read_csv(mechanical_path)
    placement_rows = read_csv(placement_path)

    bom, bom_errors = unique_by(
        bom_rows,
        "ref",
    )
    footprints, fp_errors = unique_by(
        footprint_rows,
        "ref",
    )
    errors.extend(bom_errors)
    errors.extend(fp_errors)

    bom_refs = set(bom)
    footprint_refs = set(footprints)

    for ref in sorted(physical_refs - bom_refs):
        errors.append(f"bom_missing_ref:{ref}")
    for ref in sorted(bom_refs - physical_refs):
        errors.append(f"bom_extra_ref:{ref}")

    for ref in sorted(
        physical_refs - footprint_refs
    ):
        errors.append(
            f"footprint_missing_ref:{ref}"
        )
    for ref in sorted(
        footprint_refs - physical_refs
    ):
        errors.append(
            f"footprint_extra_ref:{ref}"
        )

    for ref, row in footprints.items():
        if (
            str(row.get("status", "")).strip()
            != "LOCKED"
        ):
            errors.append(
                f"footprint_not_locked:{ref}"
            )
        if not str(
            row.get("footprint_id", "")
        ).strip():
            errors.append(
                f"footprint_blank:{ref}"
            )

    if "J2" in physical_refs:
        errors.append("obsolete_duplicate_radar_power_connector:J2")

    required_mcu_decoupling = {
        f"C{number}"
        for number in range(100, 114)
    }
    missing_vdd_caps = sorted(
        required_mcu_decoupling
        - physical_refs
    )
    for ref in missing_vdd_caps:
        errors.append(
            f"missing_mcu_vdd_decoupling:{ref}"
        )

    for ref in {"C114", "C115", "C64", "C65"}:
        if ref not in physical_refs:
            errors.append(
                f"missing_required_decoupling:{ref}"
            )

    if "FB2" in bom_refs:
        errors.append("obsolete_ref:FB2")

    if any(
        str(row.get("output_net", "")).strip()
        == "IO_HIGH_CURRENT"
        for row in power_rows
    ):
        errors.append(
            "obsolete_power_branch:IO_HIGH_CURRENT"
        )

    radar_source = [
        row
        for row in hierarchy_rows
        if str(row.get("sheet", "")).strip()
        == "POWER_INPUT"
        and str(
            row.get("net_name", "")
        ).strip()
        == "RADAR_12V"
    ]
    if len(radar_source) != 1:
        errors.append(
            "radar_12v_source_count"
        )
    else:
        row = radar_source[0]
        if (
            str(row.get("anchor_ref", "")).strip()
            != "U7"
            or str(
                row.get("anchor_pin", "")
            ).strip()
            != "6"
        ):
            errors.append(
                "radar_12v_source_anchor"
            )

    outline_rows = [
        row
        for row in mechanical_rows
        if str(row.get("kind", "")).strip()
        == "BOARD"
        and str(row.get("id", "")).strip()
        == "OUTLINE"
    ]
    if len(outline_rows) != 1:
        errors.append("board_outline")
        board_width = 0.0
        board_height = 0.0
    else:
        outline = outline_rows[0]
        try:
            board_width = float(
                outline.get("width_mm", "")
            )
            board_height = float(
                outline.get("height_mm", "")
            )
        except ValueError:
            board_width = 0.0
            board_height = 0.0
            errors.append(
                "board_outline_parse"
            )

    hard_refs: set[str] = set()
    for row in placement_rows:
        ref = str(row.get("ref", "")).strip()
        lock = str(
            row.get("lock_level", "")
        ).strip()

        if ref not in physical_refs:
            errors.append(
                f"placement_unknown_ref:{ref}"
            )

        if lock != "HARD":
            continue

        hard_refs.add(ref)
        try:
            x = float(row.get("x_mm", ""))
            y = float(row.get("y_mm", ""))
        except ValueError:
            errors.append(
                f"placement_coord:{ref}"
            )
            continue

        if not (
            0.0 <= x <= board_width
            and 0.0 <= y <= board_height
        ):
            errors.append(
                f"placement_outside_board:{ref}"
            )

    required_hard = {
        "J1",
        "D1",
        "U6",
        "U5",
        "L1",
        "U7",
        "J5",
        "J4",
        "D4",
        "U4",
        "U1",
        "Y1",
        "U2",
        "U8",
        "J8",
        "D8",
        "U3",
        "Y2",
        "D3",
        "J6",
        "J10",
    }
    for ref in sorted(
        required_hard - hard_refs
    ):
        errors.append(
            f"missing_hard_placement:{ref}"
        )

    if board_width != 100.0:
        warnings.append(
            f"evt_board_width:{board_width}"
        )
    if board_height != 80.0:
        warnings.append(
            f"evt_board_height:{board_height}"
        )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS"
            if not errors
            else "FAIL"
        ),
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "physical_ref_count":
            len(physical_refs),
        "bom_ref_count": len(bom_refs),
        "footprint_ref_count":
            len(footprint_refs),
        "hard_placement_count":
            len(hard_refs),
        "mcu_vdd_decoupling_count":
            len(
                required_mcu_decoupling
                & physical_refs
            ),
        "board_width_mm": board_width,
        "board_height_mm": board_height,
        "designator_locations": locations,
        "notes": [
            (
                "PASS verifies Altium pre-layout data consistency; "
                "native Altium equivalence is a separate gate."
            ),
            (
                "The 100x80mm outline is EVT_ROUTING_LOCKED for "
                "native layout datum use; it does not constitute a "
                "production mechanical freeze."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--system-root",
        required=True,
    )
    parser.add_argument(
        "--generated-dir",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        generated_dir=args.generated_dir,
    )
    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
