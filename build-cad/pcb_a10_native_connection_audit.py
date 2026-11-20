from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "hardware/system_carrier/altium/routing/signal_candidate"
DEFAULT_PCB = ROOT / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER_signal_candidate.PcbDoc"
DEFAULT_DRC = ROOT / "hardware/system_carrier/altium/native/Design Rule Check - EVT_SYS_CARRIER_signal_candidate.drc"
DEFAULT_OUTPUT = DEFAULT_AUDIT / "native_connection_audit.json"
PLAN = ROOT / "build-cad/compact_target_route_plan_repaired.json"
POWER_PLAN = ROOT / "build-cad/pcb_a10_power_plan.json"
COPPER_LAYERS = frozenset({1, 2, 3, 32})
BOARD_WIDTH_MIL = 90.0 / 0.0254
BOARD_HEIGHT_MIL = 70.0 / 0.0254
CONTACT_TOLERANCE_MIL = 0.02
BOUND_TOLERANCE_MIL = 0.02


@dataclass(frozen=True)
class Node:
    kind: str
    net: str
    layers: frozenset[int]
    geometry: tuple
    radius: float
    identity: str


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root == second_root:
            return
        if self.rank[first_root] < self.rank[second_root]:
            first_root, second_root = second_root, first_root
        self.parent[second_root] = first_root
        if self.rank[first_root] == self.rank[second_root]:
            self.rank[first_root] += 1


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def point_segment_distance(point, first, second) -> float:
    px, py = point
    ax, ay = first
    bx, by = second
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    ratio = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - ax - ratio * dx, py - ay - ratio * dy)


def orientation(first, second, third) -> float:
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def on_segment(point, first, second) -> bool:
    return (
        min(first[0], second[0]) - CONTACT_TOLERANCE_MIL
        <= point[0]
        <= max(first[0], second[0]) + CONTACT_TOLERANCE_MIL
        and min(first[1], second[1]) - CONTACT_TOLERANCE_MIL
        <= point[1]
        <= max(first[1], second[1]) + CONTACT_TOLERANCE_MIL
    )


def segments_intersect(first, second, third, fourth) -> bool:
    values = (
        orientation(first, second, third),
        orientation(first, second, fourth),
        orientation(third, fourth, first),
        orientation(third, fourth, second),
    )
    if values[0] * values[1] < 0 and values[2] * values[3] < 0:
        return True
    return (
        abs(values[0]) <= CONTACT_TOLERANCE_MIL and on_segment(third, first, second)
        or abs(values[1]) <= CONTACT_TOLERANCE_MIL and on_segment(fourth, first, second)
        or abs(values[2]) <= CONTACT_TOLERANCE_MIL and on_segment(first, third, fourth)
        or abs(values[3]) <= CONTACT_TOLERANCE_MIL and on_segment(second, third, fourth)
    )


def segment_distance(first, second, third, fourth) -> float:
    if segments_intersect(first, second, third, fourth):
        return 0.0
    return min(
        point_segment_distance(first, third, fourth),
        point_segment_distance(second, third, fourth),
        point_segment_distance(third, first, second),
        point_segment_distance(fourth, first, second),
    )


def polygon_edges(polygon):
    return tuple(zip(polygon, polygon[1:] + polygon[:1]))


def point_in_polygon(point, polygon) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if on_segment(point, previous, current) and abs(
            orientation(previous, current, point)
        ) <= CONTACT_TOLERANCE_MIL:
            return True
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (
                (previous[0] - current[0])
                * (point[1] - current[1])
                / (previous[1] - current[1])
                + current[0]
            )
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside


def point_polygon_distance(point, polygon) -> float:
    if point_in_polygon(point, polygon):
        return 0.0
    return min(point_segment_distance(point, first, second) for first, second in polygon_edges(polygon))


def segment_polygon_distance(first, second, polygon) -> float:
    if point_in_polygon(first, polygon) or point_in_polygon(second, polygon):
        return 0.0
    return min(segment_distance(first, second, edge_first, edge_second) for edge_first, edge_second in polygon_edges(polygon))


def polygon_distance(first, second) -> float:
    if point_in_polygon(first[0], second) or point_in_polygon(second[0], first):
        return 0.0
    return min(
        segment_distance(a, b, c, d)
        for a, b in polygon_edges(first)
        for c, d in polygon_edges(second)
    )


def rectangle(center_x: float, center_y: float, width: float, height: float):
    half_width = width / 2
    half_height = height / 2
    return (
        (center_x - half_width, center_y - half_height),
        (center_x + half_width, center_y - half_height),
        (center_x + half_width, center_y + half_height),
        (center_x - half_width, center_y + half_height),
    )


