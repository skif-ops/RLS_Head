from pathlib import Path

from tools.altium_evt_mechanical_datum_gate import validate


MECHANICAL = """kind,id,x_mm,y_mm,width_mm,height_mm,diameter_mm,layer,criticality,status,notes
BOARD,OUTLINE,0,0,100,80,,Mechanical,P0,EVT_ROUTING_LOCKED,test
BOARD,THICKNESS,,,,1.6,,Stackup,P0,LOCKED_FOR_EVT,test
BOARD,CORNER_RADIUS,,,,3,,Mechanical,P1,EVT_ROUTING_LOCKED,test
HOLE,H1,5,5,,,3.2,MultiLayer,P0,EVT_ROUTING_LOCKED,test
HOLE,H2,95,5,,,3.2,MultiLayer,P0,EVT_ROUTING_LOCKED,test
HOLE,H3,5,75,,,3.2,MultiLayer,P0,EVT_ROUTING_LOCKED,test
HOLE,H4,95,75,,,3.2,MultiLayer,P0,EVT_ROUTING_LOCKED,test
CONNECTOR_RULE,MICROFIT_EDGE,,,,10.16,,Mechanical,P0,LOCKED_FOR_EVT,test
"""

PLACEMENT = """ref,x_mm,y_mm,edge,side,zone,lock_level,status,notes
J1,5,14,LEFT,TOP,ZONE_PWR,HARD,EVT_ROUTING_LOCKED,test
J4,95,30,RIGHT,TOP,ZONE_CAN,HARD,EVT_ROUTING_LOCKED,test
J5,95,14,RIGHT,TOP,ZONE_PWR,HARD,EVT_ROUTING_LOCKED,test
J6,94.75,60,RIGHT,TOP,ZONE_ETH,HARD,EVT_ROUTING_LOCKED,test
J8,5,66,LEFT,TOP,ZONE_GNSS,HARD,EVT_ROUTING_LOCKED,test
J10,50,5,BOTTOM,TOP,ZONE_DEBUG,HARD,EVT_ROUTING_LOCKED,test
"""


def _write_fixture(root: Path, *, placement: str = PLACEMENT) -> None:
    altium = root / "altium"
    altium.mkdir(parents=True)
    (altium / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv").write_text(
        MECHANICAL,
        encoding="utf-8",
    )
    (altium / "ALTIUM_PLACEMENT_COORD_SYS_002.csv").write_text(
        placement,
        encoding="utf-8",
    )


def test_evt_mechanical_datum_gate_passes_locked_baseline(tmp_path):
    _write_fixture(tmp_path)

    result = validate(tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["evt_routing_datums_locked"] is True
    assert result["production_mechanical_freeze"] is False
    assert result["board_baseline"]["width_mm"] == 100.0
    assert result["board_baseline"]["height_mm"] == 80.0
    assert result["minimum_mount_hole_edge_ligament_mm"] == 3.4
    assert set(result["connector_datums"]) == {
        "J1",
        "J4",
        "J5",
        "J6",
        "J8",
        "J10",
    }


def test_evt_mechanical_datum_gate_rejects_shifted_connector(tmp_path):
    shifted = PLACEMENT.replace(
        "J6,94.75,60,RIGHT",
        "J6,92,60,RIGHT",
    )
    _write_fixture(tmp_path, placement=shifted)

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "connector_position_baseline:J6" in result["errors"]
    assert result["evt_routing_datums_locked"] is False


def test_evt_mechanical_datum_gate_rejects_provisional_hole(tmp_path):
    altium = tmp_path / "altium"
    altium.mkdir(parents=True)
    mechanical = MECHANICAL.replace(
        "HOLE,H2,95,5,,,3.2,MultiLayer,P0,EVT_ROUTING_LOCKED",
        "HOLE,H2,95,5,,,3.2,MultiLayer,P0,EVT_PROVISIONAL",
    )
    (altium / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv").write_text(
        mechanical,
        encoding="utf-8",
    )
    (altium / "ALTIUM_PLACEMENT_COORD_SYS_002.csv").write_text(
        PLACEMENT,
        encoding="utf-8",
    )

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "mount_hole_not_evt_routing_locked:H2" in result["errors"]
    assert result["production_mechanical_freeze"] is False
