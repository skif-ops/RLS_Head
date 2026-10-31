import csv
from pathlib import Path

from tools.altium_native_audit_validate import _coord_from_mm, validate


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware" / "system_carrier"


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _contract_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _native_fixture(tmp_path: Path, *, drop_last_rule: bool = False) -> None:
    bom = _contract_rows(SYSTEM / "BOM_SYS_CARRIER_LAYOUT_004.csv")
    netlist = _contract_rows(SYSTEM / "NETLIST_SYS_001.csv")
    rule_contract = _contract_rows(
        SYSTEM / "altium" / "ALTIUM_RULE_QUERY_SYS_001.csv"
    )
    pinmap = _contract_rows(SYSTEM / "PINMAP_SYS_001.csv")
    symbol_pins = _contract_rows(
        SYSTEM / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    )
    layer_stack = _contract_rows(
        SYSTEM / "altium" / "ALTIUM_LAYER_STACK_SYS_001.csv"
    )
    pair_contract = _contract_rows(
        SYSTEM / "altium" / "ALTIUM_DIFF_PAIRS_SYS_001.csv"
    )
    class_contract = _contract_rows(
        SYSTEM / "altium" / "ALTIUM_NET_CLASSES_SYS_001.csv"
    )
    stack_contract = _contract_rows(
        SYSTEM / "altium" / "ALTIUM_EVT_STACKUP_SYS_002.csv"
    )

    _write_csv(
        tmp_path / "component_inventory.csv",
        ["designator", "pattern", "x_mil", "y_mil"],
        [
            {
                "designator": row["ref"],
                "pattern": "AUDIT_PATTERN",
                "x_mil": "0",
                "y_mil": "0",
            }
            for row in bom
        ],
    )
    _write_csv(
        tmp_path / "net_inventory.csv",
        ["net_name"],
        [
            {"net_name": row["net_name"]}
            for row in netlist
            if row.get("net_name")
        ],
    )

    rule_rows = rule_contract[:-1] if drop_last_rule else rule_contract
    _write_csv(
        tmp_path / "rule_inventory.csv",
        [
            "rule_name",
            "rule_kind",
            "unique_id",
            "scope_1",
            "scope_2",
            "drc_enabled",
        ],
        [
            {
                "rule_name": row["rule_name"],
                "rule_kind": (
                    "DiffPairsRouting"
                    if row["rule_family"] == "DifferentialPairRouting"
                    else row["rule_family"]
                ),
                "unique_id": "TEST",
                "scope_1": row["scope_1"],
                "scope_2": row["scope_2"],
                "drc_enabled": "true",
            }
            for row in rule_rows
        ],
    )

    constraint_rows = []
    for row in rule_rows:
        if row["rule_family"] == "Clearance":
            constraint_rows.append({
                "rule_name": row["rule_name"],
                "layer_name": "All",
                "min_gap_raw": str(_coord_from_mm(row["min_value"])),
            })
            continue
        for layer in layer_stack:
            record = {
                "rule_name": row["rule_name"],
                "layer_name": layer["altium_layer"],
                "min_width_raw": str(_coord_from_mm(row["min_value"])),
                "preferred_width_raw": str(_coord_from_mm(row["preferred_value"])),
                "max_width_raw": str(_coord_from_mm(row["max_value"])),
            }
            if row["rule_family"] == "DifferentialPairRouting":
                record.update({
                    "min_gap_raw": str(_coord_from_mm(row["gap_min_mm"])),
                    "preferred_gap_raw": str(_coord_from_mm(row["gap_preferred_mm"])),
                    "max_gap_raw": str(_coord_from_mm(row["gap_max_mm"])),
                })
            constraint_rows.append(record)
    _write_csv(
        tmp_path / "rule_constraint_inventory.csv",
        [
            "rule_name", "layer_name", "min_width_raw",
            "preferred_width_raw", "max_width_raw", "min_gap_raw",
            "preferred_gap_raw", "max_gap_raw",
        ],
        constraint_rows,
    )

    pad_records: dict[tuple[str, str], str] = {}
    for row in pinmap:
        if row.get("physical_pin") and row.get("net_name"):
            pad_records[("U1", row["physical_pin"])] = row["net_name"]

    for row in symbol_pins:
        if row.get("policy") != "CONNECT":
            continue
        ref = row.get("ref", "")
        pin = row.get("pin_number", "")
        net = row.get("connection", "")
        if ref and pin and net:
            pad_records[(ref, pin)] = net

    _write_csv(
        tmp_path / "pad_net_inventory.csv",
        ["designator", "pad_name", "net_name"],
        [
            {
                "designator": ref,
                "pad_name": pin,
                "net_name": net,
            }
            for (ref, pin), net in sorted(pad_records.items())
        ],
    )

    _write_csv(
        tmp_path / "layer_stack_inventory.csv",
        ["order", "layer_name"],
        [
            {
                "order": row["order"],
                "layer_name": row["altium_layer"],
            }
            for row in layer_stack
        ],
    )

    xy = [
        (3, 0, "arc"), (0, 3, "line"),
        (0, 67, "arc"), (3, 70, "line"),
        (87, 70, "arc"), (90, 67, "line"),
        (90, 3, "arc"), (87, 0, "line"),
    ]
    mechanical_rows = [{
        "kind": "outline", "id": "board", "x_raw": "0", "y_raw": "0",
        "width_raw": str(_coord_from_mm("90")),
        "height_raw": str(_coord_from_mm("70")),
    }]
    mechanical_rows.extend({
        "kind": "vertex", "id": str(index),
        "x_raw": str(_coord_from_mm(px)),
        "y_raw": str(_coord_from_mm(py)),
        "diameter_raw": str(_coord_from_mm("3")) if shape == "arc" else "",
        "details": shape,
    } for index, (px, py, shape) in enumerate(xy))
    mechanical_rows.extend({
        "kind": "free_hole", "id": f"H{index}",
        "x_raw": str(_coord_from_mm(px)),
        "y_raw": str(_coord_from_mm(py)),
        "diameter_raw": str(_coord_from_mm("3.2")),
        "plated": "false",
    } for index, (px, py) in enumerate(((5, 5), (85, 5), (5, 65), (85, 65)), 1))
    _write_csv(
        tmp_path / "mechanical_inventory.csv",
        ["kind", "id", "x_raw", "y_raw", "width_raw", "height_raw",
         "diameter_raw", "plated", "details"],
        mechanical_rows,
    )
    _write_csv(
        tmp_path / "diff_pair_inventory.csv",
        ["pair_name", "positive_net", "negative_net"],
        [{key: row[key] for key in ("pair_name", "positive_net", "negative_net")}
         for row in pair_contract],
    )
    class_rows = [
        {"class_name": row["class_id"], "member_kind": "Net", "member_name": net}
        for row in class_contract for net in row["nets"].split(";")
    ]
    class_rows.extend(
        {"class_name": row["pair_class"], "member_kind": "DifferentialPair",
         "member_name": row["pair_name"]}
        for row in pair_contract
    )
    _write_csv(
        tmp_path / "class_inventory.csv",
        ["class_name", "member_kind", "member_name"],
        class_rows,
    )
    detail_rows = []
    for index, layer in enumerate(layer_stack):
        detail_rows.append({
            "layer_name": layer["altium_layer"],
            "copper_thickness_raw": str(_coord_from_mm(stack_contract[index * 2]["thickness_mm"])),
            "dielectric_height_raw": (
                str(_coord_from_mm(stack_contract[index * 2 + 1]["thickness_mm"]))
                if index < 3 else ""
            ),
            "dielectric_er": stack_contract[index * 2 + 1]["er_nominal"] if index < 3 else "",
        })
    _write_csv(
        tmp_path / "layer_stack_detail.csv",
        ["layer_name", "copper_thickness_raw", "dielectric_height_raw", "dielectric_er"],
        detail_rows,
    )
    _write_csv(
        tmp_path / "polygon_inventory.csv",
        [
            "polygon_name", "layer_name", "net_name", "polygon_type",
            "hatch_style", "point_count", "outline_point_count",
            "outline_match", "remove_dead", "remove_islands_by_area",
            "remove_narrow_necks",
        ],
        [{
            "polygon_name": "EVT_GND_L2_PLANE",
            "layer_name": "Mid-Layer 1",
            "net_name": "GND",
            "polygon_type": "SignalLayer",
            "hatch_style": "Solid",
            "point_count": "8",
            "outline_point_count": "8",
            "outline_match": "true",
            "remove_dead": "false",
            "remove_islands_by_area": "false",
            "remove_narrow_necks": "false",
        }],
    )