def fill_polygon(row: dict[str, str]):
    x1 = float(row["x1_mil"])
    y1 = float(row["y1_mil"])
    x2 = float(row["x2_mil"])
    y2 = float(row["y2_mil"])
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    polygon = rectangle(center_x, center_y, abs(x2 - x1), abs(y2 - y1))
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


def node_bounds(node: Node):
    if node.kind == "track":
        points = node.geometry
    elif node.kind == "via":
        points = (node.geometry,)
    else:
        points = node.geometry
    return (
        min(point[0] for point in points) - node.radius,
        min(point[1] for point in points) - node.radius,
        max(point[0] for point in points) + node.radius,
        max(point[1] for point in points) + node.radius,
    )


def bounds_overlap(first: Node, second: Node) -> bool:
    a = node_bounds(first)
    b = node_bounds(second)
    tolerance = CONTACT_TOLERANCE_MIL
    return not (
        a[2] + tolerance < b[0]
        or b[2] + tolerance < a[0]
        or a[3] + tolerance < b[1]
        or b[3] + tolerance < a[1]
    )


def nodes_touch(first: Node, second: Node) -> bool:
    if not first.layers.intersection(second.layers) or not bounds_overlap(first, second):
        return False
    limit = first.radius + second.radius + CONTACT_TOLERANCE_MIL
    if first.kind == "track" and second.kind == "track":
        distance = segment_distance(*first.geometry, *second.geometry)
    elif first.kind == "via" and second.kind == "via":
        distance = math.dist(first.geometry, second.geometry)
    elif first.kind == "track" and second.kind == "via":
        distance = point_segment_distance(second.geometry, *first.geometry)
    elif first.kind == "via" and second.kind == "track":
        distance = point_segment_distance(first.geometry, *second.geometry)
    elif first.kind in {"pad", "fill", "polygon"} and second.kind in {"pad", "fill", "polygon"}:
        distance = polygon_distance(first.geometry, second.geometry)
    elif first.kind in {"pad", "fill", "polygon"} and second.kind == "track":
        distance = segment_polygon_distance(*second.geometry, first.geometry)
    elif first.kind == "track" and second.kind in {"pad", "fill", "polygon"}:
        distance = segment_polygon_distance(*first.geometry, second.geometry)
    elif first.kind in {"pad", "fill", "polygon"} and second.kind == "via":
        distance = point_polygon_distance(second.geometry, first.geometry)
    elif first.kind == "via" and second.kind in {"pad", "fill", "polygon"}:
        distance = point_polygon_distance(first.geometry, second.geometry)
    else:
        return False
    return distance <= limit


def pad_layers(row: dict[str, str]) -> frozenset[int]:
    layer = int(row["layer"])
    if layer == 74 or float(row.get("hole_mil", 0) or 0) > 0:
        return COPPER_LAYERS
    if layer in COPPER_LAYERS:
        return frozenset({layer})
    return frozenset()


def load_nodes(audit: Path) -> tuple[list[Node], list[str]]:
    nodes: list[Node] = []
    errors: list[str] = []
    for index, row in enumerate(read_csv(audit / "pad_geometry.csv"), start=1):
        net = row["net_name"].strip()
        layers = pad_layers(row)
        if not net or not layers:
            continue
        identity = f"{row['designator'] or '<free>'}:{row['pad_name']}:{index}"
        nodes.append(Node(
            "pad",
            net,
            layers,
            rectangle(
                float(row["x_mil"]),
                float(row["y_mil"]),
                float(row["x_size_mil"]),
                float(row["y_size_mil"]),
            ),
            0.0,
            identity,
        ))
    for index, row in enumerate(read_csv(audit / "track_inventory.csv"), start=1):
        layer = int(row["layer"])
        if layer not in COPPER_LAYERS:
            continue
        net = row["net_name"].strip()
        if not net:
            errors.append(f"unassigned_track:{index}")
            continue
        nodes.append(Node(
            "track",
            net,
            frozenset({layer}),
            (
                (float(row["x1_mil"]), float(row["y1_mil"])),
                (float(row["x2_mil"]), float(row["y2_mil"])),
            ),
            float(row["width_mil"]) / 2,
            f"track:{index}",
        ))
    for index, row in enumerate(read_csv(audit / "fill_inventory.csv"), start=1):
        layer = int(row["layer"])
        if layer not in COPPER_LAYERS:
            continue
        net = row["net_name"].strip()
        if not net:
            errors.append(f"unassigned_fill:{index}")
            continue
        nodes.append(Node(
            "fill",
            net,
            frozenset({layer}),
            fill_polygon(row),
            0.0,
            f"fill:{index}",
        ))
    for index, row in enumerate(read_csv(audit / "polygon_inventory.csv"), start=1):
        layer = int(row["layer"])
        if layer not in COPPER_LAYERS:
            continue
        net = row["net_name"].strip()
        if not net:
            errors.append(f"unassigned_polygon:{index}")
            continue
        left = float(row["left_mil"])
        bottom = float(row["bottom_mil"])
        right = float(row["right_mil"])
        top = float(row["top_mil"])
        nodes.append(Node(
            "polygon",
            net,
            frozenset({layer}),
            rectangle(
                (left + right) / 2,
                (bottom + top) / 2,
                right - left,
                top - bottom,
            ),
            0.0,
            f"polygon:{index}",
        ))
    for index, row in enumerate(read_csv(audit / "via_inventory.csv"), start=1):
        net = row["net_name"].strip()
        if not net:
            errors.append(f"unassigned_via:{index}")
            continue
        nodes.append(Node(
            "via",
            net,
            COPPER_LAYERS,
            (float(row["x_mil"]), float(row["y_mil"])),
            float(row["size_mil"]) / 2,
            f"via:{index}",
        ))
    return nodes, errors


