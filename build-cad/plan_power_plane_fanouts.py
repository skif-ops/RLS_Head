from __future__ import annotations

import argparse
import copy
import csv
import heapq
import json
import math
from collections import defaultdict
from pathlib import Path

import pcb_a10_native_connection_audit as connection_audit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "hardware/system_carrier/altium/routing/physical_closure_candidate"
DEFAULT_OUTPUT = ROOT / "build-cad/power_plane_fanout_plan.json"
POWER_NETS = ("3V3", "GND")
MM_PER_MIL = 0.0254
BOARD_WIDTH_MM = 90.0
BOARD_HEIGHT_MM = 70.0
EDGE_CLEARANCE_MM = 0.40
CLEARANCE_MM = 0.20
TRACK_WIDTH_MM = 0.15
VIA_SIZE_MM = 0.40
VIA_HOLE_MM = 0.20
MICROVIA_SIZE_MM = 0.30
MICROVIA_HOLE_MM = 0.18
SEARCH_STEP_MM = 0.20


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mm(value: str | float) -> float:
    return float(value) * MM_PER_MIL


def rect_from_row(row: dict[str, str]):
    return (
        (mm(row["left_mil"]), mm(row["bottom_mil"])),
        (mm(row["right_mil"]), mm(row["bottom_mil"])),
        (mm(row["right_mil"]), mm(row["top_mil"])),
        (mm(row["left_mil"]), mm(row["top_mil"])),
    )


def fill_polygon(row: dict[str, str]):
    center_x = (mm(row["x1_mil"]) + mm(row["x2_mil"])) / 2
    center_y = (mm(row["y1_mil"]) + mm(row["y2_mil"])) / 2
    polygon = connection_audit.rectangle(
        center_x,
        center_y,
        abs(mm(row["x2_mil"]) - mm(row["x1_mil"])),
        abs(mm(row["y2_mil"]) - mm(row["y1_mil"])),
    )
    angle = math.radians(float(row.get("rotation_deg", 0) or 0))
    if abs(angle) < 1e-12:
        return polygon
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return tuple(
        (
            center_x + (x - center_x) * cosine - (y - center_y) * sine,
            center_y + (x - center_x) * sine + (y - center_y) * cosine,
        )
        for x, y in polygon
    )


def build_obstacles(audit_dir: Path):
    by_layer = defaultdict(list)
    for row in read_csv(audit_dir / "pad_geometry.csv"):
        layers = connection_audit.pad_layers(row)
        for layer in layers:
            by_layer[layer].append({
                "kind": "polygon",
                "net": row["net_name"].strip(),
                "geometry": rect_from_row(row),
                "radius": 0.0,
            })
    for row in read_csv(audit_dir / "track_inventory.csv"):
        layer = int(row["layer"])
        if layer not in connection_audit.COPPER_LAYERS:
            continue
        by_layer[layer].append({
            "kind": "track",
            "net": row["net_name"].strip(),
            "geometry": (
                (mm(row["x1_mil"]), mm(row["y1_mil"])),
                (mm(row["x2_mil"]), mm(row["y2_mil"])),
            ),
            "radius": mm(row["width_mil"]) / 2,
        })
    for row in read_csv(audit_dir / "fill_inventory.csv"):
        layer = int(row["layer"])
        if layer not in connection_audit.COPPER_LAYERS:
            continue
        by_layer[layer].append({
            "kind": "polygon",
            "net": row["net_name"].strip(),
            "geometry": fill_polygon(row),
            "radius": 0.0,
        })
    for row in read_csv(audit_dir / "via_inventory.csv"):
        obstacle = {
            "kind": "via",
            "net": row["net_name"].strip(),
            "geometry": (mm(row["x_mil"]), mm(row["y_mil"])),
            "radius": mm(row["size_mil"]) / 2,
        }
        for layer in connection_audit.COPPER_LAYERS:
            by_layer[layer].append(obstacle)
    return by_layer


def obstacle_distance_to_point(point, obstacle) -> float:
    if obstacle["kind"] == "via":
        return math.dist(point, obstacle["geometry"]) - obstacle["radius"]
    if obstacle["kind"] == "track":
        return (
            connection_audit.point_segment_distance(point, *obstacle["geometry"])
            - obstacle["radius"]
        )
    return connection_audit.point_polygon_distance(point, obstacle["geometry"])


