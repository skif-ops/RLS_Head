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
    source_commit = "1" * 40

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
        "pad_net_inventory": (
            "equivalence/pad_net_inventory.csv",
            b"designator,pad_name,net_name\nU1,40,GNSS_PPS\n",
        ),
        "layer_stack_inventory": (
            "equivalence/layer_stack_inventory.csv",
            b"order,layer_name\n1,Top Layer\n2,Mid-Layer 1\n3,Mid-Layer 2\n4,Bottom Layer\n",
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

    native_content = {
        "schematic": b"SYNTHETIC_TEST_SCHDOC",
        "pcb": b"SYNTHETIC_TEST_PCBDOC",
        "import_log": b"SYNTHETIC_IMPORT_LOG\n",
    }
    native_paths = {
        "schematic": "native/EVT_SYS_CARRIER.SchDoc",
        "pcb": "native/EVT_SYS_CARRIER.PcbDoc",
        "import_log": "equivalence/import_log.txt",
    }
    native_hashes = {
        key: hashlib.sha256(content).hexdigest()
        for key, content in native_content.items()
    }

    package_content = json.dumps(
        {
            "schema": "ALTIUM-IMPORT-PACKAGE-001",
            "status": "READY_FOR_ALTIUM_IMPORT",
            "board_id": "EVT-SYS-CARRIER",
            "hardware_revision": "A",
            "source_commit": source_commit,
            "source_cad": "KiCad 9 retained verification baseline",
            "target_cad": "Altium Designer",
            "preserve_kicad": True,
        },
        sort_keys=True,
    ).encode()
    package_hash = hashlib.sha256(package_content).hexdigest()

    receipt_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-IMPORT-RECEIPT-001",
            "status": "PASS",
            "board_id": "EVT-SYS-CARRIER",
            "hardware_revision": "A",
            "source_commit": source_commit,
            "source_cad": "KiCad 9 retained verification baseline",
            "target_cad": "Altium Designer",
            "import_mechanism": "KiCad Importer / Import Wizard",
            "altium_version": "26.0.1",
            "importer_version": "KiCad Importer 26.0.1",
            "import_package_manifest": {
                "path": "equivalence/import_package_manifest.json",
                "sha256": package_hash,
            },
            "native_artifacts": {
                key: {
                    "path": native_paths[key],
                    "sha256": native_hashes[key],
                }
                for key in native_content
            },
        },
        sort_keys=True,
    ).encode()

    entries = {
        "project": ("EVT_SYS_CARRIER.PrjPcb", b"[Design]\nVersion=1.0\n"),
        "schematic": (
            native_paths["schematic"],
            native_content["schematic"],
        ),
        "pcb": (
            native_paths["pcb"],
            native_content["pcb"],
        ),
        "import_package_manifest": (
            "equivalence/import_package_manifest.json",
            package_content,
        ),
        "import_receipt": (
            "equivalence/import_receipt.json",
            receipt_content,
        ),
        "import_log": (
            native_paths["import_log"],
            native_content["import_log"],
        ),
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
        "bom_export": (
            "equivalence/bom_export.csv",
            b"ref,mpn\nU1,STM32H753IIT6\n",
        ),
        "netlist_export": (
            "equivalence/netlist_export.csv",
            b"net,ref,pin\n3V3,U1,23\n",
        ),
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



def test_import_receipt_native_hash_mismatch_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    receipt_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["native_artifacts"]["pcb"]["sha256"] = "0" * 64
    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "import_receipt_hash:pcb" in result["errors"]