def target_nets() -> tuple[set[str], set[str]]:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    power_plan = json.loads(POWER_PLAN.read_text(encoding="utf-8"))
    signal_nets = set(plan["top"])
    signal_nets.update(item["net"] for item in plan["layer_routes"])
    return signal_nets, {item["net"] for item in power_plan}


def expected_geometry():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    tracks = []
    layers_by_point: dict[tuple[str, float, float], set[int]] = defaultdict(set)
    for net, paths in plan["top"].items():
        for path_index, path in enumerate(paths):
            for segment_index, (first, second) in enumerate(zip(path, path[1:])):
                tracks.append({
                    "net": net,
                    "layer": 1,
                    "first": first,
                    "second": second,
                    "width": 0.20,
                    "id": f"top:{net}:{path_index}:{segment_index}",
                })
                layers_by_point[(net, round(first[0], 6), round(first[1], 6))].add(1)
                layers_by_point[(net, round(second[0], 6), round(second[1], 6))].add(1)
    for route_index, route in enumerate(plan["layer_routes"]):
        net = route["net"]
        layer = int(route["layer"])
        for segment_index, (first, second) in enumerate(zip(route["points"], route["points"][1:])):
            tracks.append({
                "net": net,
                "layer": layer,
                "first": first,
                "second": second,
                "width": 0.20,
                "id": f"layer:{net}:{route_index}:{segment_index}",
            })
            layers_by_point[(net, round(first[0], 6), round(first[1], 6))].add(layer)
            layers_by_point[(net, round(second[0], 6), round(second[1], 6))].add(layer)
    vias = []
    for (net, x, y), layers in sorted(layers_by_point.items()):
        if len(layers) > 1:
            vias.append({
                "net": net,
                "point": (x, y),
                "id": f"via:{net}:{x:.6f}:{y:.6f}",
            })
    return tracks, vias


def endpoint_error(expected_first, expected_second, actual_first, actual_second) -> float:
    forward = max(
        math.dist(expected_first, actual_first),
        math.dist(expected_second, actual_second),
    )
    reverse = max(
        math.dist(expected_first, actual_second),
        math.dist(expected_second, actual_first),
    )
    return min(forward, reverse)