def obstacle_distance_to_segment(first, second, obstacle) -> float:
    if obstacle["kind"] == "via":
        return (
            connection_audit.point_segment_distance(obstacle["geometry"], first, second)
            - obstacle["radius"]
        )
    if obstacle["kind"] == "track":
        return (
            connection_audit.segment_distance(first, second, *obstacle["geometry"])
            - obstacle["radius"]
        )
    return connection_audit.segment_polygon_distance(first, second, obstacle["geometry"])


def via_is_clear(
    point,
    net: str,
    obstacles,
    layers=connection_audit.COPPER_LAYERS,
    via_size_mm=VIA_SIZE_MM,
) -> bool:
    x, y = point
    radius = via_size_mm / 2
    if not (
        EDGE_CLEARANCE_MM + radius <= x <= BOARD_WIDTH_MM - EDGE_CLEARANCE_MM - radius
        and EDGE_CLEARANCE_MM + radius <= y <= BOARD_HEIGHT_MM - EDGE_CLEARANCE_MM - radius
    ):
        return False
    for layer in layers:
        for obstacle in obstacles[layer]:
            if obstacle["net"] == net:
                continue
            if (
                obstacle_distance_to_point(point, obstacle)
                < radius + CLEARANCE_MM - 0.001
            ):
                return False
    return True


def track_is_clear(first, second, net: str, obstacles) -> bool:
    radius = TRACK_WIDTH_MM / 2
    for obstacle in obstacles[1]:
        if obstacle["net"] == net:
            continue
        if (
            obstacle_distance_to_segment(first, second, obstacle)
            < radius + CLEARANCE_MM - 0.001
        ):
            return False
    return True


def add_planned_obstacles(net: str, path, via, obstacles) -> None:
    for first, second in zip(path, path[1:]):
        obstacles[1].append({
            "kind": "track",
            "net": net,
            "geometry": (first, second),
            "radius": TRACK_WIDTH_MM / 2,
        })
    if via is not None:
        via_obstacle = {
            "kind": "via",
            "net": net,
            "geometry": via,
            "radius": VIA_SIZE_MM / 2,
        }
        for layer in connection_audit.COPPER_LAYERS:
            obstacles[layer].append(via_obstacle)


def component_centers(audit_dir: Path):
    return {
        row["designator"]: (mm(row["x_mil"]), mm(row["y_mil"]))
        for row in read_csv(audit_dir / "component_bounds.csv")
    }


def disconnected_power_groups(audit_dir: Path):
    nodes, _ = connection_audit.load_nodes(audit_dir)
    disjoint = connection_audit.DisjointSet(len(nodes))
    by_net = defaultdict(list)
    for index, node in enumerate(nodes):
        by_net[node.net].append(index)
    for indices in by_net.values():
        for offset, first_index in enumerate(indices):
            for second_index in indices[offset + 1:]:
                if connection_audit.nodes_touch(nodes[first_index], nodes[second_index]):
                    disjoint.union(first_index, second_index)

    result = {}
    for net in POWER_NETS:
        groups = defaultdict(list)
        for index in by_net[net]:
            groups[disjoint.find(index)].append(index)
        pad_groups = []
        for group in groups.values():
            pads = [index for index in group if nodes[index].kind == "pad"]
            if pads:
                pad_groups.append((pads, group))
        anchor = max(pad_groups, key=lambda item: len(item[1]))[1]
        result[net] = [pads for pads, group in pad_groups if group is not anchor]
    return nodes, result


def candidate_directions(source, center, net: str, designator: str):
    dx = source[0] - center[0]
    dy = source[1] - center[1]
    if math.hypot(dx, dy) < 0.05:
        base = 0.0
    else:
        base = math.atan2(dy, dx)
    if designator in {"U1", "U2"} and net == "3V3":
        offsets = (30, 45, 15, 60, 0, -15, -30, 90, -90, 120, -120, 180)
    elif designator in {"U1", "U2"} and net == "GND":
        offsets = (-30, -45, -15, -60, 0, 15, 30, -90, 90, -120, 120, 180)
    else:
        offsets = (0, 15, -15, 30, -30, 45, -45, 60, -60, 90, -90, 120, -120, 180)
    return [base + math.radians(offset) for offset in offsets]


def simplify_path(path):
    simplified = []
    for point in path:
        if simplified and point == simplified[-1]:
            continue
        if len(simplified) >= 2:
            first, second = simplified[-2:]
            vector_a = (second[0] - first[0], second[1] - first[1])
            vector_b = (point[0] - second[0], point[1] - second[1])
            if (
                abs(vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]) < 1e-9
                and vector_a[0] * vector_b[0] >= 0
                and vector_a[1] * vector_b[1] >= 0
            ):
                simplified[-1] = point
                continue
        simplified.append(point)
    return tuple(simplified)


