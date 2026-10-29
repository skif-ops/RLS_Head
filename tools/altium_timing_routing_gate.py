from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


SCHEMA = "ALTIUM-TIMING-ROUTING-GATE-001"
SUMMARY_SCHEMA = "ALTIUM-TIMING-ROUTING-REVIEW-A-001"
TARGETS = {
    "GNSS_PPS": {
        "segments": 10,
        "endpoints": (("J8", "4", None), ("U1", "40", None)),
    },
    "IMU_DRDY": {
        "segments": 6,
        "endpoints": (("U2", "4", None), ("U1", "80", None)),
    },
    "RADAR_REF": {
        "segments": 10,
        "endpoints": (("U1", "79", None), ("J4", "4", None)),
    },
}
QUIET_NETS = {"BUCK_SW", "BUCK5_SW"}
EXPECTED_DRC = {
    "generic_clearance": 27,
    "ten_mil_clearance": 0,
    "timing_to_buck_sw": 0,
    "uart_to_buck_sw": 27,
    "unrouted_net": 0,
    "routing_topology": 0,
    "power_plane_connect": 0,
    "hole_size": 9,
    "hole_to_hole": 1,
    "net_antennae": 0,
    "component_clearance": 55,
    "total": 119,
    "warnings": 0,
}
ZERO_DRC_RULES = {
    "ten_mil_clearance",
    "timing_to_buck_sw",
    "unrouted_net",
    "routing_topology",
    "power_plane_connect",
    "net_antennae",
    "warnings",
}
TRACK_WIDTH_MM = 0.20
MIN_QUIET_CLEARANCE_MM = 1.0
MM_PER_MIL = 0.0254
TEXT_EVIDENCE_SUFFIXES = {".csv", ".drc", ".pas", ".py"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_evidence_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_EVIDENCE_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mm(value: str) -> float:
    return float(value) * MM_PER_MIL


def point_segment_distance(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    px, py = point
    ax, ay = first
    bx, by = second
    dx = bx - ax
    dy = by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)
    ratio = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


def _orientation(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
) -> float:
    return ((second[0] - first[0]) * (third[1] - first[1]) -
            (second[1] - first[1]) * (third[0] - first[0]))


def _on_segment(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    tolerance: float = 1e-9,
) -> bool:
    return (
        min(first[0], second[0]) - tolerance <= point[0]
        <= max(first[0], second[0]) + tolerance
        and min(first[1], second[1]) - tolerance <= point[1]
        <= max(first[1], second[1]) + tolerance
        and abs(_orientation(first, second, point)) <= tolerance
    )


def segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)):
        return True
    return (
        (abs(o1) <= 1e-9 and _on_segment(b1, a1, a2))
        or (abs(o2) <= 1e-9 and _on_segment(b2, a1, a2))
        or (abs(o3) <= 1e-9 and _on_segment(a1, b1, b2))
        or (abs(o4) <= 1e-9 and _on_segment(a2, b1, b2))
    )


def segment_distance(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> float:
    if segments_intersect(a1, a2, b1, b2):
        return 0.0
    return min(
        point_segment_distance(a1, b1, b2),
        point_segment_distance(a2, b1, b2),
        point_segment_distance(b1, a1, a2),
        point_segment_distance(b2, a1, a2),
    )


def segment_rect_distance(
    first: tuple[float, float],
    second: tuple[float, float],
    rect: tuple[float, float, float, float],
) -> float:
    left, bottom, right, top = rect
    if (
        left <= first[0] <= right and bottom <= first[1] <= top
    ) or (
        left <= second[0] <= right and bottom <= second[1] <= top
    ):
        return 0.0
    corners = ((left, bottom), (right, bottom), (right, top), (left, top))
    return min(
        segment_distance(first, second, corners[index], corners[(index + 1) % 4])
        for index in range(4)
    )


def track_segment(row: dict[str, str]) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (mm(row["x1_mil"]), mm(row["y1_mil"])),
        (mm(row["x2_mil"]), mm(row["y2_mil"])),
    )


