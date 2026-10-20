import json
from pathlib import Path

from tools.altium_evt_routing_stack_gate import validate


STACK = """sequence,item,altium_layer,material,thickness_mm,copper_um,er_nominal,status,notes
1,COPPER,L1 Top Layer,Copper,0.035,35,,EVT_PROVISIONAL,test
2,DIELECTRIC,L1-L2,FR-4 prepreg,0.180,,4.2,EVT_PROVISIONAL,test
3,COPPER,L2 Mid-Layer 1,Copper,0.035,35,,EVT_PROVISIONAL,test
4,DIELECTRIC,L2-L3,FR-4 core,1.100,,4.2,EVT_PROVISIONAL,test
5,COPPER,L3 Mid-Layer 2,Copper,0.035,35,,EVT_PROVISIONAL,test
6,DIELECTRIC,L3-L4,FR-4 prepreg,0.180,,4.2,EVT_PROVISIONAL,test
7,COPPER,L4 Bottom Layer,Copper,0.035,35,,EVT_PROVISIONAL,test
"""

IMPEDANCE = """model_id,net_class,structure,signal_layer,reference_layer,dielectric_height_mm,er_nominal,copper_um,trace_width_mm,pair_gap_mm,target_ohm,calculated_ohm,tolerance_pct,status,notes
IMP-001,GNSS_RF,MICROSTRIP,L1,L2,0.180,4.2,35,0.360,,50,49.93,10,EVT_CALCULATED,test
IMP-002,ETH_MDI,EDGE_COUPLED_MICROSTRIP,L1,L2,0.180,4.2,35,0.260,0.200,100,100.45,10,EVT_CALCULATED,test
"""

RULES = """rule_id,scope,parameter,value,unit,status,notes
RV-019,ETH_MDI,evt_trace_width,0.26,mm,EVT_CALCULATED,test
RV-020,ETH_MDI,evt_pair_gap,0.20,mm,EVT_CALCULATED,test
RV-021,GNSS_RF,evt_trace_width,0.36,mm,EVT_CALCULATED,test
RV-022,STACKUP,L1_L2_dielectric,0.18,mm,EVT_PROVISIONAL,test
"""


def _contract() -> dict:
    return {
        "schema": "ALTIUM-EVT-ROUTING-STACK-LOCK-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "status": "EVT_ROUTING_LOCKED",
        "stack": {
            "total_thickness_mm": 1.6,
            "copper_um": 35,
            "l1_l2": {"thickness_mm": 0.18, "er_nominal": 4.2},
            "l2_l3": {"thickness_mm": 1.10, "er_nominal": 4.2},
            "l3_l4": {"thickness_mm": 0.18, "er_nominal": 4.2},
        },
        "impedance": {
            "GNSS_RF": {
                "structure": "MICROSTRIP",
                "signal_layer": "L1",
                "reference_layer": "L2",
                "target_ohm": 50,
                "trace_width_mm": 0.36,
                "pair_gap_mm": None,
                "tolerance_pct": 10,
            },
            "ETH_MDI": {
                "structure": "EDGE_COUPLED_MICROSTRIP",
                "signal_layer": "L1",
                "reference_layer": "L2",
                "target_ohm": 100,
                "trace_width_mm": 0.26,
                "pair_gap_mm": 0.20,
                "tolerance_pct": 10,
            },
        },
        "locked_sources": [
            "hardware/system_carrier/altium/ALTIUM_EVT_STACKUP_SYS_002.csv",
            "hardware/system_carrier/altium/ALTIUM_IMPEDANCE_START_SYS_001.csv",
            "hardware/system_carrier/altium/ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
        ],
        "production": {
            "fabricator_binding_required": True,
            "field_solver_required": True,
            "impedance_coupon_or_fabricator_control_required": True,
            "production_stack_locked": False,
        },
    }


def _write_fixture(root: Path) -> None:
    altium = root / "altium"
    altium.mkdir(parents=True)
    (altium / "ALTIUM_EVT_STACKUP_SYS_002.csv").write_text(
        STACK, encoding="utf-8"
    )
    (altium / "ALTIUM_IMPEDANCE_START_SYS_001.csv").write_text(
        IMPEDANCE, encoding="utf-8"
    )
    (altium / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv").write_text(
        RULES, encoding="utf-8"
    )
    (altium / "ALTIUM_EVT_ROUTING_STACK_LOCK_SYS_001.json").write_text(
        json.dumps(_contract(), indent=2) + "\n",
        encoding="utf-8",
    )


def test_evt_routing_stack_gate_passes_locked_baseline(tmp_path):
    _write_fixture(tmp_path)

    result = validate(tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["evt_routing_stack_locked"] is True
    assert result["production_stack_locked"] is False
    assert result["production_binding_required"] is True
    assert result["field_solver_required"] is True
    assert result["stack_total_mm"] == 1.6
    assert len(result["impedance_models"]) == 2


def test_evt_routing_stack_gate_rejects_trace_width_drift(tmp_path):
    _write_fixture(tmp_path)
    path = tmp_path / "altium/ALTIUM_IMPEDANCE_START_SYS_001.csv"
    path.write_text(
        IMPEDANCE.replace(",0.360,,50,", ",0.400,,50,"),
        encoding="utf-8",
    )

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "impedance_trace_width_mm:GNSS_RF" in result["errors"]


def test_evt_routing_stack_gate_rejects_false_production_lock(tmp_path):
    _write_fixture(tmp_path)
    path = tmp_path / "altium/ALTIUM_EVT_ROUTING_STACK_LOCK_SYS_001.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["production"]["production_stack_locked"] = True
    path.write_text(
        json.dumps(contract, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "production_stack_locked_must_be_false" in result["errors"]