def existing_plane_access_points(net: str, obstacles):
    return sorted({
        obstacle["geometry"]
        for obstacle in obstacles[1]
        if obstacle["kind"] == "via" and obstacle["net"] == net
    })


def astar_fanout(
    source,
    net: str,
    obstacles,
    access_points,
    via_layers=connection_audit.COPPER_LAYERS,
):
    origin = (
        round(source[0] / SEARCH_STEP_MM),
        round(source[1] / SEARCH_STEP_MM),
    )
    frontier = []
    best = {}
    parent = {}
    for ix in range(origin[0] - 2, origin[0] + 3):
        for iy in range(origin[1] - 2, origin[1] + 3):
            point = (ix * SEARCH_STEP_MM, iy * SEARCH_STEP_MM)
            if not track_is_clear(source, point, net, obstacles):
                continue
            cost = math.dist(source, point)
            best[(ix, iy)] = cost
            parent[(ix, iy)] = None
            heapq.heappush(frontier, (cost, cost, ix, iy))
    directions = (
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    )
    explored = 0
    while frontier and explored < 15000:
        _, cost, ix, iy = heapq.heappop(frontier)
        node = (ix, iy)
        if cost != best.get(node):
            continue
        explored += 1
        point = (ix * SEARCH_STEP_MM, iy * SEARCH_STEP_MM)
        nearby_access = sorted(
            (
                (math.dist(point, target), target)
                for target in access_points
                if math.dist(point, target) <= SEARCH_STEP_MM * 1.5
                and track_is_clear(point, target, net, obstacles)
            ),
            key=lambda item: item[0],
        )
        if nearby_access:
            target = nearby_access[0][1]
            points = [target, point]
            while parent[node] is not None:
                node = parent[node]
                points.append((node[0] * SEARCH_STEP_MM, node[1] * SEARCH_STEP_MM))
            points.append(source)
            points.reverse()
            return simplify_path(points), None
        if (
            math.dist(source, point) >= 0.45
            and via_is_clear(point, net, obstacles, via_layers)
        ):
            points = [point]
            while parent[node] is not None:
                node = parent[node]
                points.append((node[0] * SEARCH_STEP_MM, node[1] * SEARCH_STEP_MM))
            points.append(source)
            points.reverse()
            path = simplify_path(points)
            return path, path[-1]
        for dx, dy in directions:
            neighbor = (ix + dx, iy + dy)
            point_next = (
                neighbor[0] * SEARCH_STEP_MM,
                neighbor[1] * SEARCH_STEP_MM,
            )
            if (
                math.dist(source, point_next) > 12.0
                or not (EDGE_CLEARANCE_MM <= point_next[0] <= BOARD_WIDTH_MM - EDGE_CLEARANCE_MM)
                or not (EDGE_CLEARANCE_MM <= point_next[1] <= BOARD_HEIGHT_MM - EDGE_CLEARANCE_MM)
                or not track_is_clear(point, point_next, net, obstacles)
            ):
                continue
            next_cost = cost + math.dist(point, point_next)
            if next_cost >= best.get(neighbor, float("inf")):
                continue
            best[neighbor] = next_cost
            parent[neighbor] = (ix, iy)
            heuristic = max(0.0, 0.45 - math.dist(source, point_next))
            heapq.heappush(
                frontier,
                (next_cost + heuristic, next_cost, neighbor[0], neighbor[1]),
            )
    return None, None


