import csv
from pathlib import Path

from tools.altium_timing_routing_gate import validate


def _mil(value_mm: float) -> str:
    return f"{value_mm / 0.0254:.6f}"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _track(net: str, x1: float, y1: float, x2: float, y2: float, width=0.2):
    radius = width / 2.0
    return {
        "net_name": net,
        "layer": 1,
        "x1_mil": _mil(x1),
        "y1_mil": _mil(y1),
        "x2_mil": _mil(x2),
        "y2_mil": _mil(y2),
        "width_mil": _mil(width),
        "left_mil": _mil(min(x1, x2) - radius),
        "bottom_mil": _mil(min(y1, y2) - radius),
        "right_mil": _mil(max(x1, x2) + radius),
        "top_mil": _mil(max(y1, y2) + radius),
    }


def _pad(designator: str, name: str, net: str, x: float, y: float):
    return {
        "designator": designator,
        "pad_name": name,
        "net_name": net,
        "x_mil": _mil(x),
        "y_mil": _mil(y),
        "layer": 1,
        "hole_mil": 0,
        "x_size_mil": _mil(0.4),
        "y_size_mil": _mil(0.4),
        "left_mil": _mil(x - 0.2),
        "bottom_mil": _mil(y - 0.2),
        "right_mil": _mil(x + 0.2),
        "top_mil": _mil(y + 0.2),
    }


def _write_fixture(root: Path) -> None:
    altium = root / "altium"
    audit = altium / "routing" / "connection_audit"
    scripts = altium / "scripts"
    native = altium / "native"
    audit.mkdir(parents=True)
    scripts.mkdir(parents=True)
    native.mkdir(parents=True)
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"native-pcb")
    (scripts / "EVT_SYS_CARRIER_TimingRouting.pas").write_text(
        "timing route", encoding="utf-8"
    )
    (scripts / "EVT_SYS_CARRIER_RoutingAudit.pas").write_text(
        "audit", encoding="utf-8"
    )
    routing = altium / "routing"
    (routing / "render_timing_routing_review.py").write_text(
        "render", encoding="utf-8"
    )
    (routing / "timing_routing_review_a.png").write_bytes(b"png")

    tracks = []
    for net, y, count in (
        ("GNSS_PPS", 10.0, 10),
        ("IMU_DRDY", 20.0, 6),
        ("RADAR_REF", 30.0, 10),
    ):
        for index in range(count):
            tracks.append(_track(net, 10.0 + index, y, 11.0 + index, y))
    tracks.append(_track("BUCK_SW", 10.0, 50.0, 20.0, 50.0, width=0.5))
    _write_csv(
        audit / "track_inventory.csv",
        [
            "net_name", "layer", "x1_mil", "y1_mil", "x2_mil", "y2_mil",
            "width_mil", "left_mil", "bottom_mil", "right_mil", "top_mil",
        ],
        tracks,
    )
    pads = [
        _pad("U8", "3", "GNSS_PPS", 10.0, 10.0),
        _pad("U1", "40", "GNSS_PPS", 20.0, 10.0),
        _pad("U2", "4", "IMU_DRDY", 10.0, 20.0),
        _pad("U1", "80", "IMU_DRDY", 16.0, 20.0),
        _pad("U1", "79", "RADAR_REF", 10.0, 30.0),
        _pad("J4", "4", "RADAR_REF", 95.0, 33.0),
    ]
    pads[-1] = _pad("J4", "4", "RADAR_REF", 95.0, 33.0)
    tracks[-2] = _track("RADAR_REF", 18.0, 30.0, 95.0, 33.0)
    _write_csv(
        audit / "track_inventory.csv",
        [
            "net_name", "layer", "x1_mil", "y1_mil", "x2_mil", "y2_mil",
            "width_mil", "left_mil", "bottom_mil", "right_mil", "top_mil",
        ],
        tracks,
    )
    _write_csv(
        audit / "pad_geometry.csv",
        [
            "designator", "pad_name", "net_name", "x_mil", "y_mil", "layer",
            "hole_mil", "x_size_mil", "y_size_mil", "left_mil", "bottom_mil",
            "right_mil", "top_mil",
        ],
        pads,
    )
    _write_csv(
        audit / "fill_inventory.csv",
        [
            "net_name", "layer", "x1_mil", "y1_mil", "x2_mil", "y2_mil",
            "rotation_deg", "left_mil", "bottom_mil", "right_mil", "top_mil",
        ],
        [],
    )
    _write_csv(
        audit / "via_inventory.csv",
        [
            "net_name", "x_mil", "y_mil", "size_mil", "hole_mil",
            "low_layer", "high_layer", "left_mil", "bottom_mil", "right_mil",
            "top_mil",
        ],
        [],
    )
    (audit / "connection_drc_report.drc").write_text(
        "Altium Designer 26.10.1 Native Design Rule Check Summary\n"
        "PCB File : C:\\work\\EVT_SYS_CARRIER.PcbDoc\n"
        "Date     : 24.10.2026\n"
        "Time     : 21:26:20\n"
        "Warnings : 0\n"
        "Processing Rule : Clearance Constraint (Gap=7.874mil) (All),(All)\n"
        "Rule Violations :27\n"
        "Processing Rule : Clearance Constraint (Gap=10mil) (All),(All)\n"
        "Rule Violations :0\n"
        "Processing Rule : Clearance Constraint (Gap=39.37mil) (InNetClass('NC_TIMING')),(InNet('BUCK_SW'))\n"
        "Rule Violations :0\n"
        "Processing Rule : Clearance Constraint (Gap=7.874mil) (InDifferentialPairClass('DP_ETH_MDI')),(Not InDifferentialPairClass('DP_ETH_MDI'))\n"
        "Rule Violations :27\n"
        "Processing Rule : Un-Routed Net Constraint ( (All) )\n"
        "Rule Violations :0\n"
        "Processing Rule : Routing Topology Rule(Topology=Shortest) (All)\n"
        "Rule Violations :0\n"
        "Processing Rule : Power Plane Connect Rule(Relief Connect ) (All)\n"
        "Rule Violations :0\n"
        "Processing Rule : Hole Size Constraint (All)\n"
        "Rule Violations :9\n"
        "Processing Rule : Hole To Hole Clearance (All),(All)\n"
        "Rule Violations :1\n"
        "Processing Rule : Net Antennae (Tolerance=0mil) (All)\n"
        "Rule Violations :0\n"
        "Processing Rule : Component Clearance Constraint (All),(All)\n"
        "Rule Violations :55\n"
        "Violations Detected : 119\n",
        encoding="utf-8",
    )


