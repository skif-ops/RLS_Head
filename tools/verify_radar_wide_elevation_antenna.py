from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


TARGET_NETS = {
    204: "TI_RX1",
    205: "TI_RX2",
    206: "TI_RX3",
    207: "TI_RX4",
    220: "TI_TX1",
    221: "TI_TX2",
    222: "TI_TX3",
    223: "TI_TX4",
}
RF_COPPER_TO_VIA_CLEARANCE_MM = 0.30
BOARD_CENTER_MM = (50.0, 50.0)
BOARD_RADIUS_MM = 39.5
BOARD_EDGE_MARGIN_MM = 0.25
TOUCH_TOLERANCE_MM = 0.003


def field(line: str, name: str) -> str | None:
    match = re.search(rf"\|{re.escape(name)}=([^|\r\n]+)", line)
    return match.group(1) if match else None


def mm(line: str, name: str) -> float:
    raw = field(line, name)
    if raw is None or not raw.endswith("mil"):
        raise ValueError(f"missing {name}=...mil in {line[:120]}")
    return float(raw[:-3]) * 0.0254


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Track:
    net: int
    index: int
    x1: float
    y1: float
    x2: float
    y2: float
    width: float


@dataclass(frozen=True)
class Fill:
    net: int
    index: int
    x1: float
    y1: float
    x2: float
    y2: float


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> bool:
    return (
        min(a[0], b[0]) - TOUCH_TOLERANCE_MM <= p[0] <= max(a[0], b[0]) + TOUCH_TOLERANCE_MM
        and min(a[1], b[1]) - TOUCH_TOLERANCE_MM <= p[1] <= max(a[1], b[1]) + TOUCH_TOLERANCE_MM
        and abs(orientation(a, b, p)) <= TOUCH_TOLERANCE_MM
    )


def segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1, o2 = orientation(a, b, c), orientation(a, b, d)
    o3, o4 = orientation(c, d, a), orientation(c, d, b)
    if ((o1 > 0 > o2) or (o2 > 0 > o1)) and ((o3 > 0 > o4) or (o4 > 0 > o3)):
        return True
    return any(
        (
            abs(value) <= TOUCH_TOLERANCE_MM
            and on_segment(start, end, point)
        )
        for value, start, end, point in (
            (o1, a, b, c),
            (o2, a, b, d),
            (o3, c, d, a),
            (o4, c, d, b),
        )
    )


def point_segment_distance(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.dist(point, start)
    t = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq))
    projection = (start[0] + t * dx, start[1] + t * dy)
    return math.dist(point, projection)


def segment_distance(first: Track, second: Track) -> float:
    a, b = (first.x1, first.y1), (first.x2, first.y2)
    c, d = (second.x1, second.y1), (second.x2, second.y2)
    if segments_intersect(a, b, c, d):
        return 0.0
    return min(
        point_segment_distance(a, c, d),
        point_segment_distance(b, c, d),
        point_segment_distance(c, a, b),
        point_segment_distance(d, a, b),
    )


def segment_intersects_box(track: Track, box: tuple[float, float, float, float], expansion: float = 0.0) -> bool:
    left, bottom, right, top = box
    left -= expansion
    bottom -= expansion
    right += expansion
    top += expansion
    a, b = (track.x1, track.y1), (track.x2, track.y2)
    if left <= a[0] <= right and bottom <= a[1] <= top:
        return True
    if left <= b[0] <= right and bottom <= b[1] <= top:
        return True
    corners = ((left, bottom), (right, bottom), (right, top), (left, top))
    return any(segments_intersect(a, b, corners[index], corners[(index + 1) % 4]) for index in range(4))


def primitives_touch(first: Track | Fill, second: Track | Fill) -> bool:
    if isinstance(first, Track) and isinstance(second, Track):
        return segment_distance(first, second) <= first.width / 2.0 + second.width / 2.0 + TOUCH_TOLERANCE_MM
    if isinstance(first, Fill) and isinstance(second, Fill):
        return not (
            first.x2 < second.x1 - TOUCH_TOLERANCE_MM
            or second.x2 < first.x1 - TOUCH_TOLERANCE_MM
            or first.y2 < second.y1 - TOUCH_TOLERANCE_MM
            or second.y2 < first.y1 - TOUCH_TOLERANCE_MM
        )
    track = first if isinstance(first, Track) else second
    fill = second if isinstance(second, Fill) else first
    return segment_intersects_box(
        track,
        (fill.x1, fill.y1, fill.x2, fill.y2),
        track.width / 2.0 + TOUCH_TOLERANCE_MM,
    )


