from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SCHEMA = "ALTIUM-RULE-SCOPE-GATE-001"

IN_NET_RE = re.compile(r"InNet\(([^)]*)\)")
IN_NET_CLASS_RE = re.compile(r"InNetClass\('([^']+)'\)")
IN_DP_CLASS_RE = re.compile(r"InDifferentialPairClass\('([^']+)'\)")
QUOTED_RE = re.compile(r"'([^']+)'")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def value_map(
    rows: list[dict[str, str]],
    *,
    key: str,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = str(row.get(key, "")).strip()
        if not name:
            continue
        if name in result:
            raise ValueError(f"duplicate {key}: {name}")
        result[name] = row
    return result


def validate(system_root: str | Path) -> dict:
    root = Path(system_root)
    altium = root / "altium"

    pair_path = altium / "ALTIUM_DIFF_PAIRS_SYS_001.csv"
    rule_path = altium / "ALTIUM_RULE_QUERY_SYS_001.csv"
    net_class_path = altium / "ALTIUM_NET_CLASSES_SYS_001.csv"
    netlist_path = root / "NETLIST_SYS_001.csv"
    impedance_path = altium / "ALTIUM_IMPEDANCE_START_SYS_001.csv"
    power_path = altium / "ALTIUM_POWER_WIDTH_SYS_001.csv"
    values_path = altium / "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    required = (
        pair_path,
        rule_path,
        net_class_path,
        netlist_path,
        impedance_path,
        power_path,
        values_path,
    )
    for path in required:
        if not path.is_file():
            errors.append(f"missing:{path.name}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    pairs = read_csv(pair_path)
    rules = read_csv(rule_path)
    net_classes = read_csv(net_class_path)
    netlist = read_csv(netlist_path)
    impedance = value_map(
        read_csv(impedance_path),
        key="model_id",
    )
    power = value_map(
        read_csv(power_path),
        key="model_id",
    )
    values = value_map(
        read_csv(values_path),
        key="rule_id",
    )

    pair_names = {
        str(row.get("pair_name", "")).strip()
        for row in pairs
    }
    expected_pairs = {
        "DP_ETH_TX",
        "DP_ETH_RX",
        "DP_CAN",
    }
    if pair_names != expected_pairs:
        errors.append(
            "pair_set:"
            + ",".join(sorted(pair_names))
        )

    pair_classes = {
        str(row.get("pair_class", "")).strip()
        for row in pairs
    }
    if pair_classes != {"DP_ETH_MDI", "DP_CAN"}:
        errors.append(
            "pair_class_set:"
            + ",".join(sorted(pair_classes))
        )

    pair_nets: set[str] = set()
    for row in pairs:
        positive = str(
            row.get("positive_net", "")
        ).strip()
        negative = str(
            row.get("negative_net", "")
        ).strip()
        if not positive or not negative:
            errors.append(
                "blank_pair_net:"
                + str(row.get("pair_name", ""))
            )
            continue
        if positive == negative:
            errors.append(
                f"same_pair_members:{positive}"
            )
        for net in (positive, negative):
            if net in pair_nets:
                errors.append(
                    f"pair_net_reused:{net}"
                )
            pair_nets.add(net)
        if str(row.get("status", "")).strip() != "LOCKED":
            errors.append(
                "pair_not_locked:"
                + str(row.get("pair_name", ""))
            )

    known_nets = {
        str(row.get("net_name", "")).strip()
        for row in netlist
        if str(row.get("net_name", "")).strip()
    }
    known_nets |= pair_nets
    known_nets |= {"GNSS_RF", "BUCK_SW"}

    net_class_ids = {
        str(row.get("class_id", "")).strip()
        for row in net_classes
        if str(row.get("class_id", "")).strip()
    }

    expected_rule_names = {
        "R_GNSS_RF_WIDTH",
        "R_ETH_MDI_DIFF",
        "R_VIN_HIGH_CURRENT",
        "R_RADAR_12V_WIDTH",
        "R_3V3_TRUNK_WIDTH",
        "R_TIMING_TO_SW_CLEARANCE",
        "R_ETH_MDI_CLEARANCE",
        "R_CAN_DIFF",
        "R_GENERAL_CLEARANCE",
        "R_GENERAL_WIDTH",
    }

    rule_names: set[str] = set()
    priorities: set[int] = set()
    orders: set[int] = set()
    allowed_families = {
        "Width",
        "Clearance",
        "DifferentialPairRouting",
    }

    def validate_query(
        query: str,
        *,
        rule_name: str,
    ) -> None:
        query = query.strip()
        if query == "All":
            return

        normalized = query
        if normalized.startswith("Not "):
            normalized = normalized[4:].strip()

        if not (
            normalized.startswith("InNet(")
            or normalized.startswith("InNetClass(")
            or normalized.startswith("InDifferentialPairClass(")
        ):
            errors.append(
                f"unsupported_query:{rule_name}:{query}"
            )
            return

        for match in IN_NET_RE.finditer(query):
            names = QUOTED_RE.findall(
                match.group(1)
            )
            if not names:
                errors.append(
                    f"empty_innet:{rule_name}"
                )
            for name in names:
                if name not in known_nets:
                    errors.append(
                        f"unknown_net:{rule_name}:{name}"
                    )

        for name in IN_NET_CLASS_RE.findall(query):
            if name not in net_class_ids:
                errors.append(
                    f"unknown_net_class:{rule_name}:{name}"
                )

        for name in IN_DP_CLASS_RE.findall(query):
            if name not in pair_classes:
                errors.append(
                    f"unknown_diff_pair_class:{rule_name}:{name}"
                )

    for row in rules:
        name = str(row.get("rule_name", "")).strip()
        if not name:
            errors.append("blank_rule_name")
            continue
        if name in rule_names:
            errors.append(f"duplicate_rule_name:{name}")
        rule_names.add(name)

        family = str(row.get("rule_family", "")).strip()
        if family not in allowed_families:
            errors.append(
                f"unsupported_rule_family:{name}:{family}"
            )

        try:
            priority = int(row.get("priority", ""))
            order = int(row.get("order", ""))
        except ValueError:
            errors.append(
                f"invalid_rule_order_priority:{name}"
            )
            continue

        if priority in priorities:
            errors.append(
                f"duplicate_priority:{priority}"
            )
        priorities.add(priority)

        if order in orders:
            errors.append(
                f"duplicate_order:{order}"
            )
        orders.add(order)

        validate_query(
            str(row.get("scope_1", "")),
            rule_name=name,
        )
        validate_query(
            str(row.get("scope_2", "")),
            rule_name=name,
        )

        minimum = float(row["min_value"])
        preferred = float(row["preferred_value"])
        maximum = float(row["max_value"])
        if not (
            minimum <= preferred <= maximum
        ):
            errors.append(
                f"invalid_rule_range:{name}"
            )

        if family == "DifferentialPairRouting":
            gap_min = str(
                row.get("gap_min_mm", "")
            ).strip()
            gap_preferred = str(
                row.get("gap_preferred_mm", "")
            ).strip()
            gap_max = str(
                row.get("gap_max_mm", "")
            ).strip()
            if not (
                gap_min
                and gap_preferred
                and gap_max
            ):
                errors.append(
                    f"missing_diff_gap:{name}"
                )
            else:
                gaps = (
                    float(gap_min),
                    float(gap_preferred),
                    float(gap_max),
                )
                if not (
                    gaps[0]
                    <= gaps[1]
                    <= gaps[2]
                ):
                    errors.append(
                        f"invalid_gap_range:{name}"
                    )

    if rule_names != expected_rule_names:
        errors.append(
            "rule_set:"
            + ",".join(
                sorted(
                    expected_rule_names
                    - rule_names
                )
            )
        )

    by_name = {
        row["rule_name"]: row
        for row in rules
        if row.get("rule_name")
    }

    def check_float(
        rule_name: str,
        field: str,
        expected: float,
        tolerance: float = 1e-9,
    ) -> None:
        row = by_name.get(rule_name)
        if row is None:
            return
        actual = float(row[field])
        if abs(actual - expected) > tolerance:
            errors.append(
                f"value_mismatch:{rule_name}:{field}:"
                f"{actual}!={expected}"
            )

    check_float(
        "R_GNSS_RF_WIDTH",
        "preferred_value",
        float(impedance["IMP-001"]["trace_width_mm"]),
    )
    check_float(
        "R_ETH_MDI_DIFF",
        "preferred_value",
        float(impedance["IMP-002"]["trace_width_mm"]),
    )
    check_float(
        "R_ETH_MDI_DIFF",
        "gap_preferred_mm",
        float(impedance["IMP-002"]["pair_gap_mm"]),
    )
    check_float(
        "R_VIN_HIGH_CURRENT",
        "preferred_value",
        float(power["PWR-001"]["selected_width_mm"]),
    )
    check_float(
        "R_RADAR_12V_WIDTH",
        "preferred_value",
        float(power["PWR-003"]["selected_width_mm"]),
    )
    check_float(
        "R_3V3_TRUNK_WIDTH",
        "preferred_value",
        float(power["PWR-004"]["selected_width_mm"]),
    )
    check_float(
        "R_GENERAL_CLEARANCE",
        "preferred_value",
        float(values["RV-003"]["value"]),
    )
    check_float(
        "R_TIMING_TO_SW_CLEARANCE",
        "preferred_value",
        float(values["RV-015"]["value"]),
    )

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "rule_count": len(rule_names),
        "differential_pair_count": len(pair_names),
        "differential_pair_class_count": len(pair_classes),
        "net_class_count": len(net_class_ids),
        "query_language": "Altium PCB Query Language",
        "notes": [
            (
                "Queries use the Altium membership functions InNet, "
                "InNetClass and InDifferentialPairClass."
            ),
            (
                "This contract defines rules to instantiate in native "
                "Altium after import/equivalence; it is not a substitute "
                "for an Altium DRC report."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("system_carrier_root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(args.system_carrier_root)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
