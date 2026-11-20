from pathlib import Path

from tools.altium_evt_mechanical_datum_gate import validate


MECHANICAL = """kind,id,x_mm,y_mm,width_mm,height_mm,diameter_mm,layer,criticality,status,notes
BOARD,OUTLINE,0,0,90,70,,Mechanical,P0,ECO_CANDIDATE,test
BOARD,THICKNESS,,,,1.6,,Stackup,P0,LOCKED_FOR_EVT,test
BOARD,CORNER_RADIUS,,,,3,,Mechanical,P1,ECO_CANDIDATE,test
HOLE,H1,5,5,,,3.2,MultiLayer,P0,ECO_CANDIDATE,test
HOLE,H2,85,5,,,3.2,MultiLayer,P0,ECO_CANDIDATE,test
HOLE,H3,5,65,,,3.2,MultiLayer,P0,ECO_CANDIDATE,test
HOLE,H4,85,65,,,3.2,MultiLayer,P0,ECO_CANDIDATE,test
CONNECTOR_RULE,MICROFIT_EDGE,,,,10.16,,Mechanical,P0,LOCKED_FOR_EVT,test
"""

PLACEMENT = """ref,x_mm,y_mm,edge,side,zone,lock_level,status,notes
J1,5,14,LEFT,TOP,ZONE_PWR,HARD,ECO_CANDIDATE,test
J4,85,29,RIGHT,TOP,ZONE_CAN,HARD,ECO_CANDIDATE,test
J5,85,14,RIGHT,TOP,ZONE_PWR,HARD,ECO_CANDIDATE,test
J6,85,54,RIGHT,TOP,ZONE_UART,HARD,ECO_CANDIDATE,test
J8,5,57,LEFT,TOP,ZONE_GNSS,HARD,ECO_CANDIDATE,test
J10,45,5,BOTTOM,TOP,ZONE_DEBUG,HARD,ECO_CANDIDATE,test
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
    assert result["evt_routing_datums_locked"] is False
    assert result["compact_candidate_validated"] is True
    assert result["production_mechanical_freeze"] is False
    assert result["board_baseline"]["width_mm"] == 90.0
    assert result["board_baseline"]["height_mm"] == 70.0
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
        "J6,85,54,RIGHT",
        "J6,82,54,RIGHT",
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
        "HOLE,H2,85,5,,,3.2,MultiLayer,P0,ECO_CANDIDATE",
        "HOLE,H2,85,5,,,3.2,MultiLayer,P0,EVT_PROVISIONAL",
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
    assert "mount_hole_status:H2" in result["errors"]
    assert result["production_mechanical_freeze"] is False