def test_native_audit_validator_passes_complete_fixture(tmp_path):
    _native_fixture(tmp_path)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["component_count"] == result["expected_component_count"]
    assert result["required_rule_count"] == 9
    assert result["pinmap_checked_count"] > 0
    assert result["symbol_pin_checked_count"] > 0
    assert result["symbol_pin_semantic_deferred_count"] > 0
    assert result["layer_stack_count"] == 4
    assert result["verified_checks"] == {
        "native_pcb_audit": "PASS",
        "mechanical_equivalence": "PASS",
        "pair_class_equivalence": "PASS",
        "pinmap_equivalence": "PASS",
        "rules_equivalence": "PASS",
        "stackup_equivalence": "PASS",
    }
    assert set(result["input_sha256"]) == {
        "component_inventory",
        "net_inventory",
        "rule_inventory",
        "rule_constraint_inventory",
        "pad_net_inventory",
        "layer_stack_inventory",
        "mechanical_inventory",
        "diff_pair_inventory",
        "class_inventory",
        "layer_stack_detail",
        "polygon_inventory",
    }
    assert all(
        len(value) == 64
        for value in result["input_sha256"].values()
    )


def test_native_audit_validator_detects_missing_rule(tmp_path):
    _native_fixture(tmp_path, drop_last_rule=True)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("missing_rules:")
        for item in result["errors"]
    )