def parse_target_geometry(lines: list[str]) -> tuple[dict[int, list[Track]], dict[int, list[Fill]]]:
    tracks: dict[int, list[Track]] = defaultdict(list)
    fills: dict[int, list[Fill]] = defaultdict(list)
    for line in lines:
        net_raw = field(line, "NET")
        if net_raw is None or int(net_raw) not in TARGET_NETS or field(line, "LAYER") != "TOP":
            continue
        net = int(net_raw)
        index = int(field(line, "INDEXFORSAVE") or -1)
        if field(line, "RECORD") == "Track":
            tracks[net].append(Track(net, index, mm(line, "X1"), mm(line, "Y1"), mm(line, "X2"), mm(line, "Y2"), mm(line, "WIDTH")))
        elif field(line, "RECORD") == "Fill":
            x1, x2 = sorted((mm(line, "X1"), mm(line, "X2")))
            y1, y2 = sorted((mm(line, "Y1"), mm(line, "Y2")))
            fills[net].append(Fill(net, index, x1, y1, x2, y2))
    return tracks, fills


def connected_component_size(primitives: list[Track | Fill]) -> int:
    if not primitives:
        return 0
    graph: dict[int, list[int]] = defaultdict(list)
    for first_index, first in enumerate(primitives):
        for second_index in range(first_index + 1, len(primitives)):
            if primitives_touch(first, primitives[second_index]):
                graph[first_index].append(second_index)
                graph[second_index].append(first_index)
    seen = {0}
    queue = deque([0])
    while queue:
        current = queue.popleft()
        for neighbor in graph[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen)


def bbox_intersects_rf_zone(line: str, rf_zone: tuple[float, float, float, float]) -> bool:
    record = field(line, "RECORD")
    if record == "Track":
        track = Track(
            int(field(line, "NET") or -1),
            int(field(line, "INDEXFORSAVE") or -1),
            mm(line, "X1"),
            mm(line, "Y1"),
            mm(line, "X2"),
            mm(line, "Y2"),
            mm(line, "WIDTH"),
        )
        return segment_intersects_box(track, rf_zone, track.width / 2.0)
    if record == "Fill":
        left, right = sorted((mm(line, "X1"), mm(line, "X2")))
        bottom, top = sorted((mm(line, "Y1"), mm(line, "Y2")))
    elif record in {"Pad", "Via"}:
        x, y = mm(line, "X"), mm(line, "Y")
        x_size_raw = field(line, "XSIZE") or field(line, "DIAMETER")
        y_size_raw = field(line, "YSIZE") or field(line, "DIAMETER")
        if x_size_raw is None or y_size_raw is None or not x_size_raw.endswith("mil") or not y_size_raw.endswith("mil"):
            return False
        x_radius = float(x_size_raw[:-3]) * 0.0254 / 2.0
        y_radius = float(y_size_raw[:-3]) * 0.0254 / 2.0
        left, right, bottom, top = x - x_radius, x + x_radius, y - y_radius, y + y_radius
    elif record == "Arc":
        x, y, radius = mm(line, "LOCATION.X"), mm(line, "LOCATION.Y"), mm(line, "RADIUS")
        left, right, bottom, top = x - radius, x + radius, y - radius, y + radius
    else:
        return False
    zone_left, zone_bottom, zone_right, zone_top = rf_zone
    return not (right < zone_left or left > zone_right or top < zone_bottom or bottom > zone_top)


def inside_board(x: float, y: float, allowance: float = 0.0) -> bool:
    return math.hypot(x - BOARD_CENTER_MM[0], y - BOARD_CENTER_MM[1]) + allowance <= BOARD_RADIUS_MM - BOARD_EDGE_MARGIN_MM