def test_timing_routing_passes_and_binds_summary(tmp_path):
    _write_fixture(tmp_path)

    result = validate(tmp_path, refresh_summary=True)

    assert result["status"] == "PASS"
    assert result["summary_binding"] == "PASS"
    assert result["routes"]["GNSS_PPS"]["connected"] is True
    assert result["routes"]["IMU_DRDY"]["segment_count"] == 6
    assert result["routes"]["RADAR_REF"]["via_count"] == 0
    assert result["drc"]["route_induced_markers"] == 0
    assert result["production_authority"] == "NOT_AUTHORIZED"


def test_timing_routing_accepts_native_report_without_zero_warning_line(tmp_path):
    _write_fixture(tmp_path)
    drc_path = (
        tmp_path
        / "altium"
        / "routing"
        / "connection_audit"
        / "connection_drc_report.drc"
    )
    drc_path.write_text(
        drc_path.read_text(encoding="utf-8").replace("Warnings : 0\n", ""),
        encoding="utf-8",
    )

    result = validate(tmp_path, refresh_summary=True)

    assert result["status"] == "PASS"
    assert result["drc"]["counts"]["warnings"] == 0


def test_timing_routing_rejects_disconnected_route(tmp_path):
    _write_fixture(tmp_path)
    assert validate(tmp_path, refresh_summary=True)["status"] == "PASS"
    track_path = tmp_path / "altium" / "routing" / "connection_audit" / "track_inventory.csv"
    rows = list(csv.DictReader(track_path.open(encoding="utf-8")))
    rows[3]["x1_mil"] = _mil(13.5)
    _write_csv(track_path, list(rows[0]), rows)

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "endpoint_connectivity:GNSS_PPS" in result["errors"]


def test_timing_routing_rejects_narrow_quiet_clearance(tmp_path):
    _write_fixture(tmp_path)
    track_path = tmp_path / "altium" / "routing" / "connection_audit" / "track_inventory.csv"
    rows = list(csv.DictReader(track_path.open(encoding="utf-8")))
    rows[-1] = _track("BUCK_SW", 10.0, 10.6, 17.0, 10.6, width=0.5)
    _write_csv(track_path, list(rows[0]), rows)

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert any(error.startswith("quiet_clearance:GNSS_PPS:") for error in result["errors"])


def test_timing_routing_rejects_width_drift(tmp_path):
    _write_fixture(tmp_path)
    track_path = tmp_path / "altium" / "routing" / "connection_audit" / "track_inventory.csv"
    rows = list(csv.DictReader(track_path.open(encoding="utf-8")))
    rows[0]["width_mil"] = _mil(0.15)
    _write_csv(track_path, list(rows[0]), rows)

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert any(error.startswith("target_width:GNSS_PPS:") for error in result["errors"])


def test_timing_summary_is_stable_across_text_line_endings(tmp_path):
    _write_fixture(tmp_path)
    assert validate(tmp_path, refresh_summary=True)["status"] == "PASS"
    track_path = tmp_path / "altium" / "routing" / "connection_audit" / "track_inventory.csv"
    data = track_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    track_path.write_bytes(data)

    result = validate(tmp_path)

    assert result["status"] == "PASS"
    assert result["summary_binding"] == "PASS"
