from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCHEMA = "ALTIUM-ROOM-GATE-001"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    altium = root / "altium"
    room_path = altium / "ALTIUM_ROOMS_SYS_001.csv"
    placement_path = altium / "ALTIUM_PLACEMENT_COORD_SYS_002.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path in (room_path, placement_path):
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }

    room_rows = rows(room_path)
    placement_rows = rows(placement_path)

    rooms: dict[str, dict[str, object]] = {}
    zone_to_room: dict[str, str] = {}

    for row in room_rows:
        room_id = str(row.get("room_id", "")).strip()
        zone_id = str(row.get("zone_id", "")).strip()
        if not room_id or not zone_id:
            errors.append("blank_room_or_zone")
            continue
        if room_id in rooms:
            errors.append(f"duplicate_room:{room_id}")
            continue
        if zone_id in zone_to_room:
            errors.append(f"duplicate_room_zone:{zone_id}")
            continue

        try:
            x_min = float(row["x_min_mm"])
            y_min = float(row["y_min_mm"])
            x_max = float(row["x_max_mm"])
            y_max = float(row["y_max_mm"])
        except ValueError:
            errors.append(f"room_coord:{room_id}")
            continue

        if not (x_min < x_max and y_min < y_max):
            errors.append(f"invalid_room_bounds:{room_id}")

        if str(row.get("status", "")).strip() != "EVT_PROVISIONAL":
            errors.append(f"room_status:{room_id}")

        rooms[room_id] = {
            "zone_id": zone_id,
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
        }
        zone_to_room[zone_id] = room_id

    expected_zones = {
        "ZONE_PWR",
        "ZONE_CAN",
        "ZONE_MCU",
        "ZONE_IMU",
        "ZONE_GNSS",
        "ZONE_ETH",
        "ZONE_DEBUG",
    }
    if set(zone_to_room) != expected_zones:
        errors.append(
            "room_zone_set:"
            + ",".join(sorted(set(zone_to_room)))
        )

    hard_checked = 0
    local_refs = 0

    for row in placement_rows:
        ref = str(row.get("ref", "")).strip()
        zone = str(row.get("zone", "")).strip()
        lock = str(row.get("lock_level", "")).strip()

        room_id = zone_to_room.get(zone)
        if room_id is None:
            errors.append(f"placement_zone_without_room:{ref}:{zone}")
            continue

        x_text = str(row.get("x_mm", "")).strip()
        y_text = str(row.get("y_mm", "")).strip()

        if lock == "LOCAL":
            local_refs += 1
            if x_text or y_text:
                warnings.append(f"local_ref_has_absolute_coordinate:{ref}")
            continue

        if not x_text or not y_text:
            if lock == "HARD":
                errors.append(f"hard_ref_missing_coordinate:{ref}")
            continue

        x = float(x_text)
        y = float(y_text)
        room = rooms[room_id]
        inside = (
            float(room["x_min"]) <= x <= float(room["x_max"])
            and float(room["y_min"]) <= y <= float(room["y_max"])
        )

        if not inside:
            errors.append(
                f"outside_room:{ref}:{room_id}:{x:.3f},{y:.3f}"
            )

        if lock == "HARD":
            hard_checked += 1

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "room_count": len(rooms),
        "hard_checked_count": hard_checked,
        "local_ref_count": local_refs,
        "zone_to_room": zone_to_room,
        "notes": [
            (
                "Rooms are EVT provisional placement controls only and do "
                "not represent a production enclosure/mechanical freeze."
            ),
            (
                "LOCAL parts inherit the room from their zone and receive "
                "exact coordinates during native Altium placement."
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
