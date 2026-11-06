import json
import math
from pathlib import Path

import pcb_a10_planner as design


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "build-cad/pcb_a10_plan.json"
POWER_PLAN = ROOT / "build-cad/pcb_a10_power_plan.json"
OUTPUT = ROOT / "build-cad/pcb_a10_moved_pad_audit.json"
TOLERANCE = 0.02


def same_point(first, second):
    return math.hypot(first[0] - second[0], first[1] - second[1]) <= TOLERANCE


def audit():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    power_plan = json.loads(POWER_PLAN.read_text(encoding="utf-8"))
    power = {
        (item["designator"], item["pad_name"]): (item["net"], item["route"])
        for item in power_plan
    }
    mdi_endpoints = {}
    for net, _, first, second in design.MDI_REPLACEMENT_TRACKS:
        mdi_endpoints.setdefault(net, []).extend((first, second))

    results = []
    for row in design.rows("pad_geometry.csv"):
        designator = row["designator"]
        if designator not in design.PLACEMENT_SHIFT:
            continue
        pad_name = row["pad_name"]
        net = row["net_name"]
        point = design.row_point(row)
        method = None
        if (designator, pad_name) in power:
            stitch_net, points = power[designator, pad_name]
            route_start = points[0][1], points[0][2]
            if stitch_net == net and same_point(route_start, point):
                method = "power_connection"
        if method is None and net in plan:
            route_points = [
                (item[1], item[2])
                for route in plan[net]
                for item in route
                if item[0] == 0
            ]
            if any(same_point(item, point) for item in route_points):
                method = "signal_route"
        if method is None and any(same_point(item, point) for item in mdi_endpoints.get(net, [])):
            method = "mdi_replacement"
        results.append({
            "designator": designator,
            "pad_name": pad_name,
            "net": net,
            "x_mm": round(point[0], 6),
            "y_mm": round(point[1], 6),
            "covered": method is not None,
            "method": method,
        })

    report = {
        "moved_component_count": len(design.PLACEMENT_SHIFT),
        "moved_pad_count": len(results),
        "covered_count": sum(item["covered"] for item in results),
        "uncovered_count": sum(not item["covered"] for item in results),
        "pads": results,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "pads"}, indent=2))
    for item in results:
        print(f"{item['designator']}-{item['pad_name']} {item['net']}: {item['method'] or 'UNCOVERED'}")
    if report["uncovered_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    audit()
