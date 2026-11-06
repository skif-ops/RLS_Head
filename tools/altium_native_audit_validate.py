from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-AUDIT-RESULT-001"

RULE_KIND_ALIASES = {
    "DifferentialPairRouting": "DiffPairsRouting",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def _clean(value: object) -> str:
    return str(value if value is not None else "").strip()


def _norm_scope(value: object) -> str:
    return re.sub(r"\s+", "", _clean(value)).lower()


def _norm_layer(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _clean(value).lower())


def _coord_from_mm(value: object) -> int:
    return int(
        (Decimal(_clean(value)) * Decimal("1000000") / Decimal("2.54"))
        .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def _validate_mechanical(system: Path, rows: list[dict[str, str]]) -> list[str]:
    contract = read_csv(system / "altium" / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv")
    board = next(row for row in contract if row["id"] == "OUTLINE")
    radius = next(row for row in contract if row["id"] == "CORNER_RADIUS")
    x = Decimal(board["x_mm"])
    y = Decimal(board["y_mm"])
    width = Decimal(board["width_mm"])
    height = Decimal(board["height_mm"])
    r = Decimal(radius["height_mm"])
    expected_outline = [
        _coord_from_mm(v) for v in (x, y, width, height)
    ]
    errors: list[str] = []
    outlines = [row for row in rows if row.get("kind") == "outline"]
    if len(outlines) != 1:
        errors.append("mechanical_outline_count")
    else:
        actual = [
            int(outlines[0][key])
            for key in ("x_raw", "y_raw", "width_raw", "height_raw")
        ]
        if any(abs(a - b) > 2 for a, b in zip(actual, expected_outline)):
            errors.append("mechanical_outline_dimensions")

    expected_vertices = {
        (_coord_from_mm(px), _coord_from_mm(py))
        for px, py in (
            (x + r, y), (x, y + r),
            (x, y + height - r), (x + r, y + height),
            (x + width - r, y + height),
            (x + width, y + height - r),
            (x + width, y + r), (x + width - r, y),
        )
    }
    vertices = [row for row in rows if row.get("kind") == "vertex"]
    if len(vertices) != 8:
        errors.append("mechanical_vertex_count")
    else:
        unmatched = expected_vertices.copy()
        for row in vertices:
            actual_x, actual_y = int(row["x_raw"]), int(row["y_raw"])
            match = next(
                (
                    point for point in unmatched
                    if abs(point[0] - actual_x) <= 2
                    and abs(point[1] - actual_y) <= 2
                ),
                None,
            )
            if match is not None:
                unmatched.remove(match)
        if unmatched:
            errors.append("mechanical_vertex_positions")
    arcs = [row for row in vertices if row.get("details") == "arc"]
    lines = [row for row in vertices if row.get("details") == "line"]
    if len(arcs) != 4 or len(lines) != 4 or any(
        abs(int(row.get("diameter_raw") or "0") - _coord_from_mm(r)) > 2
        for row in arcs
    ):
        errors.append("mechanical_corner_radius")

    holes = [row for row in rows if row.get("kind") == "free_hole"]
    expected_holes = [row for row in contract if row.get("kind") == "HOLE"]
    if len(holes) != len(expected_holes):
        errors.append("mechanical_hole_count")
    else:
        by_name = {row["id"]: row for row in holes}
        if len(by_name) != len(expected_holes):
            errors.append("mechanical_hole_names")
        for expected in expected_holes:
            actual = by_name.get(expected["id"])
            if actual is None:
                errors.append(f"mechanical_hole_missing:{expected['id']}")
                continue
            for field, value in (
                ("x_raw", expected["x_mm"]),
                ("y_raw", expected["y_mm"]),
                ("diameter_raw", expected["diameter_mm"]),
            ):
                if abs(int(actual[field]) - _coord_from_mm(value)) > 2:
                    errors.append(f"mechanical_hole_{field}:{expected['id']}")
            if _clean(actual.get("plated")).lower() != "false":
                errors.append(f"mechanical_hole_plating:{expected['id']}")
    return errors


def validate(
    *,
    system_root: str | Path,
    audit_dir: str | Path,
) -> dict:
    system = Path(system_root)
    audit = Path(audit_dir)

    paths = {
        "component_inventory": audit / "component_inventory.csv",
        "net_inventory": audit / "net_inventory.csv",
        "rule_inventory": audit / "rule_inventory.csv",
        "rule_constraint_inventory": audit / "rule_constraint_inventory.csv",
        "pad_net_inventory": audit / "pad_net_inventory.csv",
        "layer_stack_inventory": audit / "layer_stack_inventory.csv",
        "mechanical_inventory": audit / "mechanical_inventory.csv",
        "diff_pair_inventory": audit / "diff_pair_inventory.csv",
        "class_inventory": audit / "class_inventory.csv",
        "layer_stack_detail": audit / "layer_stack_detail.csv",
        "polygon_inventory": audit / "polygon_inventory.csv",
    }

    errors: list[str] = []
    warnings: list[str] = []

    for artifact_id, path in paths.items():
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    components = read_csv(paths["component_inventory"])
    nets = read_csv(paths["net_inventory"])
    rules = read_csv(paths["rule_inventory"])
    rule_constraints = read_csv(paths["rule_constraint_inventory"])
    pad_nets = read_csv(paths["pad_net_inventory"])
    layer_stack = read_csv(paths["layer_stack_inventory"])
    mechanical = read_csv(paths["mechanical_inventory"])
    diff_pairs = read_csv(paths["diff_pair_inventory"])
    classes = read_csv(paths["class_inventory"])
    stack_detail = read_csv(paths["layer_stack_detail"])
    polygons = read_csv(paths["polygon_inventory"])

    input_sha256 = {
        artifact_id: sha256_file(path)
        for artifact_id, path in paths.items()
    }

    component_refs = {
        _clean(row.get("designator"))
        for row in components
        if _clean(row.get("designator"))
    }

    with (
        system / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        bom_rows = list(csv.DictReader(handle))

    expected_refs = {
        _clean(row.get("ref"))
        for row in bom_rows
        if _clean(row.get("ref"))
    }

    missing_refs = sorted(expected_refs - component_refs)
    extra_refs = sorted(component_refs - expected_refs)

    if missing_refs:
        errors.append("missing_components:" + ",".join(missing_refs))
    if extra_refs:
        warnings.append("extra_components:" + ",".join(extra_refs))

    blank_patterns = sorted(
        _clean(row.get("designator"))
        for row in components
        if _clean(row.get("designator"))
        and not _clean(row.get("pattern"))
    )
    if blank_patterns:
        errors.append(
            "blank_footprint_pattern:" + ",".join(blank_patterns)
        )

    actual_nets = {
        _clean(row.get("net_name"))
        for row in nets
        if _clean(row.get("net_name"))
    }

    with (
        system / "NETLIST_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        net_rows = list(csv.DictReader(handle))

    contract_nets = {
        _clean(row.get("net_name"))
        for row in net_rows
        if _clean(row.get("net_name"))
    }
    required_nets = {
        _clean(row.get("net_name"))
        for row in net_rows
        if _clean(row.get("net_name"))
        and _clean(row.get("criticality")) in {"P0", "P1"}
    }

    missing_nets = sorted(required_nets - actual_nets)
    if missing_nets:
        errors.append("missing_p0_p1_nets:" + ",".join(missing_nets))

    actual_rules = {
        _clean(row.get("rule_name")): {
            "kind": _clean(row.get("rule_kind")),
            "scope_1": _clean(row.get("scope_1")),
            "scope_2": _clean(row.get("scope_2")),
            "enabled": _clean(row.get("drc_enabled")).lower(),
        }
        for row in rules
        if _clean(row.get("rule_name"))
    }

    with (
        system / "altium" / "ALTIUM_RULE_QUERY_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        rule_rows = list(csv.DictReader(handle))

    missing_rules: list[str] = []
    wrong_rule_kinds: list[str] = []
    for row in rule_rows:
        name = _clean(row.get("rule_name"))
        if not name:
            continue
        expected_kind = RULE_KIND_ALIASES.get(
            _clean(row.get("rule_family")),
            _clean(row.get("rule_family")),
        )
        if name not in actual_rules:
            missing_rules.append(name)
            continue

        actual_rule = actual_rules[name]
        if actual_rule["kind"] != expected_kind:
            wrong_rule_kinds.append(
                f"{name}:{expected_kind}!={actual_rule['kind']}"
            )

        if _norm_scope(actual_rule["scope_1"]) != _norm_scope(
            row.get("scope_1")
        ):
            errors.append(f"rule_scope_1_mismatch:{name}")
        if _norm_scope(actual_rule["scope_2"]) != _norm_scope(
            row.get("scope_2")
        ):
            errors.append(f"rule_scope_2_mismatch:{name}")
        if actual_rule["enabled"] not in {"true", "1", "yes"}:
            errors.append(f"rule_disabled:{name}")

    if missing_rules:
        errors.append("missing_rules:" + ",".join(sorted(missing_rules)))
    if wrong_rule_kinds:
        errors.append(
            "rule_kind_mismatch:" + ",".join(sorted(wrong_rule_kinds))
        )

    expected_layer_rows = read_csv(
        system / "altium" / "ALTIUM_LAYER_STACK_SYS_001.csv"
    )
    expected_layers = [
        _clean(row.get("altium_layer"))
        for row in sorted(
            expected_layer_rows,
            key=lambda row: int(_clean(row.get("order")) or "0"),
        )
        if _clean(row.get("altium_layer"))
    ]
    constraints_by_rule: dict[str, list[dict[str, str]]] = {}
    for row in rule_constraints:
        constraints_by_rule.setdefault(_clean(row.get("rule_name")), []).append(row)
    constraint_errors: list[str] = []
    for contract in rule_rows:
        name = _clean(contract.get("rule_name"))
        family = _clean(contract.get("rule_family"))
        if not name or name in missing_rules:
            continue
        records = constraints_by_rule.get(name, [])
        if family == "Clearance":
            if len(records) != 1 or _clean(records[0].get("layer_name")) != "All":
                constraint_errors.append(f"{name}:expected_one_global_clearance")
                continue
            values = [("min_gap_raw", "min_value", records[0])]
        else:
            by_layer = {
                _norm_layer(record.get("layer_name")): record
                for record in records
            }
            if len(records) != len(expected_layers) or set(by_layer) != {
                _norm_layer(layer) for layer in expected_layers
            }:
                constraint_errors.append(f"{name}:layer_coverage")
                continue
            values = []
            for layer in expected_layers:
                record = by_layer[_norm_layer(layer)]
                values.extend(
                    (field, contract_field, record)
                    for field, contract_field in (
                        ("min_width_raw", "min_value"),
                        ("preferred_width_raw", "preferred_value"),
                        ("max_width_raw", "max_value"),
                    )
                )
                if family == "DifferentialPairRouting":
                    values.extend(
                        (field, contract_field, record)
                        for field, contract_field in (
                            ("min_gap_raw", "gap_min_mm"),
                            ("preferred_gap_raw", "gap_preferred_mm"),
                            ("max_gap_raw", "gap_max_mm"),
                        )
                    )
        for field, contract_field, record in values:
            actual = _clean(record.get(field))
            expected = _coord_from_mm(contract.get(contract_field))
            if not actual.isdigit() or abs(int(actual) - expected) > 1:
                constraint_errors.append(
                    f"{name}:{_clean(record.get('layer_name'))}:{field}:"
                    f"{expected}!={actual or 'MISSING'}"
                )
    if constraint_errors:
        errors.append("rule_constraint_mismatch:" + ",".join(sorted(constraint_errors)))

    pad_map: dict[tuple[str, str], str] = {}
    duplicate_pads: list[str] = []
    for row in pad_nets:
        designator = _clean(row.get("designator"))
        pad_name = _clean(row.get("pad_name"))
        net_name = _clean(row.get("net_name"))
        if not designator or not pad_name:
            continue
        key = (designator, pad_name)
        previous = pad_map.get(key)
        if previous is not None and previous != net_name:
            duplicate_pads.append(
                f"{designator}.{pad_name}:{previous}|{net_name}"
            )
        pad_map[key] = net_name

    if duplicate_pads:
        errors.append(
            "conflicting_pad_records:"
            + ",".join(sorted(duplicate_pads))
        )

    with (
        system / "PINMAP_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        pinmap_rows = list(csv.DictReader(handle))

    pinmap_mismatches: list[str] = []
    pinmap_checked = 0
    for row in pinmap_rows:
        pin = _clean(row.get("physical_pin"))
        expected_net = _clean(row.get("net_name"))
        if not pin or not expected_net:
            continue
        pinmap_checked += 1
        actual_net = pad_map.get(("U1", pin), "")
        if actual_net != expected_net:
            pinmap_mismatches.append(
                f"U1.{pin}:{expected_net}!={actual_net or 'MISSING'}"
            )

    if pinmap_mismatches:
        errors.append(
            "pinmap_net_mismatch:"
            + ",".join(sorted(pinmap_mismatches))
        )

    with (
        system / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        symbol_pin_rows = list(csv.DictReader(handle))

    symbol_pin_mismatches: list[str] = []
    symbol_pin_checked = 0
    symbol_pin_semantic_deferred = 0
    for row in symbol_pin_rows:
        if _clean(row.get("policy")) != "CONNECT":
            continue
        ref = _clean(row.get("ref"))
        pin = _clean(row.get("pin_number"))
        expected_net = _clean(row.get("connection"))
        if not ref or not pin or not expected_net:
            continue
        if expected_net not in contract_nets | actual_nets:
            symbol_pin_semantic_deferred += 1
            continue
        symbol_pin_checked += 1
        actual_net = pad_map.get((ref, pin), "")
        if actual_net != expected_net:
            symbol_pin_mismatches.append(
                f"{ref}.{pin}:{expected_net}!={actual_net or 'MISSING'}"
            )

    if symbol_pin_mismatches:
        errors.append(
            "symbol_pin_net_mismatch:"
            + ",".join(sorted(symbol_pin_mismatches))
        )

    actual_layers = [
        _clean(row.get("layer_name"))
        for row in sorted(
            layer_stack,
            key=lambda row: int(_clean(row.get("order")) or "0"),
        )
        if _clean(row.get("layer_name"))
    ]

    layers_match = [
        _norm_layer(name) for name in actual_layers
    ] == [
        _norm_layer(name) for name in expected_layers
    ]
    if not layers_match:
        errors.append(
            "layer_stack_mismatch:"
            + "|".join(expected_layers)
            + "!="
            + "|".join(actual_layers)
        )

    mechanical_errors = _validate_mechanical(system, mechanical)
    errors.extend(mechanical_errors)

    expected_pairs = read_csv(system / "altium" / "ALTIUM_DIFF_PAIRS_SYS_001.csv")
    actual_pairs = {
        _clean(row.get("pair_name")): (
            _clean(row.get("positive_net")),
            _clean(row.get("negative_net")),
        ) for row in diff_pairs
    }
    pair_errors = []
    for row in expected_pairs:
        name = row["pair_name"]
        expected = (row["positive_net"], row["negative_net"])
        if actual_pairs.get(name) != expected:
            pair_errors.append(f"diff_pair_mismatch:{name}")
    if len(diff_pairs) != len(actual_pairs):
        pair_errors.append("duplicate_diff_pairs")

    required_classes: dict[tuple[str, str], set[str]] = {}
    for row in read_csv(system / "altium" / "ALTIUM_NET_CLASSES_SYS_001.csv"):
        required_classes[(row["class_id"], "Net")] = set(row["nets"].split(";"))
    for row in expected_pairs:
        required_classes.setdefault(
            (row["pair_class"], "DifferentialPair"), set()
        ).add(row["pair_name"])
    actual_classes: dict[tuple[str, str], list[str]] = {}
    for row in classes:
        key = (_clean(row.get("class_name")), _clean(row.get("member_kind")))
        actual_classes.setdefault(key, []).append(_clean(row.get("member_name")))
    class_errors = []
    for key, expected_members in required_classes.items():
        actual_members = actual_classes.get(key, [])
        if set(actual_members) != expected_members:
            class_errors.append(f"class_membership_mismatch:{key[0]}")
        elif len(actual_members) != len(expected_members):
            warnings.append(f"duplicate_class_members:{key[0]}")
    errors.extend(pair_errors + class_errors)

    expected_stack = read_csv(system / "altium" / "ALTIUM_EVT_STACKUP_SYS_002.csv")
    stack_errors = []
    if len(stack_detail) != 4:
        stack_errors.append("stack_detail_layer_count")
    else:
        for index, actual in enumerate(stack_detail):
            copper = expected_stack[index * 2]
            if _norm_layer(actual.get("layer_name")) != _norm_layer(expected_layers[index]):
                stack_errors.append(f"stack_detail_layer:{index + 1}")
            if abs(int(actual["copper_thickness_raw"]) -
                   _coord_from_mm(copper["thickness_mm"])) > 400:
                stack_errors.append(f"stack_copper_thickness:{index + 1}")
            if index < 3:
                dielectric = expected_stack[index * 2 + 1]
                if abs(int(actual["dielectric_height_raw"]) -
                       _coord_from_mm(dielectric["thickness_mm"])) > 2:
                    stack_errors.append(f"stack_dielectric_height:{index + 1}")
                actual_er = Decimal(actual["dielectric_er"].replace(",", "."))
                if abs(actual_er - Decimal(dielectric["er_nominal"])) > Decimal("0.01"):
                    stack_errors.append(f"stack_dielectric_er:{index + 1}")
    errors.extend(stack_errors)

    ground_planes = [
        row for row in polygons
        if _clean(row.get("polygon_name")) == "EVT_GND_L2_PLANE"
    ]
    ground_plane_errors: list[str] = []
    if len(ground_planes) != 1:
        ground_plane_errors.append(
            f"gnd_l2_plane_count:{len(ground_planes)}"
        )
    else:
        ground_plane = ground_planes[0]
        expected_values = {
            "layer_name": "midlayer1",
            "net_name": "gnd",
            "polygon_type": "signallayer",
            "hatch_style": "solid",
            "outline_match": "true",
            "remove_dead": "false",
            "remove_islands_by_area": "false",
            "remove_narrow_necks": "false",
        }
        for field, expected in expected_values.items():
            actual = _norm_layer(ground_plane.get(field))
            if actual != expected:
                ground_plane_errors.append(
                    f"gnd_l2_plane_{field}:{expected}!={actual or 'missing'}"
                )
        point_count = _clean(ground_plane.get("point_count"))
        outline_point_count = _clean(
            ground_plane.get("outline_point_count")
        )
        if (
            not point_count.isdigit()
            or int(point_count) < 4
            or point_count != outline_point_count
        ):
            ground_plane_errors.append(
                "gnd_l2_plane_outline_point_count"
            )
    errors.extend(ground_plane_errors)

    audit_status = "PASS" if not errors else "FAIL"
    verified_checks = {
        "native_pcb_audit": audit_status,
        "pinmap_equivalence": (
            "PASS" if not pinmap_mismatches else "FAIL"
        ),
        "stackup_equivalence": (
            "PASS" if layers_match and not stack_errors else "FAIL"
        ),
        "mechanical_equivalence": (
            "PASS" if not mechanical_errors else "FAIL"
        ),
        "pair_class_equivalence": (
            "PASS" if not pair_errors and not class_errors else "FAIL"
        ),
        "rules_equivalence": (
            "PASS"
            if not missing_rules
            and not wrong_rule_kinds
            and not constraint_errors
            and not any(
                item.startswith("rule_scope_")
                or item.startswith("rule_disabled:")
                for item in errors
            )
            else "FAIL"
        ),
    }

    return {
        "schema": SCHEMA,
        "status": audit_status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "component_count": len(component_refs),
        "expected_component_count": len(expected_refs),
        "net_count": len(actual_nets),
        "required_p0_p1_net_count": len(required_nets),
        "rule_count": len(actual_rules),
        "required_rule_count": len(rule_rows),
        "pad_record_count": len(pad_map),
        "pinmap_checked_count": pinmap_checked,
        "symbol_pin_checked_count": symbol_pin_checked,
        "symbol_pin_semantic_deferred_count": symbol_pin_semantic_deferred,
        "layer_stack_count": len(actual_layers),
        "expected_layer_stack_count": len(expected_layers),
        "mounting_hole_count": sum(
            row.get("kind") == "free_hole" for row in mechanical
        ),
        "differential_pair_count": len(actual_pairs),
        "required_class_count": len(required_classes),
        "polygon_count": len(polygons),
        "gnd_l2_plane_count": len(ground_planes),
        "input_sha256": input_sha256,
        "verified_checks": verified_checks,
        "notes": [
            (
                "PASS cross-checks native components, P0/P1 net names, "
                "rule names/families and values, MCU pin-to-net assignments, "
                "direct symbol pin contracts, four-layer copper stack, "
                "board outline, mounting holes and the solid GND polygon "
                "bound to the complete L2 board outline."
            ),
            (
                "Exact footprint equivalence, hierarchy/port semantics, "
                "connector aggregate semantics and rule priority remain "
                "controlled by dedicated evidence."
            ),
            (
                "The full ALTIUM_EQUIVALENCE_GATE still controls layout authority."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        audit_dir=args.audit_dir,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
