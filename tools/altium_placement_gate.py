from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


SCHEMA = "ALTIUM-PLACEMENT-GATE-001"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def parse_float(value: str, *, field: str) -> float:
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    errors: list[str] = []
    warnings: list[str] = []

    mechanical_path = (
        root
        / "altium"
        / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv"
    )
    placement_path = (
        root
        / "altium"
        / "ALTIUM_PLACEMENT_COORD_SYS_002.csv"
    )
    zone_path = (
        root
        / "altium"
        / "ALTIUM_PLACEMENT_PLAN_SYS_001.csv"
    )

    for path in (mechanical_path, placement_path, zone_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    mechanical = read_csv(mechanical_path)
    placement_rows = read_csv(placement_path)
    zone_rows = read_csv(zone_path)

    zones = {
        str(row.get("zone_id", "")).strip()
        for row in zone_rows
        if str(row.get("zone_id", "")).strip()
    }

    outline = next(
        (
            row
            for row in mechanical
            if str(row.get("kind", "")).strip() == "BOARD"
            and str(row.get("id", "")).strip() == "OUTLINE"
        ),
        None,
    )
    if outline is None:
        errors.append("missing_board_outline")
        width = height = 0.0
    else:
        width = parse_float(outline["width_mm"], field="board width")
        height = parse_float(outline["height_mm"], field="board height")

    quiet = next(
        (
            row
            for row in mechanical
            if str(row.get("kind", "")).strip() == "KEEPOUT"
            and str(row.get("id", "")).strip() == "GNSS_QUIET_ZONE"
        ),
        None,
    )
    if quiet is None:
        errors.append("missing_gnss_quiet_zone")
        qx = qy = qw = qh = 0.0
    else:
        qx = parse_float(quiet["x_mm"], field="quiet x")
        qy = parse_float(quiet["y_mm"], field="quiet y")
        qw = parse_float(quiet["width_mm"], field="quiet width")
        qh = parse_float(quiet["height_mm"], field="quiet height")

    edge_rule = next(
        (
            row
            for row in mechanical
            if str(row.get("kind", "")).strip() == "CONNECTOR_RULE"
            and str(row.get("id", "")).strip() == "MICROFIT_EDGE"
        ),
        None,
    )
    if edge_rule is None:
        edge_limit = 10.16
    else:
        edge_value = next(
            (
                str(edge_rule.get(field, "")).strip()
                for field in ("width_mm", "height_mm", "diameter_mm")
                if str(edge_rule.get(field, "")).strip()
            ),
            "",
        )
        edge_limit = (
            parse_float(edge_value, field="edge limit")
            if edge_value
            else 10.16
        )

    placement: dict[str, dict] = {}
    hard_positions: dict[tuple[float, float], str] = {}

    for row in placement_rows:
        ref = str(row.get("ref", "")).strip()
        if not ref:
            errors.append("blank_placement_ref")
            continue
        if ref in placement:
            errors.append(f"duplicate_placement_ref:{ref}")
            continue

        zone = str(row.get("zone", "")).strip()
        if zone not in zones:
            errors.append(f"unknown_zone:{ref}:{zone}")

        x_text = str(row.get("x_mm", "")).strip()
        y_text = str(row.get("y_mm", "")).strip()
        lock = str(row.get("lock_level", "")).strip()

        record = dict(row)
        record["x"] = None
        record["y"] = None

        if x_text or y_text:
            if not x_text or not y_text:
                errors.append(f"partial_coordinate:{ref}")
            else:
                x = parse_float(x_text, field=f"{ref}.x")
                y = parse_float(y_text, field=f"{ref}.y")
                record["x"] = x
                record["y"] = y

                if not (0.0 <= x <= width and 0.0 <= y <= height):
                    errors.append(f"outside_board:{ref}")

                if lock == "HARD":
                    key = (x, y)
                    other = hard_positions.get(key)
                    if other is not None:
                        errors.append(
                            f"hard_coordinate_collision:{other}:{ref}"
                        )
                    hard_positions[key] = ref

        placement[ref] = record

    def point(ref: str) -> tuple[float, float]:
        item = placement.get(ref)
        if item is None:
            errors.append(f"missing_placement:{ref}")
            return (math.nan, math.nan)
        x = item.get("x")
        y = item.get("y")
        if x is None or y is None:
            errors.append(f"missing_hard_coordinate:{ref}")
            return (math.nan, math.nan)
        return (float(x), float(y))

    def inside_quiet(ref: str) -> bool:
        x, y = point(ref)
        if math.isnan(x) or math.isnan(y):
            return False
        return qx <= x <= qx + qw and qy <= y <= qy + qh

    def require_order(name: str, refs: tuple[str, ...]) -> None:
        xs = [point(ref)[0] for ref in refs]
        if any(math.isnan(value) for value in xs):
            return
        if not all(a < b for a, b in zip(xs, xs[1:])):
            errors.append(
                f"placement_order:{name}:"
                + ">".join(refs)
            )

    # Edge-access connectors: all declared edge parts must actually be
    # within the mechanical mating-edge limit.
    edge_refs: list[str] = []
    for ref, row in placement.items():
        edge = str(row.get("edge", "")).strip().upper()
        if not edge:
            continue
        x = row.get("x")
        y = row.get("y")
        if x is None or y is None:
            continue

        edge_refs.append(ref)
        if edge == "LEFT":
            distance = float(x)
        elif edge == "RIGHT":
            distance = width - float(x)
        elif edge == "BOTTOM":
            distance = float(y)
        elif edge == "TOP":
            distance = height - float(y)
        else:
            errors.append(f"unknown_edge:{ref}:{edge}")
            continue

        if distance > edge_limit:
            errors.append(
                f"edge_access:{ref}:{distance:.3f}>{edge_limit:.3f}"
            )

    # GNSS corridor is the only hard-placement domain allowed inside the
    # quiet region.
    for ref in ("J8", "D8", "U8"):
        if not inside_quiet(ref):
            errors.append(f"gnss_outside_quiet_zone:{ref}")

    for ref, row in placement.items():
        if (
            str(row.get("lock_level", "")).strip() == "HARD"
            and str(row.get("zone", "")).strip() != "ZONE_GNSS"
            and row.get("x") is not None
            and inside_quiet(ref)
        ):
            errors.append(f"non_gnss_in_quiet_zone:{ref}")

    require_order(
        "POWER_CHAIN",
        ("J1", "D1", "U6", "U5", "L1", "U7", "J5"),
    )
    require_order(
        "CAN_CORRIDOR",
        ("U4", "D4", "J4"),
    )
    require_order(
        "ETH_CORRIDOR",
        ("U3", "D3", "J6"),
    )
    require_order(
        "GNSS_CORRIDOR",
        ("J8", "D8", "U8"),
    )

    # 50 MHz source should remain geometrically between MCU and PHY.
    u1x, u1y = point("U1")
    y2x, y2y = point("Y2")
    u3x, u3y = point("U3")
    if not any(math.isnan(v) for v in (u1x, y2x, u3x)):
        if not min(u1x, u3x) < y2x < max(u1x, u3x):
            errors.append("eth_50m_source_not_between_mcu_phy")

    def distance(a: str, b: str) -> float:
        ax, ay = point(a)
        bx, by = point(b)
        if any(math.isnan(v) for v in (ax, ay, bx, by)):
            return math.nan
        return math.hypot(ax - bx, ay - by)

    # IMU isolation is a placement-level guard, not a production mechanics
    # claim. It uses only the provisional EVT coordinates already frozen in
    # the repository.
    imu_to_l1 = distance("U2", "L1")
    if not math.isnan(imu_to_l1) and imu_to_l1 < 20.0:
        errors.append(f"imu_too_close_to_buck:{imu_to_l1:.3f}")

    y2_to_u1 = distance("Y2", "U1")
    y2_to_u3 = distance("Y2", "U3")
    if not math.isnan(y2_to_u1) and y2_to_u1 > 20.0:
        errors.append(f"eth_50m_to_mcu_too_long:{y2_to_u1:.3f}")
    if not math.isnan(y2_to_u3) and y2_to_u3 > 20.0:
        errors.append(f"eth_50m_to_phy_too_long:{y2_to_u3:.3f}")

    mount_holes = [
        row
        for row in mechanical
        if str(row.get("kind", "")).strip() == "HOLE"
    ]
    if len(mount_holes) != 4:
        errors.append(f"mount_hole_count:{len(mount_holes)}!=4")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "board_width_mm": width,
        "board_height_mm": height,
        "edge_limit_mm": edge_limit,
        "edge_ref_count": len(edge_refs),
        "hard_position_count": len(hard_positions),
        "gnss_quiet_zone": {
            "x_mm": qx,
            "y_mm": qy,
            "width_mm": qw,
            "height_mm": qh,
        },
        "imu_to_buck_mm": (
            None if math.isnan(imu_to_l1) else round(imu_to_l1, 3)
        ),
        "eth_50m_to_mcu_mm": (
            None if math.isnan(y2_to_u1) else round(y2_to_u1, 3)
        ),
        "eth_50m_to_phy_mm": (
            None if math.isnan(y2_to_u3) else round(y2_to_u3, 3)
        ),
        "notes": [
            (
                "This gate validates the provisional Altium placement plan "
                "only; it does not freeze production mechanics."
            ),
            (
                "All checks use repository-defined EVT coordinates and "
                "mechanical constraints; no enclosure dimensions are inferred."
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
