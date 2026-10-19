import csv
from pathlib import Path

from tools.altium_native_audit_validate import validate


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


def test_native_audit_validator_passes_complete_fixture(tmp_path):
    _native_fixture(tmp_path)

    result = validate(system_root=SYSTEM, audit_dir=tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["component_count"] == result["expected_component_count"]
    assert result["required_rule_count"] == 10
    assert result["pinmap_checked_count"] > 0
    assert result["symbol_pin_checked_count"] > 0
    assert result["layer_stack_count"] == 4
    assert result["verified_checks"] == {
        "native_pcb_audit": "PASS",
        "pinmap_equivalence": "PASS",
        "rules_equivalence": "PASS",
        "stackup_equivalence": "PASS",
    }
    assert set(result["input_sha256"]) == {
        "component_inventory",
        "net_inventory",
        "rule_inventory",
        "pad_net_inventory",
        "layer_stack_inventory",
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
    assert "rule_scope_1_mismatch:R_GNSS_RF_WIDTH" in result["errors"]
    assert result["verified_checks"]["rules_equivalence"] == "FAIL"