def choose_fanout(group, nodes, pad_rows, centers, net: str, obstacles):
    candidates = []
    access_points = existing_plane_access_points(net, obstacles)
    for node_index in group:
        node = nodes[node_index]
        row_index = int(node.identity.rsplit(":", 1)[1]) - 1
        row = pad_rows[row_index]
        source = (mm(row["x_mil"]), mm(row["y_mil"]))
        center = centers.get(row["designator"], source)
        area = mm(row["x_size_mil"]) * mm(row["y_size_mil"])
        if (
            min(mm(row["x_size_mil"]), mm(row["y_size_mil"]))
            >= VIA_SIZE_MM + 0.05
            and via_is_clear(source, net, obstacles)
        ):
            candidates.append(
                (0.55, row, (source,), source, (1, 32), VIA_SIZE_MM, VIA_HOLE_MM)
            )
        for direction_rank, angle in enumerate(
            candidate_directions(source, center, net, row["designator"])
        ):
            for step in range(0, 80):
                distance = 0.45 + step * 0.10
                via = (
                    source[0] + math.cos(angle) * distance,
                    source[1] + math.sin(angle) * distance,
                )
                if not via_is_clear(via, net, obstacles):
                    continue
                path_options = (
                    (source, via),
                    (source, (source[0], via[1]), via),
                    (source, (via[0], source[1]), via),
                )
                for path in path_options:
                    path = tuple(
                        point for index, point in enumerate(path)
                        if index == 0 or point != path[index - 1]
                    )
                    if not all(
                        track_is_clear(first, second, net, obstacles)
                        for first, second in zip(path, path[1:])
                    ):
                        continue
                    length = sum(
                        math.dist(first, second)
                        for first, second in zip(path, path[1:])
                    )
                    score = (
                        length
                        + direction_rank * 0.08
                        + (len(path) - 2) * 0.12
                        - min(area, 2.0) * 0.01
                    )
                    candidates.append(
                        (score, row, path, via, (1, 32), VIA_SIZE_MM, VIA_HOLE_MM)
                    )
                break
        for target in access_points:
            distance = math.dist(source, target)
            if distance > 15.0:
                continue
            for path in (
                (source, target),
                (source, (source[0], target[1]), target),
                (source, (target[0], source[1]), target),
            ):
                path = simplify_path(path)
                if not all(
                    track_is_clear(first, second, net, obstacles)
                    for first, second in zip(path, path[1:])
                ):
                    continue
                length = sum(
                    math.dist(first, second)
                    for first, second in zip(path, path[1:])
                )
                candidates.append(
                    (
                        length + (len(path) - 2) * 0.12 + 0.10,
                        row,
                        path,
                        None,
                        None,
                        None,
                        None,
                    )
                )
    if not candidates:
        for node_index in group:
            node = nodes[node_index]
            row_index = int(node.identity.rsplit(":", 1)[1]) - 1
            row = pad_rows[row_index]
            source = (mm(row["x_mil"]), mm(row["y_mil"]))
            path, via = astar_fanout(source, net, obstacles, access_points)
            if path:
                return (
                    row,
                    path,
                    via,
                    (1, 32) if via is not None else None,
                    VIA_SIZE_MM if via is not None else None,
                    VIA_HOLE_MM if via is not None else None,
                )
        blind_layers = (1, 2) if net == "GND" else (1, 2, 3)
        for node_index in group:
            node = nodes[node_index]
            row_index = int(node.identity.rsplit(":", 1)[1]) - 1
            row = pad_rows[row_index]
            source = (mm(row["x_mil"]), mm(row["y_mil"]))
            if (
                min(mm(row["x_size_mil"]), mm(row["y_size_mil"]))
                >= VIA_SIZE_MM + 0.05
                and via_is_clear(source, net, obstacles, blind_layers)
            ):
                return (
                    row,
                    (source,),
                    source,
                    (1, blind_layers[-1]),
                    VIA_SIZE_MM,
                    VIA_HOLE_MM,
                )
            if (
                min(mm(row["x_size_mil"]), mm(row["y_size_mil"]))
                >= MICROVIA_SIZE_MM - 0.001
                and via_is_clear(
                    source,
                    net,
                    obstacles,
                    blind_layers,
                    MICROVIA_SIZE_MM,
                )
            ):
                return (
                    row,
                    (source,),
                    source,
                    (1, blind_layers[-1]),
                    MICROVIA_SIZE_MM,
                    MICROVIA_HOLE_MM,
                )
            path, via = astar_fanout(
                source,
                net,
                obstacles,
                (),
                blind_layers,
            )
            if path:
                return (
                    row,
                    path,
                    via,
                    (1, blind_layers[-1]),
                    VIA_SIZE_MM,
                    VIA_HOLE_MM,
                )
        identities = [nodes[index].identity for index in group]
        raise RuntimeError(f"no clear {net} fanout for {identities}")
    _, row, path, via, via_layers, via_size, via_hole = min(
        candidates, key=lambda item: item[0]
    )
    return row, path, via, via_layers, via_size, via_hole