def match_expected_geometry(audit: Path) -> dict:
    tracks, vias = expected_geometry()
    actual_tracks = []
    for index, row in enumerate(read_csv(audit / "track_inventory.csv"), start=1):
        layer = int(row["layer"])
        if layer not in COPPER_LAYERS or not row["net_name"].strip():
            continue
        actual_tracks.append({
            "index": index,
            "net": row["net_name"].strip(),
            "layer": layer,
            "first": (float(row["x1_mil"]), float(row["y1_mil"])),
            "second": (float(row["x2_mil"]), float(row["y2_mil"])),
            "width": float(row["width_mil"]),
        })
    actual_vias = []
    for index, row in enumerate(read_csv(audit / "via_inventory.csv"), start=1):
        if not row["net_name"].strip():
            continue
        actual_vias.append({
            "index": index,
            "net": row["net_name"].strip(),
            "point": (float(row["x_mil"]), float(row["y_mil"])),
        })

    used_tracks = set()
    missing_tracks = []
    for expected in tracks:
        first = tuple(value / 0.0254 for value in expected["first"])
        second = tuple(value / 0.0254 for value in expected["second"])
        width = expected["width"] / 0.0254
        ranked = []
        for actual_index, actual in enumerate(actual_tracks):
            if actual_index in used_tracks:
                continue
            if actual["net"] != expected["net"] or actual["layer"] != expected["layer"]:
                continue
            if abs(actual["width"] - width) > 0.05:
                continue
            error = endpoint_error(first, second, actual["first"], actual["second"])
            if error <= 0.85:
                ranked.append((error, actual_index))
        if not ranked:
            missing_tracks.append(expected["id"])
            continue
        _, actual_index = min(ranked)
        used_tracks.add(actual_index)

    used_vias = set()
    missing_vias = []
    for expected in vias:
        point = tuple(value / 0.0254 for value in expected["point"])
        ranked = []
        for actual_index, actual in enumerate(actual_vias):
            if actual_index in used_vias or actual["net"] != expected["net"]:
                continue
            error = math.dist(point, actual["point"])
            if error <= 0.85:
                ranked.append((error, actual_index))
        if not ranked:
            missing_vias.append(expected["id"])
            continue
        _, actual_index = min(ranked)
        used_vias.add(actual_index)
    return {
        "expected_track_count": len(tracks),
        "matched_track_count": len(tracks) - len(missing_tracks),
        "missing_tracks": missing_tracks,
        "expected_via_count": len(vias),
        "matched_via_count": len(vias) - len(missing_vias),
        "missing_vias": missing_vias,
    }