def row_rect(row: dict[str, str]) -> tuple[float, float, float, float]:
    return tuple(
        mm(row[key]) for key in ("left_mil", "bottom_mil", "right_mil", "top_mil")
    )


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def resolve_pad(
    pads: list[dict[str, str]],
    net: str,
    endpoint: tuple[str, str, tuple[float, float] | None],
) -> dict[str, str] | None:
    designator, pad_name, expected = endpoint
    candidates = [
        row for row in pads
        if row.get("net_name") == net
        and row.get("pad_name") == pad_name
        and row.get("designator", "") == designator
    ]
    if expected is None:
        return candidates[0] if len(candidates) == 1 else None
    if not candidates:
        return None
    ranked = sorted(
        (
            math.hypot(mm(row["x_mil"]) - expected[0], mm(row["y_mil"]) - expected[1]),
            row,
        )
        for row in candidates
    )
    return ranked[0][1] if ranked[0][0] <= 0.05 else None


def route_is_connected(
    rows: list[dict[str, str]],
    endpoint_pads: list[dict[str, str]],
) -> tuple[bool, int]:
    if not rows:
        return False, 0
    sets = DisjointSet(len(rows))
    for first_index, first in enumerate(rows):
        first_segment = track_segment(first)
        for second_index in range(first_index + 1, len(rows)):
            second = rows[second_index]
            if first["layer"] != second["layer"]:
                continue
            if segment_distance(*first_segment, *track_segment(second)) <= 0.003:
                sets.union(first_index, second_index)
    components = {sets.find(index) for index in range(len(rows))}
    endpoint_components: list[set[int]] = []
    for pad in endpoint_pads:
        rect = row_rect(pad)
        touching = {
            sets.find(index)
            for index, row in enumerate(rows)
            if segment_rect_distance(*track_segment(row), rect)
            <= mm(row["width_mil"]) / 2.0 + 0.003
        }
        endpoint_components.append(touching)
    connected = (
        len(endpoint_components) == 2
        and bool(endpoint_components[0])
        and bool(endpoint_components[1])
        and bool(endpoint_components[0] & endpoint_components[1])
        and len(components) == 1
    )
    return connected, len(components)


def quiet_clearance(
    target_rows: list[dict[str, str]],
    tracks: list[dict[str, str]],
    fills: list[dict[str, str]],
    vias: list[dict[str, str]],
    pads: list[dict[str, str]],
) -> float:
    minimum = math.inf
    for target in target_rows:
        first, second = track_segment(target)
        target_radius = mm(target["width_mil"]) / 2.0
        for other in tracks:
            if other.get("net_name") not in QUIET_NETS or other.get("layer") != target.get("layer"):
                continue
            clearance = (
                segment_distance(first, second, *track_segment(other))
                - target_radius
                - mm(other["width_mil"]) / 2.0
            )
            minimum = min(minimum, clearance)
        for fill in fills:
            if fill.get("net_name") not in QUIET_NETS or fill.get("layer") != target.get("layer"):
                continue
            minimum = min(
                minimum,
                segment_rect_distance(first, second, row_rect(fill)) - target_radius,
            )
        for via in vias:
            if via.get("net_name") not in QUIET_NETS:
                continue
            center = (mm(via["x_mil"]), mm(via["y_mil"]))
            clearance = (
                point_segment_distance(center, first, second)
                - target_radius
                - mm(via["size_mil"]) / 2.0
            )
            minimum = min(minimum, clearance)
        for pad in pads:
            if pad.get("net_name") not in QUIET_NETS:
                continue
            layer = int(pad["layer"])
            if layer != 1 and float(pad["hole_mil"]) <= 0.0:
                continue
            minimum = min(
                minimum,
                segment_rect_distance(first, second, row_rect(pad)) - target_radius,
            )
    return minimum


