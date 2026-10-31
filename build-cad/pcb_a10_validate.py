import csv
import json
import math
from pathlib import Path

import pcb_a10_planner as design


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "hardware/system_carrier/altium/routing/a10_planning_baseline"
PLAN = ROOT / "build-cad/pcb_a10_plan.json"
POWER_PLAN = ROOT / "build-cad/pcb_a10_power_plan.json"
TRACE_WIDTH = 0.20
CLEARANCE = 0.20
VIA_RADIUS = 0.30
VIA_HOLE_RADIUS = 0.15
HOLE_CLEARANCE = 0.254


def rows(name):
    with (AUDIT / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mm(value):
    return float(value) * 0.0254


def point_segment_distance(point, first, second):
    px, py = point
    ax, ay = first
    bx, by = second
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    ratio = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - ax - ratio * dx, py - ay - ratio * dy)


def orientation(first, second, third):
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def intersects(first, second, third, fourth):
    a = orientation(first, second, third)
    b = orientation(first, second, fourth)
    c = orientation(third, fourth, first)
    d = orientation(third, fourth, second)
    if ((a > 1e-9 and b < -1e-9) or (a < -1e-9 and b > 1e-9)) and ((c > 1e-9 and d < -1e-9) or (c < -1e-9 and d > 1e-9)):
        return True

    def on_segment(point, start, end):
        return (
            min(start[0], end[0]) - 1e-9 <= point[0] <= max(start[0], end[0]) + 1e-9
            and min(start[1], end[1]) - 1e-9 <= point[1] <= max(start[1], end[1]) + 1e-9
        )

    return (
        abs(a) <= 1e-9 and on_segment(third, first, second)
        or abs(b) <= 1e-9 and on_segment(fourth, first, second)
        or abs(c) <= 1e-9 and on_segment(first, third, fourth)
        or abs(d) <= 1e-9 and on_segment(second, third, fourth)
    )


def segment_distance(first, second, third, fourth):
    if intersects(first, second, third, fourth):
        return 0.0
    return min(
        point_segment_distance(first, third, fourth),
        point_segment_distance(second, third, fourth),
        point_segment_distance(third, first, second),
        point_segment_distance(fourth, first, second),
    )


def segment_rect_distance(first, second, rect):
    left, bottom, right, top = rect
    if left <= first[0] <= right and bottom <= first[1] <= top:
        return 0.0
    if left <= second[0] <= right and bottom <= second[1] <= top:
        return 0.0
    edges = (
        ((left, bottom), (right, bottom)),
        ((right, bottom), (right, top)),
        ((right, top), (left, top)),
        ((left, top), (left, bottom)),
    )
    return min(segment_distance(first, second, edge[0], edge[1]) for edge in edges)


def planned_geometry():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    power_plan = json.loads(POWER_PLAN.read_text(encoding="utf-8"))
    narrow_segments = set()
    for row in design.rows("pad_geometry.csv"):
        manual = design.MANUAL_LEADS.get((row["designator"], row["pad_name"]))
        if manual is None:
            continue
        lead = [design.row_point(row), *manual]
        for first, second in zip(lead, lead[1:]):
            narrow_segments.add(tuple(sorted((
                (round(first[0], 6), round(first[1], 6)),
                (round(second[0], 6), round(second[1], 6)),
            ))))
    tracks = []
    vias = []
    via_seen = set()

    def append_via(net, point, via_id):
        key = net, round(point[0], 6), round(point[1], 6)
        if key in via_seen:
            return
        via_seen.add(key)
        vias.append({"net": net, "point": point, "id": via_id})

    for net, routes in plan.items():
        for route_index, route in enumerate(routes):
            for index, (first, second) in enumerate(zip(route, route[1:])):
                if first[0] == second[0]:
                    key = tuple(sorted(((round(first[1], 6), round(first[2], 6)), (round(second[1], 6), round(second[2], 6)))))
                    tracks.append({
                        "net": net,
                        "layer": first[0],
                        "first": (first[1], first[2]),
                        "second": (second[1], second[2]),
                        "width": 0.15 if key in narrow_segments else TRACE_WIDTH,
                        "id": f"{net}/{route_index}/{index}",
                    })
                else:
                    append_via(net, (first[1], first[2]), f"{net}/{route_index}/{index}")
    for item in power_plan:
        route = item["route"]
        prefix = f"power-{item['designator']}-{item['pad_name']}"
        for index, (first, second) in enumerate(zip(route, route[1:])):
            if first[0] == second[0]:
                tracks.append({
                    "net": item["net"],
                    "layer": first[0],
                    "first": (first[1], first[2]),
                    "second": (second[1], second[2]),
                    "width": design.power_segment_width(
                        route,
                        index,
                        (item["designator"], item["pad_name"]),
                    ),
                    "id": f"{prefix}/{index}",
                })
            else:
                append_via(item["net"], (first[1], first[2]), f"{prefix}/{index}")
    return plan, power_plan, tracks, vias