def apply_drc_correction(item: dict) -> bool:
    key = (item["net"], item["designator"], item["pad_name"])
    source = item["track"][0]
    if key == ("GND", "U1", "148"):
        item["track"] = [source, item["track"][1], [56.5, 51.45099740984039]]
        item["via"] = [56.5, 51.45099740984039]
        item["via_layers"] = [1, 2]
    elif key == ("3V3", "U1", "82"):
        item["track"] = [source, [59.85, 25.375608417986367]]
        item["via"] = [59.85, 25.375608417986367]
    elif key == ("GND", "C93", "2"):
        item["track"] = [source, [16.30, 61.149986399999996]]
        item["via"] = [16.30, 61.149986399999996]
    elif key == ("3V3", "C111", "1"):
        item["track"] = [source, [63.999998999999995, 53.75]]
        item["via"] = [63.999998999999995, 53.75]
    elif key == ("3V3", "U1", "114"):
        item["track"] = [
            source,
            [65.81419721237354, 41.7500054],
            [65.81419721237354, 41.90729120635914],
            [66.224994, 42.04369242791856],
        ]
        item["via"] = None
        item["via_layers"] = None
        item["via_size_mm"] = None
        item["via_hole_mm"] = None
    elif key == ("GND", "D3", "8"):
        item["track"] = [source, [77.86501059999999, 53.999993599999996]]
        item["via"] = None
        item["via_layers"] = None
        item["via_size_mm"] = None
        item["via_hole_mm"] = None
    elif key == ("3V3", "U1", "15"):
        item["track"] = [
            source,
            [37.875475758662276, 43.78748453385372],
            [37.5000012, 44.0700024],
        ]
        item["via"] = None
        item["via_layers"] = None
        item["via_size_mm"] = None
        item["via_hole_mm"] = None
    else:
        return False
    item["drc_correction"] = "post-route full-DRC correction"
    return True


def plan(audit_dir: Path, nets=POWER_NETS) -> dict:
    obstacles = build_obstacles(audit_dir)
    nodes, groups = disconnected_power_groups(audit_dir)
    pad_rows = read_csv(audit_dir / "pad_geometry.csv")
    centers = component_centers(audit_dir)
    fanouts = []
    cleanup_fanouts = [
        {
            "net": "GND",
            "track": [
                [55.2500038, 52.6750026],
                [55.2500038, 51.45099740984039],
                [56.45, 51.45099740984039],
            ],
            "via": [56.45, 51.45099740984039],
        },
        {
            "net": "3V3",
            "track": [
                [66.499994, 42.5200064],
                [66.325, 42.04369242791856],
            ],
            "via": [66.325, 42.04369242791856],
        },
    ]
    for net in nets:
        ordered = sorted(
            groups[net],
            key=lambda group: (
                0
                if nodes[group[0]].identity.split(":", 1)[0]
                in {"U1", "U2", "U4", "U9"}
                else 1,
                min(nodes[index].identity for index in group),
            ),
        )
        for group in ordered:
            row, path, via, via_layers, via_size, via_hole = choose_fanout(
                group, nodes, pad_rows, centers, net, obstacles
            )
            fanout = {
                "net": net,
                "designator": row["designator"],
                "pad_name": row["pad_name"],
                "group_pads": [nodes[index].identity for index in group],
                "track_width_mm": TRACK_WIDTH_MM,
                "via_size_mm": via_size,
                "via_hole_mm": via_hole,
                "track": [list(point) for point in path],
                "via": list(via) if via is not None else None,
                "via_layers": list(via_layers) if via_layers is not None else None,
            }
            legacy = copy.deepcopy(fanout)
            if apply_drc_correction(fanout):
                cleanup_fanouts.append(legacy)
            add_planned_obstacles(
                net,
                tuple(tuple(point) for point in fanout["track"]),
                tuple(fanout["via"]) if fanout["via"] is not None else None,
                obstacles,
            )
            fanouts.append(fanout)
    return {
        "schema": "EVT-POWER-PLANE-FANOUT-PLAN-001",
        "board_mm": [BOARD_WIDTH_MM, BOARD_HEIGHT_MM],
        "planes": {"GND": 2, "3V3": 3},
        "fanout_count": len(fanouts),
        "cleanup_fanouts": cleanup_fanouts,
        "fanouts": fanouts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--nets", nargs="+", choices=POWER_NETS, default=list(POWER_NETS))
    args = parser.parse_args()
    result = plan(args.audit_dir.resolve(), args.nets)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "fanout_count": result["fanout_count"],
        "by_net": {
            net: sum(item["net"] == net for item in result["fanouts"])
            for net in args.nets
        },
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