def point_box_distance(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
    left, bottom, right, top = box
    dx = max(left - point[0], 0.0, point[0] - right)
    dy = max(bottom - point[1], 0.0, point[1] - top)
    return math.hypot(dx, dy)


def via_clearance_to_target_copper(
    x: float,
    y: float,
    radius: float,
    target_tracks: list[Track],
    target_fills: list[Fill],
) -> tuple[float, str, int, str]:
    candidates = [
        (
            point_segment_distance((x, y), (track.x1, track.y1), (track.x2, track.y2))
            - radius
            - track.width / 2.0,
            "Track",
            track.index,
            TARGET_NETS[track.net],
        )
        for track in target_tracks
    ]
    candidates.extend(
        (
            point_box_distance((x, y), (fill.x1, fill.y1, fill.x2, fill.y2)) - radius,
            "Fill",
            fill.index,
            TARGET_NETS[fill.net],
        )
        for fill in target_fills
    )
    return min(candidates, key=lambda item: item[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the D79 eight-element wide-elevation antenna candidate")
    parser.add_argument("--pcb", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    lines = args.pcb.read_bytes().decode("cp1252").splitlines()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tracks, fills = parse_target_geometry(lines)
    all_target_fills = [fill for items in fills.values() for fill in items]
    rf_zone = (
        min(fill.x1 for fill in all_target_fills) - 0.50,
        min(fill.y1 for fill in all_target_fills) - 0.50,
        max(fill.x2 for fill in all_target_fills) + 0.50,
        max(fill.y2 for fill in all_target_fills) + 0.50,
    )
    errors: list[str] = []
    channel_results: list[dict[str, object]] = []

    for net, name in TARGET_NETS.items():
        generated_tracks = [track for track in tracks[net] if track.index >= 8000]
        primitives: list[Track | Fill] = [*generated_tracks, *fills[net]]
        component_size = connected_component_size(primitives)
        connected = bool(primitives) and component_size == len(primitives)
        if len(fills[net]) != 8:
            errors.append(f"{name}: expected 8 radiators, found {len(fills[net])}")
        if not connected:
            errors.append(f"{name}: generated feed and radiators are not one connected copper component")
        if any(
            not inside_board(x, y)
            for fill in fills[net]
            for x, y in ((fill.x1, fill.y1), (fill.x1, fill.y2), (fill.x2, fill.y1), (fill.x2, fill.y2))
        ):
            errors.append(f"{name}: a radiator corner is outside the D79 board margin")
        channel_results.append(
            {
                "net": name,
                "radiator_count": len(fills[net]),
                "generated_feed_track_count": len(generated_tracks),
                "single_connected_component": connected,
            }
        )

    duplicate_indices: list[dict[str, object]] = []
    seen_indices: dict[tuple[str, int], int] = {}
    for line_number, line in enumerate(lines, start=1):
        record = field(line, "RECORD")
        index_raw = field(line, "INDEXFORSAVE")
        if record not in {"Track", "Fill", "Via", "Arc", "Pad"} or index_raw is None:
            continue
        key = (record, int(index_raw))
        if key in seen_indices:
            duplicate_indices.append({"record": record, "index": int(index_raw), "lines": [seen_indices[key], line_number]})
        else:
            seen_indices[key] = line_number
    if duplicate_indices:
        errors.append(f"duplicate INDEXFORSAVE values: {len(duplicate_indices)}")

    old_tracks = [
        int(field(line, "INDEXFORSAVE") or -1)
        for line in lines
        if field(line, "RECORD") == "Track"
        and field(line, "NET") is not None
        and int(field(line, "NET") or -1) in TARGET_NETS
        and 5199 <= int(field(line, "INDEXFORSAVE") or -1) <= 5246
    ]
    if old_tracks:
        errors.append(f"obsolete two-element antenna tracks remain: {old_tracks}")

    intrusions: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        record = field(line, "RECORD")
        layer = field(line, "LAYER")
        if record not in {"Track", "Fill", "Pad", "Arc"}:
            continue
        on_top = layer == "TOP"
        net = int(field(line, "NET") or -1)
        if on_top and net not in TARGET_NETS and bbox_intersects_rf_zone(line, rf_zone):
            intrusions.append(
                {
                    "line": line_number,
                    "record": record,
                    "index": int(field(line, "INDEXFORSAVE") or -1),
                    "net": net,
                }
            )
    if intrusions:
        errors.append(f"non-antenna Top copper in RF zone: {len(intrusions)} primitives")

    target_tracks = [track for items in tracks.values() for track in items if track.index >= 8000]
    target_fills = all_target_fills
    all_routed_tracks: list[tuple[int, int, str, float, float, float, float]] = []
    for line in lines:
        if field(line, "RECORD") != "Track":
            continue
        all_routed_tracks.append(
            (
                int(field(line, "NET") or -1),
                int(field(line, "INDEXFORSAVE") or -1),
                field(line, "LAYER") or "",
                mm(line, "X1"),
                mm(line, "Y1"),
                mm(line, "X2"),
                mm(line, "Y2"),
            )
        )
    near_vias: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        if field(line, "RECORD") != "Via" or int(field(line, "NET") or -1) in TARGET_NETS:
            continue
        if "TOP" not in {field(line, "STARTLAYER"), field(line, "ENDLAYER")}:
            continue
        x, y = mm(line, "X"), mm(line, "Y")
        diameter_raw = field(line, "DIAMETER")
        if diameter_raw is None or not diameter_raw.endswith("mil"):
            continue
        radius = float(diameter_raw[:-3]) * 0.0254 / 2.0
        clearance, nearest_record, nearest_index, nearest_net = via_clearance_to_target_copper(
            x, y, radius, target_tracks, target_fills
        )
        if clearance < RF_COPPER_TO_VIA_CLEARANCE_MM:
            via_net = int(field(line, "NET") or -1)
            incident_tracks = [
                {"index": index, "layer": layer}
                for net, index, layer, x1, y1, x2, y2 in all_routed_tracks
                if net == via_net
                and (
                    math.hypot(x1 - x, y1 - y) <= TOUCH_TOLERANCE_MM
                    or math.hypot(x2 - x, y2 - y) <= TOUCH_TOLERANCE_MM
                )
            ]
            near_vias.append(
                {
                    "line": line_number,
                    "index": int(field(line, "INDEXFORSAVE") or -1),
                    "net": via_net,
                    "x_mm": x,
                    "y_mm": y,
                    "clearance_to_target_copper_mm": clearance,
                    "nearest_target_record": nearest_record,
                    "nearest_target_index": nearest_index,
                    "nearest_target_net": nearest_net,
                    "incident_tracks": incident_tracks,
                }
            )
    if near_vias:
        errors.append(f"non-antenna vias inside {RF_COPPER_TO_VIA_CLEARANCE_MM:.2f} mm RF copper clearance: {len(near_vias)}")

    actual_hash = sha256(args.pcb)
    hash_matches = actual_hash == manifest.get("output_sha256")
    if not hash_matches:
        errors.append("PCB SHA-256 does not match the calculation manifest")

    report = {
        "schema": "radar_wide_elevation_antenna_preflight_v1",
        "revision": manifest.get("revision"),
        "status": "PASS" if not errors else "FAIL",
        "pcb": str(args.pcb.resolve()),
        "pcb_sha256": actual_hash,
        "manifest_hash_matches": hash_matches,
        "required_elements_per_channel": 8,
        "channel_count": len(TARGET_NETS),
        "total_radiator_count": sum(len(items) for items in fills.values()),
        "channels": channel_results,
        "rf_zone_mm": {"left": rf_zone[0], "bottom": rf_zone[1], "right": rf_zone[2], "top": rf_zone[3]},
        "non_antenna_top_copper_in_rf_zone": intrusions,
        "required_rf_copper_to_via_clearance_mm": RF_COPPER_TO_VIA_CLEARANCE_MM,
        "non_antenna_vias_inside_rf_copper_clearance": near_vias,
        "obsolete_two_element_track_indices": old_tracks,
        "duplicate_indices": duplicate_indices,
        "errors": errors,
        "native_altium_drc": "PENDING",
        "full_wave_em": "REQUIRED_NOT_PERFORMED",
        "production_authority": "NOT_AUTHORIZED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(args.output), "errors": errors}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
