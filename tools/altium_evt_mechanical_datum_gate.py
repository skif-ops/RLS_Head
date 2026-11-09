from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


SCHEMA = "ALTIUM-EVT-MECHANICAL-DATUM-GATE-001"
LOCK_STATUS = "EVT_ROUTING_LOCKED"
CANDIDATE_STATUS = "ECO_CANDIDATE"
ALLOWED_DATUM_STATUSES = {LOCK_STATUS, CANDIDATE_STATUS}

EXPECTED_BOARD = {
    "x_mm": 0.0,
    "y_mm": 0.0,
    "width_mm": 90.0,
    "height_mm": 70.0,
    "corner_radius_mm": 3.0,
}

EXPECTED_HOLES = {
    "H1": (5.0, 5.0, 3.2),
    "H2": (85.0, 5.0, 3.2),
    "H3": (5.0, 65.0, 3.2),
    "H4": (85.0, 65.0, 3.2),
}

EXPECTED_CONNECTOR_DATUMS = {
    "J1": ("LEFT", 5.0, 14.0),
    "J4": ("RIGHT", 85.0, 29.0),
    "J5": ("RIGHT", 85.0, 14.0),
    "J6": ("RIGHT", 85.0, 54.0),
    "J8": ("LEFT", 5.0, 57.0),
    "J10": ("BOTTOM", 45.0, 5.0),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def parse_float(value: object, *, field: str, errors: list[str]) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        errors.append(f"invalid_number:{field}")
        return math.nan


def close(a: float, b: float, tol: float = 1e-6) -> bool:
    return not math.isnan(a) and abs(a - b) <= tol


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    mechanical_path = (
        root / "altium" / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv"
    )
    placement_path = (
        root / "altium" / "ALTIUM_PLACEMENT_COORD_SYS_002.csv"
    )

    errors: list[str] = []
    warnings: list[str] = []
    datum_statuses: list[str] = []

    for path in (mechanical_path, placement_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
            "evt_routing_datums_locked": False,
            "production_mechanical_freeze": False,
        }

    mechanical = read_csv(mechanical_path)
    placements = read_csv(placement_path)

    def mechanical_row(kind: str, row_id: str) -> dict[str, str] | None:
        matches = [
            row
            for row in mechanical
            if str(row.get("kind", "")).strip() == kind
            and str(row.get("id", "")).strip() == row_id
        ]
        if len(matches) != 1:
            errors.append(
                f"mechanical_row_count:{kind}:{row_id}:{len(matches)}"
            )
            return None
        return matches[0]

    outline = mechanical_row("BOARD", "OUTLINE")
    corner = mechanical_row("BOARD", "CORNER_RADIUS")
    thickness = mechanical_row("BOARD", "THICKNESS")
    edge_rule = mechanical_row("CONNECTOR_RULE", "MICROFIT_EDGE")

    width = height = math.nan
    if outline is not None:
        x = parse_float(outline.get("x_mm"), field="OUTLINE.x_mm", errors=errors)
        y = parse_float(outline.get("y_mm"), field="OUTLINE.y_mm", errors=errors)
        width = parse_float(
            outline.get("width_mm"),
            field="OUTLINE.width_mm",
            errors=errors,
        )
        height = parse_float(
            outline.get("height_mm"),
            field="OUTLINE.height_mm",
            errors=errors,
        )
        for field, actual, expected in (
            ("x_mm", x, EXPECTED_BOARD["x_mm"]),
            ("y_mm", y, EXPECTED_BOARD["y_mm"]),
            ("width_mm", width, EXPECTED_BOARD["width_mm"]),
            ("height_mm", height, EXPECTED_BOARD["height_mm"]),
        ):
            if not close(actual, expected):
                errors.append(f"board_outline_baseline:{field}")
        outline_status = str(outline.get("status", "")).strip()
        datum_statuses.append(outline_status)
        if outline_status not in ALLOWED_DATUM_STATUSES:
            errors.append("board_outline_status")

    corner_radius = math.nan
    if corner is not None:
        corner_radius = parse_float(
            corner.get("height_mm"),
            field="CORNER_RADIUS.height_mm",
            errors=errors,
        )
        if not close(corner_radius, EXPECTED_BOARD["corner_radius_mm"]):
            errors.append("corner_radius_baseline")
        corner_status = str(corner.get("status", "")).strip()
        datum_statuses.append(corner_status)
        if corner_status not in ALLOWED_DATUM_STATUSES:
            errors.append("corner_radius_status")

    board_thickness = math.nan
    if thickness is not None:
        board_thickness = parse_float(
            thickness.get("height_mm"),
            field="THICKNESS.height_mm",
            errors=errors,
        )
        if not close(board_thickness, 1.6):
            errors.append("board_thickness_evt_baseline")
        if str(thickness.get("status", "")).strip() != "LOCKED_FOR_EVT":
            errors.append("board_thickness_not_locked_for_evt")

    edge_limit = 10.16
    if edge_rule is not None:
        edge_limit = parse_float(
            edge_rule.get("height_mm"),
            field="MICROFIT_EDGE.height_mm",
            errors=errors,
        )
        if math.isnan(edge_limit):
            edge_limit = 10.16
        if str(edge_rule.get("status", "")).strip() != "LOCKED_FOR_EVT":
            errors.append("connector_edge_rule_not_locked_for_evt")

    hole_records: dict[str, dict] = {}
    min_hole_edge_ligament = math.inf
    for hole_id, (expected_x, expected_y, expected_diameter) in (
        EXPECTED_HOLES.items()
    ):
        row = mechanical_row("HOLE", hole_id)
        if row is None:
            continue

        x = parse_float(row.get("x_mm"), field=f"{hole_id}.x_mm", errors=errors)
        y = parse_float(row.get("y_mm"), field=f"{hole_id}.y_mm", errors=errors)
        diameter = parse_float(
            row.get("diameter_mm"),
            field=f"{hole_id}.diameter_mm",
            errors=errors,
        )

        if not close(x, expected_x) or not close(y, expected_y):
            errors.append(f"mount_hole_position_baseline:{hole_id}")
        if not close(diameter, expected_diameter):
            errors.append(f"mount_hole_diameter_baseline:{hole_id}")
        hole_status = str(row.get("status", "")).strip()
        datum_statuses.append(hole_status)
        if hole_status not in ALLOWED_DATUM_STATUSES:
            errors.append(f"mount_hole_status:{hole_id}")

        if not any(math.isnan(value) for value in (x, y, diameter, width, height)):
            radius = diameter / 2.0
            ligament = min(
                x - radius,
                width - x - radius,
                y - radius,
                height - y - radius,
            )
            min_hole_edge_ligament = min(min_hole_edge_ligament, ligament)
            if ligament < 3.0:
                errors.append(
                    f"mount_hole_edge_ligament:{hole_id}:{ligament:.3f}<3.000"
                )

        hole_records[hole_id] = {
            "x_mm": x,
            "y_mm": y,
            "diameter_mm": diameter,
        }

    placement_by_ref: dict[str, dict[str, str]] = {}
    for row in placements:
        ref = str(row.get("ref", "")).strip()
        if not ref:
            continue
        if ref in placement_by_ref:
            errors.append(f"duplicate_placement_ref:{ref}")
        placement_by_ref[ref] = row

    connector_records: dict[str, dict] = {}
    for ref, (expected_edge, expected_x, expected_y) in (
        EXPECTED_CONNECTOR_DATUMS.items()
    ):
        row = placement_by_ref.get(ref)
        if row is None:
            errors.append(f"missing_connector_datum:{ref}")
            continue

        x = parse_float(row.get("x_mm"), field=f"{ref}.x_mm", errors=errors)
        y = parse_float(row.get("y_mm"), field=f"{ref}.y_mm", errors=errors)
        edge = str(row.get("edge", "")).strip().upper()
        lock = str(row.get("lock_level", "")).strip()
        status = str(row.get("status", "")).strip()

        if edge != expected_edge:
            errors.append(f"connector_edge_baseline:{ref}")
        if not close(x, expected_x) or not close(y, expected_y):
            errors.append(f"connector_position_baseline:{ref}")
        if lock != "HARD":
            errors.append(f"connector_datum_not_hard:{ref}")
        datum_statuses.append(status)
        if status not in ALLOWED_DATUM_STATUSES:
            errors.append(f"connector_datum_status:{ref}")

        distance = math.nan
        if not any(math.isnan(value) for value in (x, y, width, height)):
            if edge == "LEFT":
                distance = x
            elif edge == "RIGHT":
                distance = width - x
            elif edge == "BOTTOM":
                distance = y
            elif edge == "TOP":
                distance = height - y
            else:
                errors.append(f"connector_unknown_edge:{ref}:{edge}")

            if not math.isnan(distance) and distance > edge_limit:
                errors.append(
                    f"connector_edge_access:{ref}:{distance:.3f}>{edge_limit:.3f}"
                )

        connector_records[ref] = {
            "edge": edge,
            "x_mm": x,
            "y_mm": y,
            "edge_distance_mm": (
                None if math.isnan(distance) else round(distance, 3)
            ),
        }

    status = "PASS" if not errors else "FAIL"
    datums_locked = (
        status == "PASS"
        and bool(datum_statuses)
        and all(item == LOCK_STATUS for item in datum_statuses)
    )
    if status == "PASS" and not datums_locked:
        warnings.append("compact_candidate_requires_native_drc_before_lock")
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "evt_routing_datums_locked": datums_locked,
        "compact_candidate_validated": status == "PASS",
        "production_mechanical_freeze": False,
        "board_baseline": {
            "origin_mm": [EXPECTED_BOARD["x_mm"], EXPECTED_BOARD["y_mm"]],
            "width_mm": width,
            "height_mm": height,
            "corner_radius_mm": corner_radius,
            "thickness_mm": board_thickness,
        },
        "mounting_holes": hole_records,
        "connector_datums": connector_records,
        "minimum_mount_hole_edge_ligament_mm": (
            None
            if math.isinf(min_hole_edge_ligament)
            else round(min_hole_edge_ligament, 3)
        ),
        "notes": [
            (
                "PASS validates the repository board envelope, mounting pattern "
                "and primary edge-connector anchors. ECO_CANDIDATE remains "
                "unlocked until native Altium placement, routing and DRC pass."
            ),
            (
                "PASS does not constitute a production mechanical freeze, "
                "enclosure/STEP fit verification or manufacturing authority."
            ),
            (
                "Production remains subject to the separate native-PcbDoc-bound "
                "ALTIUM-MECHANICAL-REVIEW-001 required by the production gate."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("system_carrier_root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.system_carrier_root)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