def test_native_audit_validator_detects_pinmap_mismatch(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "pad_net_inventory.csv"
    rows = _contract_rows(path)
    for row in rows:
        if row["designator"] == "U1":
            row["net_name"] = "WRONG_NET"
            break
    _write_csv(
        path,
        ["designator", "pad_name", "net_name"],
        rows,
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("pinmap_net_mismatch:")
        for item in result["errors"]
    )


def test_native_audit_validator_detects_layer_stack_mismatch(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "layer_stack_inventory.csv"
    rows = _contract_rows(path)
    rows[1]["layer_name"] = "Wrong Layer"
    _write_csv(path, ["order", "layer_name"], rows)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("layer_stack_mismatch:")
        for item in result["errors"]
    )


def test_native_audit_validator_detects_missing_gnd_l2_plane(tmp_path):
    _native_fixture(tmp_path)
    _write_csv(
        tmp_path / "polygon_inventory.csv",
        [
            "polygon_name", "layer_name", "net_name", "polygon_type",
            "hatch_style", "point_count", "outline_point_count",
            "outline_match", "remove_dead", "remove_islands_by_area",
            "remove_narrow_necks",
        ],
        [],
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert "gnd_l2_plane_count:0" in result["errors"]


def test_native_audit_validator_accepts_altium_layer_name_punctuation(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "layer_stack_inventory.csv"
    rows = _contract_rows(path)
    rows[1]["layer_name"] = "Mid Layer 1"
    rows[2]["layer_name"] = "Mid Layer 2"
    _write_csv(path, ["order", "layer_name"], rows)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "PASS"
    assert result["verified_checks"]["stackup_equivalence"] == "PASS"


def test_native_audit_validator_detects_direct_symbol_pin_mismatch(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "pad_net_inventory.csv"
    rows = _contract_rows(path)
    for row in rows:
        if row["designator"] == "U2" and row["pad_name"] == "4":
            row["net_name"] = "WRONG_NET"
            break
    _write_csv(path, ["designator", "pad_name", "net_name"], rows)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("symbol_pin_net_mismatch:U2.4:")
        for item in result["errors"]
    )



def test_native_audit_validator_detects_rule_scope_mismatch(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "rule_inventory.csv"
    rows = _contract_rows(path)
    rows[0]["scope_1"] = "All"
    _write_csv(
        path,
        [
            "rule_name",
            "rule_kind",
            "unique_id",
            "scope_1",
            "scope_2",
            "drc_enabled",
        ],
        rows,
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert "rule_scope_1_mismatch:R_VIN_HIGH_CURRENT" in result["errors"]
    assert result["verified_checks"]["rules_equivalence"] == "FAIL"


def test_native_audit_validator_detects_rule_value_mismatch(tmp_path):
    _native_fixture(tmp_path)

    path = tmp_path / "rule_constraint_inventory.csv"
    rows = _contract_rows(path)
    for row in rows:
        if row["rule_name"] == "R_CAN_DIFF" and row["layer_name"] == "Top Layer":
            row["preferred_gap_raw"] = "0"
            break
    _write_csv(
        path,
        [
            "rule_name", "layer_name", "min_width_raw",
            "preferred_width_raw", "max_width_raw", "min_gap_raw",
            "preferred_gap_raw", "max_gap_raw",
        ],
        rows,
    )

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "FAIL"
    assert any(
        "R_CAN_DIFF:Top Layer:preferred_gap_raw" in item
        for item in result["errors"]
    )


def test_native_audit_validator_detects_wrong_mounting_hole(tmp_path):
    _native_fixture(tmp_path)
    path = tmp_path / "mechanical_inventory.csv"
    rows = _contract_rows(path)
    next(row for row in rows if row["id"] == "H2")["plated"] = "true"
    _write_csv(
        path,
        ["kind", "id", "x_raw", "y_raw", "width_raw", "height_raw",
         "diameter_raw", "plated", "details"],
        rows,
    )
    result = validate(system_root=SYSTEM, audit_dir=tmp_path)
    assert result["status"] == "FAIL"
    assert "mechanical_hole_plating:H2" in result["errors"]


def test_native_audit_validator_detects_wrong_pair_binding(tmp_path):
    _native_fixture(tmp_path)
    path = tmp_path / "diff_pair_inventory.csv"
    rows = _contract_rows(path)
    next(row for row in rows if row["pair_name"] == "DP_CAN")["negative_net"] = "GND"
    _write_csv(path, ["pair_name", "positive_net", "negative_net"], rows)
    result = validate(system_root=SYSTEM, audit_dir=tmp_path)
    assert "diff_pair_mismatch:DP_CAN" in result["errors"]