def drc_result(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    pcb_match = re.search(r"^PCB File\s*:\s*(.+)$", text, re.MULTILINE)
    pcb_file = pcb_match.group(1).strip() if pcb_match else ""
    wanted = {
        "Un-Routed Net Constraint": "unrouted_net_violations",
        "Routing Topology Rule": "routing_topology_violations",
        "Net Antennae": "net_antennae_violations",
    }
    counts = {}
    active = ""
    for line in text.splitlines():
        if line.startswith("Processing Rule :"):
            active = line.split(":", 1)[1].strip()
            continue
        match = re.match(r"Rule Violations\s*:\s*(\d+)\s*$", line.strip())
        if not match:
            continue
        for prefix, key in wanted.items():
            if active.startswith(prefix):
                counts[key] = int(match.group(1))
                break
    return {"pcb_file": pcb_file, **counts}


def audit_connections(audit: Path, pcb: Path, drc: Path) -> dict:
    nodes, errors = load_nodes(audit)
    outside = []
    for node in nodes:
        left, bottom, right, top = node_bounds(node)
        if (
            left < -BOUND_TOLERANCE_MIL
            or bottom < -BOUND_TOLERANCE_MIL
            or right > BOARD_WIDTH_MIL + BOUND_TOLERANCE_MIL
            or top > BOARD_HEIGHT_MIL + BOUND_TOLERANCE_MIL
        ):
            outside.append(node.identity)

    by_net: dict[str, list[int]] = defaultdict(list)
    for index, node in enumerate(nodes):
        by_net[node.net].append(index)
    disjoint = DisjointSet(len(nodes))
    for indices in by_net.values():
        for offset, first_index in enumerate(indices):
            first = nodes[first_index]
            for second_index in indices[offset + 1:]:
                if nodes_touch(first, nodes[second_index]):
                    disjoint.union(first_index, second_index)

    net_results = {}
    disconnected_nets = []
    disconnected_components = {}
    unattached_target_pads = []
    orphan_copper = []
    signal_targets, power_targets = target_nets()
    expected_targets = signal_targets.union(power_targets)
    for net, indices in sorted(by_net.items()):
        groups: dict[int, list[int]] = defaultdict(list)
        for index in indices:
            groups[disjoint.find(index)].append(index)
        pad_groups = []
        pad_count = 0
        for group in groups.values():
            pads = [index for index in group if nodes[index].kind == "pad"]
            if pads:
                pad_groups.append(pads)
                pad_count += len(pads)
            elif any(nodes[index].kind != "pad" for index in group):
                orphan_copper.append({
                    "net": net,
                    "objects": [nodes[index].identity for index in group[:12]],
                    "object_count": len(group),
                })
        disconnected = pad_count > 1 and len(pad_groups) > 1
        if disconnected:
            disconnected_nets.append(net)
            disconnected_components[net] = [
                {
                    "pads": [nodes[index].identity for index in pads],
                    "pad_count": len(pads),
                    "has_copper": any(
                        nodes[index].kind != "pad"
                        for index in groups[disjoint.find(pads[0])]
                    ),
                }
                for pads in pad_groups
            ]
        if net in signal_targets:
            for pads in pad_groups:
                root = disjoint.find(pads[0])
                group = groups[root]
                if not any(nodes[index].kind != "pad" for index in group):
                    unattached_target_pads.extend(nodes[index].identity for index in pads)
        net_results[net] = {
            "node_count": len(indices),
            "pad_count": pad_count,
            "pad_component_count": len(pad_groups),
            "connected": not disconnected,
        }

    missing_target_nets = sorted(expected_targets.difference(by_net))
    disconnected_signal_nets = sorted(signal_targets.intersection(disconnected_nets))
    disconnected_power_nets = sorted(power_targets.intersection(disconnected_nets))
    expected_match = match_expected_geometry(audit)
    expected_match["gate"] = "DIAGNOSTIC_ONLY"
    expected_match["reason"] = (
        "The compact route plan contains superseded alternative branches; "
        "connectivity and native DRC are the release gates."
    )
    drc_data = drc_result(drc)
    drc_board = Path(drc_data["pcb_file"].replace("\\", "/"))
    if drc_board.name.lower() != pcb.name.lower():
        errors.append("drc_board_mismatch")
    drc_data["pcb_file"] = evidence_path(drc_board)
    for key in (
        "unrouted_net_violations",
        "routing_topology_violations",
        "net_antennae_violations",
    ):
        if drc_data.get(key) != 0:
            errors.append(f"drc_nonzero:{key}:{drc_data.get(key)}")
    if outside:
        errors.append(f"outside_board:{len(outside)}")
    if disconnected_signal_nets:
        errors.append(f"disconnected_signal_nets:{len(disconnected_signal_nets)}")
    if disconnected_power_nets:
        errors.append(f"disconnected_power_nets:{len(disconnected_power_nets)}")
    if missing_target_nets:
        errors.append(f"missing_target_nets:{len(missing_target_nets)}")
    if unattached_target_pads:
        errors.append(f"unattached_target_pads:{len(unattached_target_pads)}")
    counts = defaultdict(int)
    for node in nodes:
        counts[node.kind] += 1
    evidence = [
        audit / "pad_geometry.csv",
        audit / "track_inventory.csv",
        audit / "fill_inventory.csv",
        audit / "polygon_inventory.csv",
        audit / "via_inventory.csv",
        pcb,
        drc,
    ]
    return {
        "schema": "PCB-A10-NATIVE-CONNECTION-AUDIT-001",
        "status": "PASS" if not errors else "FAIL",
        "production_authority": "NOT_AUTHORIZED",
        "candidate_pcb": evidence_path(pcb),
        "candidate_pcb_sha256": sha256(pcb),
        "drc": drc_data,
        "counts": dict(sorted(counts.items())),
        "target_net_count": len(expected_targets),
        "signal_target_net_count": len(signal_targets),
        "power_stitch_net_count": len(power_targets),
        "missing_target_nets": missing_target_nets,
        "disconnected_pad_nets": disconnected_nets,
        "disconnected_pad_components": disconnected_components,
        "disconnected_signal_nets": disconnected_signal_nets,
        "disconnected_power_nets": disconnected_power_nets,
        "unattached_target_pads": unattached_target_pads,
        "route_plan_geometry_diagnostic": expected_match,
        "outside_board_count": len(outside),
        "outside_board": outside,
        "orphan_copper_component_count": len(orphan_copper),
        "orphan_copper_components": orphan_copper,
        "net_results": net_results,
        "evidence_sha256": {
            evidence_path(path): sha256(path) for path in evidence
        },
        "errors": sorted(set(errors)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument("--drc", type=Path, default=DEFAULT_DRC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit_dir = args.audit_dir.resolve()
    pcb = args.pcb.resolve()
    drc = args.drc.resolve()
    output = args.output.resolve()
    result = audit_connections(audit_dir, pcb, drc)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "status": result["status"],
        "counts": result["counts"],
        "target_net_count": result["target_net_count"],
        "outside_board_count": result["outside_board_count"],
        "disconnected_pad_nets": result["disconnected_pad_nets"],
        "disconnected_power_nets": result["disconnected_power_nets"],
        "unattached_target_pad_count": len(result["unattached_target_pads"]),
        "orphan_copper_component_count": result["orphan_copper_component_count"],
        "errors": result["errors"],
    }
    print(json.dumps(summary, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
