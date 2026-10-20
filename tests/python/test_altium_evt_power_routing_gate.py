import json
from pathlib import Path

from tools.altium_evt_power_routing_gate import validate


POWER = """model_id,net_or_class,current_a,copper_um,allowed_temp_rise_c,calculated_min_width_mm,selected_width_mm,status,notes
PWR-001,VIN_RAW,5.00,35,10,2.77,3.00,EVT_CALCULATED,test
PWR-002,VIN_PROTECTED,5.00,35,10,2.77,3.00,EVT_CALCULATED,test
PWR-003,RADAR_12V,3.18,35,10,1.48,1.50,EVT_CALCULATED,test
PWR-004,3V3_TRUNK,3.00,35,10,1.37,1.50,EVT_CALCULATED,test
"""

RULES = """rule_id,scope,parameter,value,unit,status,notes
RV-006,VIN_RAW,min_neck_width,3.00,mm,EVT_CALCULATED,test
RV-007,RADAR_12V,min_neck_width,1.50,mm,EVT_BASELINE,test
RV-008,3V3,min_trunk_width,1.50,mm,EVT_CALCULATED,test
RV-023,VIN_PROTECTED,min_neck_width,3.00,mm,EVT_CALCULATED,test
RV-024,POWER_EXTERNAL,screen_temp_rise,10,C,EVT_CALCULATED,test
"""

BUDGET = """rail,load,nominal_voltage,min_voltage,max_voltage,peak_current,average_current,capacity,unit,source,status,notes
12V_IN,System,12,10,14,5,3,5,A,test,LOCKED,test
RADAR_12V,Radar,12,10,14,3.18,2,3.18,A,test,LOCKED,test
3V3,Digital,3.3,3.2,3.4,3,2,3,A,test,LOCKED,test
"""


def _contract() -> dict:
    return {
        "schema": "ALTIUM-EVT-POWER-ROUTING-LOCK-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "status": "EVT_ROUTING_LOCKED",
        "method": "IPC-2221_EXTERNAL_TRACE_SCREEN",
        "copper_um": 35,
        "allowed_temp_rise_c": 10,
        "nets": {
            "VIN_RAW": {
                "current_a": 5.0,
                "min_neck_width_mm": 3.0,
                "rule_id": "RV-006",
            },
            "VIN_PROTECTED": {
                "current_a": 5.0,
                "min_neck_width_mm": 3.0,
                "rule_id": "RV-023",
            },
            "RADAR_12V": {
                "current_a": 3.18,
                "min_neck_width_mm": 1.5,
                "rule_id": "RV-007",
            },
            "3V3_TRUNK": {
                "current_a": 3.0,
                "min_neck_width_mm": 1.5,
                "rule_id": "RV-008",
            },
        },
        "locked_sources": [
            "hardware/system_carrier/altium/ALTIUM_POWER_WIDTH_SYS_001.csv",
            "hardware/system_carrier/altium/ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
            "hardware/system_carrier/POWER_BUDGET_SYS_001.csv",
        ],
        "routing_policy": {
            "prefer_polygons_or_pours": True,
            "selected_widths_are_minimum_necks": True,
            "local_pin_neckdown_allowed_only_when_required": True,
        },
        "production": {
            "final_copper_weight_review_required": True,
            "final_stack_review_required": True,
            "thermal_review_required": True,
            "production_power_geometry_locked": False,
        },
    }


def _write_fixture(root: Path) -> None:
    altium = root / "altium"
    altium.mkdir(parents=True)
    (altium / "ALTIUM_POWER_WIDTH_SYS_001.csv").write_text(
        POWER, encoding="utf-8"
    )
    (altium / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv").write_text(
        RULES, encoding="utf-8"
    )
    (root / "POWER_BUDGET_SYS_001.csv").write_text(
        BUDGET, encoding="utf-8"
    )
    (altium / "ALTIUM_EVT_POWER_ROUTING_LOCK_SYS_001.json").write_text(
        json.dumps(_contract(), indent=2) + "\n",
        encoding="utf-8",
    )


def test_evt_power_routing_gate_passes_locked_baseline(tmp_path):
    _write_fixture(tmp_path)

    result = validate(tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["evt_power_routing_locked"] is True
    assert result["production_power_geometry_locked"] is False
    assert result["production_review_required"] is True
    assert len(result["models"]) == 4


def test_evt_power_routing_gate_rejects_width_drift(tmp_path):
    _write_fixture(tmp_path)
    path = tmp_path / "altium/ALTIUM_POWER_WIDTH_SYS_001.csv"
    path.write_text(
        POWER.replace("PWR-002,VIN_PROTECTED,5.00,35,10,2.77,3.00",
                      "PWR-002,VIN_PROTECTED,5.00,35,10,2.77,2.90"),
        encoding="utf-8",
    )

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "power_selected_width:VIN_PROTECTED" in result["errors"]


def test_evt_power_routing_gate_rejects_false_production_lock(tmp_path):
    _write_fixture(tmp_path)
    path = tmp_path / "altium/ALTIUM_EVT_POWER_ROUTING_LOCK_SYS_001.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["production"]["production_power_geometry_locked"] = True
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    result = validate(tmp_path)

    assert result["status"] == "FAIL"
    assert "production_power_geometry_locked_must_be_false" in result["errors"]
