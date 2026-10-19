import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_gate import validate_manifest


def _write(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _manifest(tmp_path: Path) -> Path:
    artifacts = []

    raw_audit_entries = {
        "component_inventory": (
            "equivalence/component_inventory.csv",
            b"designator,pattern,x_mil,y_mil\nU1,TEST,0,0\n",
        ),
        "net_inventory": (
            "equivalence/net_inventory.csv",
            b"net_name\n3V3\n",
        ),
        "rule_inventory": (
            "equivalence/rule_inventory.csv",
            b"rule_name,rule_kind,unique_id\nR_GENERAL_WIDTH,Width,TEST\n",
        ),
    }
    raw_hashes = {}
    for artifact_id, (relative, content) in raw_audit_entries.items():
        digest = _write(tmp_path / relative, content)
        raw_hashes[artifact_id] = digest
        artifacts.append(
            {
                "id": artifact_id,
                "path": relative,
                "sha256": digest,
            }
        )

    entries = {
        "project": ("EVT_SYS_CARRIER.PrjPcb", b"[Design]\nVersion=1.0\n"),
        "schematic": ("native/EVT_SYS_CARRIER.SchDoc", b"SYNTHETIC_TEST_SCHDOC"),
        "pcb": ("native/EVT_SYS_CARRIER.PcbDoc", b"SYNTHETIC_TEST_PCBDOC"),
        "import_log": ("equivalence/import_log.txt", b"SYNTHETIC_IMPORT_LOG\n"),
        "compile_report": (
            "equivalence/compile_report.json",
            json.dumps(
                {
                    "schema": "ALTIUM-COMPILE-REPORT-001",
                    "errors": 0,
                    "warnings": 0,
                },
                sort_keys=True,
            ).encode(),
        ),
        "bom_export": ("equivalence/bom_export.csv", b"ref,mpn\nU1,STM32H753IIT6\n"),
        "netlist_export": ("equivalence/netlist_export.csv", b"net,ref,pin\n3V3,U1,23\n"),
        "footprint_report": (
            "equivalence/footprint_report.json",
            b'{"status":"PASS"}',
        ),
        "native_audit_result": (
            "equivalence/native_audit_result.json",
            json.dumps(
                {
                    "schema": "ALTIUM-NATIVE-AUDIT-RESULT-001",
                    "status": "PASS",
                    "errors": [],
                    "warnings": [],
                    "input_sha256": raw_hashes,
                },
                sort_keys=True,
            ).encode(),
        ),
    }

    for artifact_id, (relative, content) in entries.items():
        digest = _write(tmp_path / relative, content)
        artifacts.append(
            {
                "id": artifact_id,
                "path": relative,
                "sha256": digest,
            }
        )

    checks = {
        "bom_designator_mpn_equivalence": "PASS",
        "pinmap_equivalence": "PASS",
        "connector_pinout_equivalence": "PASS",
        "netlist_equivalence": "PASS",
        "footprint_equivalence": "PASS",
        "hierarchy_equivalence": "PASS",
        "rules_equivalence": "PASS",
        "stackup_equivalence": "PASS",
        "no_76_81GHz_rf_on_system_carrier": "PASS",
        "native_pcb_audit": "PASS",
    }

    manifest = {
        "schema": "ALTIUM-EQUIVALENCE-MANIFEST-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "primary_cad": "Altium Designer",
        "synthetic_fixture": True,
        "evidence_level": "SOFTWARE_CI",
        "review_a_status": "PASS",
        "preserve_kicad": True,
        "artifacts": artifacts,
        "checks": checks,
    }

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_synthetic_altium_equivalence_fixture_is_test_ready(tmp_path):
    manifest = _manifest(tmp_path)
    result = validate_manifest(
        manifest,
        tmp_path,
    )

    assert result["schema"] == "ALTIUM-EQUIVALENCE-RESULT-001"
    assert result["status"] == "TEST_READY"
    assert result["synthetic_fixture"] is True
    assert result["errors"] == []
    assert result["reason_codes"] == []
    assert result["compile"]["errors"] == 0
    assert result["compile"]["warnings"] == 0
    assert result["native_audit"]["status"] == "PASS"
    assert all(
        value == "PASS"
        for value in result["checks"].values()
    )
    assert result["layout_authority"] == "NOT_AUTHORIZED"
    assert result["production_authority"] == "NOT_AUTHORIZED"


def test_failed_equivalence_check_blocks_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())
    data["checks"]["netlist_equivalence"] = "FAIL"
    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(
        manifest,
        tmp_path,
    )

    assert result["status"] == "FAIL"
    assert (
        "CHECK_NETLIST_EQUIVALENCE"
        in result["reason_codes"]
    )
    assert result["layout_authority"] == "NOT_AUTHORIZED"


def test_failed_native_audit_blocks_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    audit_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "native_audit_result"
    )
    audit_path = tmp_path / audit_item["path"]
    audit = json.loads(audit_path.read_text())
    audit["status"] = "FAIL"
    audit["errors"] = ["missing_rules:R_GENERAL_WIDTH"]
    audit_content = json.dumps(
        audit,
        sort_keys=True,
    ).encode()
    audit_path.write_bytes(audit_content)
    audit_item["sha256"] = hashlib.sha256(audit_content).hexdigest()

    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(
        manifest,
        tmp_path,
    )

    assert result["status"] == "FAIL"
    assert "NATIVE_AUDIT" in result["reason_codes"]
    assert result["layout_authority"] == "NOT_AUTHORIZED"


def test_native_audit_input_hash_mismatch_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    audit_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "native_audit_result"
    )
    audit_path = tmp_path / audit_item["path"]
    audit = json.loads(audit_path.read_text())
    audit["input_sha256"]["rule_inventory"] = "0" * 64
    audit_content = json.dumps(audit, sort_keys=True).encode()
    audit_path.write_bytes(audit_content)
    audit_item["sha256"] = hashlib.sha256(audit_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "native_audit_input_hash:rule_inventory" in result["errors"]