def add_violation(items, kind, first, second, distance, required):
    items.append({
        "kind": kind,
        "first": first,
        "second": second,
        "distance_mm": round(distance, 4),
        "required_mm": round(required, 4),
    })


def validate():
    plan, power_plan, tracks, vias = planned_geometry()
    violations = []
    pads = []
    for row in rows("pad_geometry.csv"):
        layer_number = int(row["layer"])
        layers = (0, 1, 2) if float(row["hole_mil"]) > 0 or layer_number == 74 else ((0,) if layer_number == 1 else ((2,) if layer_number == 32 else ()))
        if not layers:
            continue
        pads.append({
            "net": row["net_name"],
            "layers": layers,
            "rect": design.row_rect(row),
            "id": f"{row['designator'] or '<free>'}-{row['pad_name']}",
        })

    existing_tracks = []
    for row in rows("track_inventory.csv"):
        layer_number = int(row["layer"])
        if layer_number not in (1, 3, 32):
            continue
        if row["net_name"] == "GNSS_PPS":
            continue
        first = (mm(row["x1_mil"]), mm(row["y1_mil"]))
        second = (mm(row["x2_mil"]), mm(row["y2_mil"]))
        key = tuple(sorted(((round(first[0], 2), round(first[1], 2)), (round(second[0], 2), round(second[1], 2)))))
        if key in design.MDI_REPLACED_SEGMENTS.get(row["net_name"], set()):
            continue
        existing_tracks.append({
            "net": row["net_name"],
            "layer": {1: 0, 3: 1, 32: 2}[layer_number],
            "first": first,
            "second": second,
            "radius": mm(row["width_mil"]) / 2,
            "id": f"existing-track-{row.get('index', len(existing_tracks))}",
        })
    for index, (first, second) in enumerate(design.GNSS_PPS_REROUTE):
        tracks.append({
            "net": "GNSS_PPS",
            "layer": 0,
            "first": first,
            "second": second,
            "width": 0.20,
            "id": f"proposed-gnss-{index}",
        })
    for index, (net, layer, first, second) in enumerate(design.MDI_REPLACEMENT_TRACKS):
        tracks.append({
            "net": net,
            "layer": layer,
            "first": first,
            "second": second,
            "width": 0.26,
            "id": f"proposed-mdi-{index}",
        })

    fills = []
    for row in rows("fill_inventory.csv"):
        layer_number = int(row["layer"])
        if layer_number not in (1, 3, 32):
            continue
        fills.append({
            "net": row["net_name"],
            "layer": {1: 0, 3: 1, 32: 2}[layer_number],
            "rect": tuple(mm(row[key]) for key in ("left_mil", "bottom_mil", "right_mil", "top_mil")),
            "id": f"existing-fill-{row.get('index', len(fills))}",
        })

    existing_vias = []
    for row in rows("via_inventory.csv"):
        point = (mm(row["x_mil"]), mm(row["y_mil"]))
        if row["net_name"] == "ETH_TXP" and math.hypot(point[0] - 75.0, point[1] - 55.49) < 0.02:
            continue
        existing_vias.append({
            "net": row["net_name"],
            "point": point,
            "radius": mm(row["size_mil"]) / 2,
            "hole_radius": mm(row["hole_mil"]) / 2,
            "id": f"existing-via-{row.get('index', len(existing_vias))}",
        })
    vias.append({
        "net": "ETH_TXP",
        "point": (79.0, 55.49),
        "id": "proposed-mdi-via",
    })

    for track in tracks:
        for pad in pads:
            if pad["net"] == track["net"] or track["layer"] not in pad["layers"]:
                continue
            distance = segment_rect_distance(track["first"], track["second"], pad["rect"])
            required = track["width"] / 2 + CLEARANCE
            if distance < required - 1e-6:
                add_violation(violations, "track-pad", track["id"], pad["id"], distance, required)
        for existing in existing_tracks:
            if existing["net"] == track["net"] or existing["layer"] != track["layer"]:
                continue
            distance = segment_distance(track["first"], track["second"], existing["first"], existing["second"])
            required = track["width"] / 2 + CLEARANCE + existing["radius"]
            if distance < required - 1e-6:
                add_violation(violations, "track-existing-track", track["id"], existing["id"], distance, required)
        for fill in fills:
            if fill["net"] == track["net"] or fill["layer"] != track["layer"]:
                continue
            distance = segment_rect_distance(track["first"], track["second"], fill["rect"])
            required = track["width"] / 2 + CLEARANCE
            if distance < required - 1e-6:
                add_violation(violations, "track-fill", track["id"], fill["id"], distance, required)
        for existing in existing_vias:
            if existing["net"] == track["net"]:
                continue
            distance = point_segment_distance(existing["point"], track["first"], track["second"])
            required = track["width"] / 2 + CLEARANCE + existing["radius"]
            if distance < required - 1e-6:
                add_violation(violations, "track-existing-via", track["id"], existing["id"], distance, required)

    for index, track in enumerate(tracks):
        for other in tracks[index + 1:]:
            if track["net"] == other["net"] or track["layer"] != other["layer"]:
                continue
            distance = segment_distance(track["first"], track["second"], other["first"], other["second"])
            required = track["width"] / 2 + other["width"] / 2 + CLEARANCE
            if distance < required - 1e-6:
                add_violation(violations, "track-track", track["id"], other["id"], distance, required)

    for via in vias:
        for pad in pads:
            if pad["net"] == via["net"]:
                continue
            distance = min(
                math.hypot(via["point"][0] - x, via["point"][1] - y)
                for x in (max(pad["rect"][0], min(via["point"][0], pad["rect"][2])),)
                for y in (max(pad["rect"][1], min(via["point"][1], pad["rect"][3])),)
            )
            required = VIA_RADIUS + CLEARANCE
            if distance < required - 1e-6:
                add_violation(violations, "via-pad", via["id"], pad["id"], distance, required)
        for track in tracks:
            if track["net"] == via["net"]:
                continue
            distance = point_segment_distance(via["point"], track["first"], track["second"])
            required = VIA_RADIUS + CLEARANCE + track["width"] / 2
            if distance < required - 1e-6:
                add_violation(violations, "via-track", via["id"], track["id"], distance, required)
        for existing in existing_tracks:
            if existing["net"] == via["net"]:
                continue
            distance = point_segment_distance(via["point"], existing["first"], existing["second"])
            required = VIA_RADIUS + CLEARANCE + existing["radius"]
            if distance < required - 1e-6:
                add_violation(violations, "via-existing-track", via["id"], existing["id"], distance, required)
        for fill in fills:
            if fill["net"] == via["net"]:
                continue
            distance = segment_rect_distance(via["point"], via["point"], fill["rect"])
            required = VIA_RADIUS + CLEARANCE
            if distance < required - 1e-6:
                add_violation(violations, "via-fill", via["id"], fill["id"], distance, required)
        for existing in existing_vias:
            distance = math.hypot(via["point"][0] - existing["point"][0], via["point"][1] - existing["point"][1])
            hole_required = VIA_HOLE_RADIUS + HOLE_CLEARANCE + existing["hole_radius"]
            if distance < hole_required - 1e-6:
                add_violation(violations, "via-existing-hole", via["id"], existing["id"], distance, hole_required)
            if existing["net"] != via["net"]:
                required = VIA_RADIUS + CLEARANCE + existing["radius"]
                if distance < required - 1e-6:
                    add_violation(violations, "via-existing-via", via["id"], existing["id"], distance, required)

    for index, via in enumerate(vias):
        for other in vias[index + 1:]:
            distance = math.hypot(via["point"][0] - other["point"][0], via["point"][1] - other["point"][1])
            hole_required = VIA_HOLE_RADIUS * 2 + HOLE_CLEARANCE
            if distance < hole_required - 1e-6:
                add_violation(violations, "via-hole", via["id"], other["id"], distance, hole_required)
            if via["net"] != other["net"]:
                required = VIA_RADIUS * 2 + CLEARANCE
                if distance < required - 1e-6:
                    add_violation(violations, "via-via", via["id"], other["id"], distance, required)

    outside = []
    for track in tracks:
        for point in (track["first"], track["second"]):
            if not (0.55 <= point[0] <= 99.45 and 0.55 <= point[1] <= 79.45):
                outside.append({"id": track["id"], "point": point})
    for via in vias:
        if not (0.55 <= via["point"][0] <= 99.45 and 0.55 <= via["point"][1] <= 79.45):
            outside.append({"id": via["id"], "point": via["point"]})

    result = {
        "net_count": len(plan) + len({item["net"] for item in power_plan}),
        "track_count": len(tracks),
        "via_count": len(vias),
        "outside_count": len(outside),
        "violation_count": len(violations),
        "outside": outside,
        "violations": violations,
    }
    output = ROOT / "build-cad/pcb_a10_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("net_count", "track_count", "via_count", "outside_count", "violation_count")}, indent=2))
    for item in violations[:40]:
        print(item)


if __name__ == "__main__":
    validate()
