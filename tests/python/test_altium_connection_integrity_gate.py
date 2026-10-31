from pathlib import Path

from tools.altium_connection_integrity_gate import validate


MECHANICAL = """kind,id,x_mm,y_mm,width_mm,height_mm,diameter_mm,layer,criticality,status,notes
BOARD,OUTLINE,0,0,100,80,,Mechanical,P0,EVT_ROUTING_LOCKED,test
"""


def _write_fixture(root: Path, *, pad_right: float = 110.0) -> None:
    altium = root / "altium"
    native = altium / "native"
    audit = altium / "routing" / "connection_audit"
    equivalence = altium / "equivalence"
    native.mkdir(parents=True)
    audit.mkdir(parents=True)
    equivalence.mkdir(parents=True)
    (native / "EVT_SYS_CARRIER.PcbDoc").write_bytes(b"native-pcb")
    (altium / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv").write_text(
        MECHANICAL,
        encoding="utf-8",
    )
    (equivalence / "pad_net_inventory.csv").write_text(
        "designator,pad_name,net_name\nU1,1,3V3\n",
        encoding="utf-8",
    )
    (audit / "component_bounds.csv").write_text(
        "designator,pattern,x_mil,y_mil,rotation_deg,layer,"
        "left_mil,bottom_mil,right_mil,top_mil\n"
        "U1,QFN,100,100,0,1,80,80,120,120\n",
        encoding="utf-8",
    )
    (audit / "pad_geometry.csv").write_text(
        "designator,pad_name,net_name,x_mil,y_mil,layer,hole_mil,"
        "x_size_mil,y_size_mil,left_mil,bottom_mil,right_mil,top_mil\n"
        f"U1,1,3V3,100,100,1,0,20,20,90,90,{pad_right},110\n",
        encoding="utf-8",
    )
    (audit / "track_inventory.csv").write_text(
        "net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,width_mil,"
        "left_mil,bottom_mil,right_mil,top_mil\n"
        "3V3,1,100,100,200,100,10,95,95,205,105\n",
        encoding="utf-8",
    )
    (audit / "fill_inventory.csv").write_text(
        "net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,rotation_deg,"
        "left_mil,bottom_mil,right_mil,top_mil\n",
        encoding="utf-8",
    )
    (audit / "via_inventory.csv").write_text(
        "net_name,x_mil,y_mil,size_mil,hole_mil,low_layer,high_layer,"
        "left_mil,bottom_mil,right_mil,top_mil\n",
        encoding="utf-8",
    )
    (audit / "connection_drc_report.drc").write_text(
        "Protel Design System Design Rule Check\n"
        "PCB File : C:\\work\\EVT_SYS_CARRIER.PcbDoc\n"
        "Processing Rule : Un-Routed Net Constraint ( (All) )\n"
        "Rule Violations :0\n"
        "Processing Rule : Routing Topology Rule(Topology=Shortest) (All)\n"
        "Rule Violations :0\n"
        "Processing Rule : Net Antennae (Tolerance=0mil) (All)\n"
        "Rule Violations :0\n",
        encoding="utf-8",
    )


def test_connection_integrity_passes_and_binds_receipt(tmp_path):
    _write_fixture(tmp_path)

    result = validate(tmp_path, refresh_receipt=True)

    assert result["status"] == "PASS"
    assert result["outside_board_count"] == 0
    assert result["endpoint_baseline_matches"] is True
    assert result["unrouted_net_violations"] == 0
    assert result["receipt_binding"] == "PASS"
    assert result["production_authority"] == "NOT_AUTHORIZED"


def test_connection_integrity_rejects_pad_beyond_board(tmp_path):
    _write_fixture(tmp_path, pad_right=4000.0)

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert result["outside_board_count"] == 1
    assert any(error.startswith("outside_board:pad:") for error in result["errors"])


def test_connection_integrity_rejects_stale_pcb_receipt(tmp_path):
    _write_fixture(tmp_path)
    assert validate(tmp_path, refresh_receipt=True)["status"] == "PASS"
    pcb = tmp_path / "altium" / "native" / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"changed-native-pcb")

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "receipt_binding_mismatch" in result["errors"]


def test_connection_integrity_receipt_is_stable_across_text_line_endings(
    tmp_path,
):
    _write_fixture(tmp_path)
    assert validate(tmp_path, refresh_receipt=True)["status"] == "PASS"
    track_path = (
        tmp_path / "altium" / "routing" / "connection_audit" /
        "track_inventory.csv"
    )
    track_bytes = track_path.read_bytes()
    track_bytes = track_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    track_path.write_bytes(track_bytes.replace(b"\n", b"\r\n"))

    result = validate(tmp_path)

    assert result["status"] == "PASS"
    assert result["receipt_binding"] == "PASS"


def test_connection_integrity_rejects_endpoint_drift(tmp_path):
    _write_fixture(tmp_path)
    pad_path = (
        tmp_path / "altium" / "routing" / "connection_audit" /
        "pad_geometry.csv"
    )
    pad_path.write_text(
        pad_path.read_text(encoding="utf-8").replace("U1,1,3V3", "U1,1,GND"),
        encoding="utf-8",
    )

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "endpoint_baseline_missing:1" in result["errors"]
    assert "endpoint_baseline_extra:1" in result["errors"]


def test_connection_integrity_reconciles_free_imported_pad(tmp_path):
    _write_fixture(tmp_path)
    pad_path = (
        tmp_path / "altium" / "routing" / "connection_audit" /
        "pad_geometry.csv"
    )
    pad_path.write_text(
        pad_path.read_text(encoding="utf-8").replace("U1,1,3V3", ",1,3V3"),
        encoding="utf-8",
    )

    result = validate(tmp_path, refresh_receipt=True)

    assert result["status"] == "PASS"
    assert result["endpoint_baseline_matches"] is True
    assert result["inferred_free_pad_count"] == 1
    assert result["free_pad_assignments"] == {"U1": 1}


def test_connection_integrity_ignores_exported_unowned_shadow_pad(tmp_path):
    _write_fixture(tmp_path)
    baseline_path = (
        tmp_path / "altium" / "equivalence" / "pad_net_inventory.csv"
    )
    baseline_path.write_text(
        "designator,pad_name,net_name\n"
        ",1,3V3\n"
        "U1,1,3V3\n",
        encoding="utf-8",
    )

    result = validate(tmp_path, refresh_receipt=True)

    assert result["status"] == "PASS"
    assert result["endpoint_baseline_matches"] is True
    assert result["baseline_shadow_pad_count"] == 1