def parse_drc(path: Path) -> tuple[str, str, dict[str, int]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    timestamp = ""
    date_match = re.search(r"^Date\s*:\s*(.+)$", text, re.MULTILINE)
    time_match = re.search(r"^Time\s*:\s*(.+)$", text, re.MULTILINE)
    if date_match and time_match:
        timestamp = f"{date_match.group(1).strip()} {time_match.group(1).strip()}"
    pcb_match = re.search(r"^PCB File\s*:\s*(.+)$", text, re.MULTILINE)
    pcb_file = pcb_match.group(1).strip() if pcb_match else ""
    counts: dict[str, int] = {}
    rules: list[tuple[str, int]] = []
    active = ""
    for line in text.splitlines():
        if line.startswith("Processing Rule :"):
            active = line.split(":", 1)[1].strip()
            continue
        match = re.match(r"Rule Violations\s*:\s*(\d+)\s*$", line.strip())
        if match:
            rules.append((active, int(match.group(1))))
    clearance_rules = [(rule, count) for rule, count in rules if rule.startswith("Clearance Constraint")]
    if len(clearance_rules) >= 2:
        counts["generic_clearance"] = clearance_rules[0][1]
        counts["ten_mil_clearance"] = clearance_rules[1][1]
    for rule, count in clearance_rules:
        if "NC_TIMING" in rule and "BUCK_SW" in rule:
            counts["timing_to_buck_sw"] = count
        if (
            ("NC_HOST_UART" in rule or "NC_GNSS_UART" in rule)
            and ("BUCK_SW" in rule or "BUCK5_SW" in rule)
        ):
            counts["uart_to_buck_sw"] = count
    prefixes = {
        "Un-Routed Net Constraint": "unrouted_net",
        "Routing Topology Rule": "routing_topology",
        "Power Plane Connect Rule": "power_plane_connect",
        "Hole Size Constraint": "hole_size",
        "Hole To Hole Clearance": "hole_to_hole",
        "Net Antennae": "net_antennae",
        "Component Clearance Constraint": "component_clearance",
    }
    for rule, count in rules:
        for prefix, name in prefixes.items():
            if rule.startswith(prefix):
                counts[name] = count
                break
    total_match = re.search(r"^Violations Detected\s*:\s*(\d+)\s*$", text, re.MULTILINE)
    warning_match = re.search(r"^Warnings\s*:\s*(\d+)\s*$", text, re.MULTILINE)
    if total_match:
        counts["total"] = int(total_match.group(1))
    if warning_match:
        counts["warnings"] = int(warning_match.group(1))
    elif total_match:
        counts["warnings"] = 0
    return pcb_file, timestamp, counts


def drc_has_no_new_markers(counts: dict[str, int]) -> bool:
    return all(
        name in counts
        and (
            counts[name] == 0
            if name in ZERO_DRC_RULES
            else counts[name] <= baseline
        )
        for name, baseline in EXPECTED_DRC.items()
    )


def validate(
    system_root: str | Path,
    *,
    refresh_summary: bool = False,
) -> dict:
    system = Path(system_root)
    altium = system / "altium"
    audit = altium / "routing" / "connection_audit"
    routing = altium / "routing"
    native_pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    summary_path = routing / "timing_routing_drc_summary.json"
    evidence = {
        "native_pcb": native_pcb,
        "pad_geometry": audit / "pad_geometry.csv",
        "track_inventory": audit / "track_inventory.csv",
        "fill_inventory": audit / "fill_inventory.csv",
        "via_inventory": audit / "via_inventory.csv",
        "drc_report": audit / "connection_drc_report.drc",
        "routing_script": altium / "scripts" / "EVT_SYS_CARRIER_TimingRouting.pas",
        "routing_audit_script": altium / "scripts" / "EVT_SYS_CARRIER_RoutingAudit.pas",
        "review_render_script": routing / "render_timing_routing_review.py",
        "review_render": routing / "timing_routing_review_a.png",
    }
    if not native_pcb.is_file():
        return {
            "schema": SCHEMA,
            "status": "NOT_APPLICABLE",
            "reason": "native_pcb_not_present",
            "production_authority": "NOT_AUTHORIZED",
            "errors": [],
        }
    errors = [f"missing:{name}" for name, path in evidence.items() if not path.is_file()]
    result: dict = {
        "schema": SCHEMA,
        "status": "FAIL",
        "routing_authority": "AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "canonical_pcb_sha256": sha256_file(native_pcb),
        "routes": {},
        "drc": {},
        "summary_binding": "FAIL",
        "errors": errors,
    }
    if errors:
        return result

    tracks = read_csv(evidence["track_inventory"])
    pads = read_csv(evidence["pad_geometry"])
    fills = read_csv(evidence["fill_inventory"])
    vias = read_csv(evidence["via_inventory"])
    route_payload: dict[str, dict] = {}
    for net, contract in TARGETS.items():
        net_tracks = [row for row in tracks if row.get("net_name") == net]
        net_vias = [row for row in vias if row.get("net_name") == net]
        endpoint_pads = [resolve_pad(pads, net, endpoint) for endpoint in contract["endpoints"]]
        resolved_pads = [pad for pad in endpoint_pads if pad is not None]
        connected, component_count = route_is_connected(net_tracks, resolved_pads)
        length_mm = sum(
            math.hypot(second[0] - first[0], second[1] - first[1])
            for first, second in map(track_segment, net_tracks)
        )
        widths = sorted({round(mm(row["width_mil"]), 6) for row in net_tracks})
        layers = sorted({int(row["layer"]) for row in net_tracks})
        clearance = quiet_clearance(net_tracks, tracks, fills, vias, pads)
        payload = {
            "segment_count": len(net_tracks),
            "via_count": len(net_vias),
            "layers": layers,
            "width_mm": widths,
            "length_mm": round(length_mm, 6),
            "endpoint_pads_resolved": len(resolved_pads),
            "connected": connected,
            "graph_component_count": component_count,
            "quiet_clearance_mm": round(clearance, 6),
        }
        route_payload[net] = payload
        if len(net_tracks) != contract["segments"]:
            errors.append(f"segment_count:{net}:{len(net_tracks)}")
        if net_vias:
            errors.append(f"target_via_count:{net}:{len(net_vias)}")
        if layers != [1]:
            errors.append(f"target_layer:{net}:{layers}")
        if len(widths) != 1 or abs(widths[0] - TRACK_WIDTH_MM) > 0.001:
            errors.append(f"target_width:{net}:{widths}")
        if len(resolved_pads) != 2:
            errors.append(f"endpoint_resolution:{net}:{len(resolved_pads)}")
        if not connected:
            errors.append(f"endpoint_connectivity:{net}")
        if clearance + 0.001 < MIN_QUIET_CLEARANCE_MM:
            errors.append(f"quiet_clearance:{net}:{clearance:.6f}")
    result["routes"] = route_payload

    pcb_file, drc_timestamp, drc_counts = parse_drc(evidence["drc_report"])
    no_new_drc_markers = drc_has_no_new_markers(drc_counts)
    result["drc"] = {
        "timestamp": drc_timestamp,
        "counts": drc_counts,
        "route_induced_markers": 0 if no_new_drc_markers else None,
    }
    if Path(pcb_file.replace("\\", "/")).name.lower() != "evt_sys_carrier.pcbdoc":
        errors.append("drc_not_canonical_pcb")
    for name, expected in EXPECTED_DRC.items():
        actual = drc_counts.get(name)
        if actual is None:
            errors.append(f"drc_count_missing:{name}")
        elif name in ZERO_DRC_RULES and actual != 0:
            errors.append(f"drc_count_nonzero:{name}:{actual}")
        elif name not in ZERO_DRC_RULES and actual > expected:
            errors.append(f"drc_count_increase:{name}:{actual}:{expected}")

    summary_payload = {
        "schema": SUMMARY_SCHEMA,
        "review_status": "PASS",
        "routing_authority": "AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "board_id": "EVT-SYS-CARRIER",
        "altium_version": "26.10.1 Trial",
        "drc_timestamp": drc_timestamp,
        "source_pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
        "source_pcb_sha256": sha256_file(native_pcb),
        "source_drc_report": "hardware/system_carrier/altium/routing/connection_audit/connection_drc_report.drc",
        "source_drc_report_sha256": sha256_evidence_file(evidence["drc_report"]),
        "geometry": {
            "pad_count": len(pads),
            "track_count": len(tracks),
            "fill_count": len(fills),
            "via_count": len(vias),
            "timing_track_count": sum(item["segment_count"] for item in route_payload.values()),
            "timing_via_count": sum(item["via_count"] for item in route_payload.values()),
            "trace_width_mm": TRACK_WIDTH_MM,
            "minimum_quiet_clearance_mm": round(
                min(item["quiet_clearance_mm"] for item in route_payload.values()), 6
            ),
            "routes": route_payload,
        },
        "rule_violations": {
            **drc_counts,
            "timing_route_induced": 0 if no_new_drc_markers else None,
        },
        "input_sha256": {
            name: sha256_evidence_file(path)
            for name, path in sorted(evidence.items())
            if name not in {"native_pcb", "drc_report"}
        },
    }
    if refresh_summary and not errors:
        summary_path.write_text(
            json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not summary_path.is_file():
        errors.append("missing:timing_routing_drc_summary.json")
    else:
        try:
            committed_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            committed_summary = {}
            errors.append("summary_parse")
        if committed_summary == summary_payload:
            result["summary_binding"] = "PASS"
        else:
            errors.append("summary_binding_mismatch")

    result["errors"] = sorted(set(errors))
    if not result["errors"]:
        result["status"] = "PASS"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate native Altium EVT timing-route evidence."
    )
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--refresh-summary", action="store_true")
    args = parser.parse_args()
    result = validate(args.system_root, refresh_summary=args.refresh_summary)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
