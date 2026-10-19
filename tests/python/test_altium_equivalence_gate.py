import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_gate import validate_manifest
from tools.altium_native_file_preflight import CFB_MAGIC


def _write(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _cfb_stub() -> bytes:
    data = bytearray(512)
    data[:8] = CFB_MAGIC
    data[24:26] = (0x003E).to_bytes(2, "little")
    data[26:28] = (3).to_bytes(2, "little")
    data[28:30] = (0xFFFE).to_bytes(2, "little")
    data[30:32] = (9).to_bytes(2, "little")
    data[32:34] = (6).to_bytes(2, "little")
    return bytes(data)


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
            b"rule_name,rule_kind,unique_id,scope_1,scope_2,drc_enabled\nR_GENERAL_WIDTH,Width,TEST,All,All,true\n",
        ),
        "pad_net_inventory": (
            "equivalence/pad_net_inventory.csv",
            b"designator,pad_name,net_name\nU1,40,GNSS_PPS\nJ1,1,VIN_RAW\n",
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

    bom_contract_content = (
        b"ref,qty,manufacturer,value_or_mpn,description,procurement_class,"
        b"footprint_id,population,status\n"
        b"U1,1,STMicroelectronics,STM32H753IIT6,System MCU,LOCKED_MPN,"
        b"TEST,POPULATE,LOCKED\n"
    )
    bom_contract_path = (
        tmp_path / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    _write(bom_contract_path, bom_contract_content)
    bom_contract_hash = hashlib.sha256(bom_contract_content).hexdigest()

    footprint_contract_content = (
        b"ref,value_or_mpn,footprint_id,package,source,status,population,notes\n"
        b"U1,STM32H753IIT6,TEST,LQFP176,TEST,LOCKED,POPULATE,\n"
    )
    footprint_contract_path = (
        tmp_path / "hardware/system_carrier/FOOTPRINT_ASSIGNMENT_SYS_002.csv"
    )
    _write(footprint_contract_path, footprint_contract_content)
    footprint_contract_hash = hashlib.sha256(
        footprint_contract_content
    ).hexdigest()

    connector_contract_content = (
        b"connector,pin,signal,direction,voltage_or_standard,criticality,notes\n"
        b"J1_POWER,1,12V_IN,IN,12V nominal,P0,\n"
    )
    connector_contract_path = (
        tmp_path / "hardware/system_carrier/CONNECTOR_PINOUT_SYS_001.csv"
    )
    _write(connector_contract_path, connector_contract_content)
    connector_contract_hash = hashlib.sha256(
        connector_contract_content
    ).hexdigest()

    connector_map_content = (
        b"connector,logical_pin,logical_signal,physical_ref,physical_pad,"
        b"native_net,policy,criticality,notes\n"
        b"J1_POWER,1,12V_IN,J1,1,VIN_RAW,CONNECT,P0,\n"
    )
    connector_map_path = (
        tmp_path
        / "hardware/system_carrier/CONNECTOR_NATIVE_PINMAP_SYS_001.csv"
    )
    _write(connector_map_path, connector_map_content)
    connector_map_hash = hashlib.sha256(
        connector_map_content
    ).hexdigest()

    hierarchy_contract_content = (
        b"sheet,net_name,pin_type,anchor_ref,anchor_pin,criticality,notes\n"
        b"MCU_CORE,GNSS_PPS,input,U1,40,P0,\n"
    )
    hierarchy_contract_path = (
        tmp_path / "hardware/system_carrier/HIERARCHY_INTERFACE_SYS_001.csv"
    )
    _write(hierarchy_contract_path, hierarchy_contract_content)
    hierarchy_contract_hash = hashlib.sha256(
        hierarchy_contract_content
    ).hexdigest()

    native_content = {
        "schematic": _cfb_stub(),
        "pcb": _cfb_stub(),
        "import_log": b"SYNTHETIC_IMPORT_LOG\n",
    }
    native_paths = {
        "schematic": (
            "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"
        ),
        "pcb": (
            "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"
        ),
        "import_log": (
            "hardware/system_carrier/altium/equivalence/import_log.txt"
        ),
    }
    native_hashes = {
        key: hashlib.sha256(content).hexdigest()
        for key, content in native_content.items()
    }

    native_file_preflight_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-FILE-PREFLIGHT-001",
            "status": "PASS",
            "errors": [],
            "artifacts": {
                "schematic": {
                    "path": native_paths["schematic"],
                    "status": "PASS",
                    "errors": [],
                    "size": len(native_content["schematic"]),
                    "sha256": native_hashes["schematic"],
                    "cfb_major_version": 3,
                    "sector_shift": 9,
                    "sector_size": 512,
                },
                "pcb": {
                    "path": native_paths["pcb"],
                    "status": "PASS",
                    "errors": [],
                    "size": len(native_content["pcb"]),
                    "sha256": native_hashes["pcb"],
                    "cfb_major_version": 3,
                    "sector_shift": 9,
                    "sector_size": 512,
                },
            },
        },
        sort_keys=True,
    ).encode()

    baseline_content = (
        b"designator,pin,net_name\n"
        b"U1,40,GNSS_PPS\n"
        b"J1,1,VIN_RAW\n"
    )
    baseline_hash = hashlib.sha256(baseline_content).hexdigest()

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
            "files": [
                {
                    "path": (
                        "build-cad/altium_import/evidence/"
                        "kicad_netlist_baseline.csv"
                    ),
                    "sha256": baseline_hash,
                }
            ],
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
            "snapshot_role": "POST_IMPORT_NATIVE_SNAPSHOT",
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

    bom_export_content = b"designator,mpn\nU1,STM32H753IIT6\n"
    bom_export_hash = hashlib.sha256(bom_export_content).hexdigest()
    bom_validation_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-BOM-RESULT-001",
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "input_sha256": {
                "bom_export": bom_export_hash,
                "bom_contract": bom_contract_hash,
            },
            "verified_checks": {
                "bom_designator_mpn_equivalence": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    footprint_validation_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-FOOTPRINT-RESULT-001",
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "input_sha256": {
                "component_inventory": raw_hashes["component_inventory"],
                "footprint_contract": footprint_contract_hash,
            },
            "verified_checks": {
                "footprint_equivalence": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    connector_validation_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-CONNECTOR-RESULT-001",
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "input_sha256": {
                "pad_net_inventory": raw_hashes["pad_net_inventory"],
                "connector_pinout_contract": connector_contract_hash,
                "connector_native_map": connector_map_hash,
            },
            "verified_checks": {
                "connector_pinout_equivalence": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    netlist_validation_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-NETLIST-RESULT-001",
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "input_sha256": {
                "kicad_netlist_baseline": baseline_hash,
                "pad_net_inventory": raw_hashes["pad_net_inventory"],
            },
            "verified_checks": {
                "netlist_equivalence": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    hierarchy_export_content = (
        b"sheet,net_name,pin_type\n"
        b"MCU_CORE,GNSS_PPS,input\n"
    )
    hierarchy_export_hash = hashlib.sha256(
        hierarchy_export_content
    ).hexdigest()
    hierarchy_validation_content = json.dumps(
        {
            "schema": "ALTIUM-NATIVE-HIERARCHY-RESULT-001",
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "input_sha256": {
                "hierarchy_contract": hierarchy_contract_hash,
                "hierarchy_export": hierarchy_export_hash,
                "pad_net_inventory": raw_hashes["pad_net_inventory"],
            },
            "verified_checks": {
                "hierarchy_equivalence": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    no_mmwave_review_content = json.dumps(
        {
            "schema": "ALTIUM-NO-MMWAVE-REVIEW-001",
            "status": "PASS",
            "reviewer": "Synthetic CI",
            "no_76_81ghz_components": True,
            "no_76_81ghz_nets": True,
            "no_76_81ghz_routing": True,
            "no_76_81ghz_antenna": True,
        },
        sort_keys=True,
    ).encode()
    no_mmwave_review_hash = hashlib.sha256(
        no_mmwave_review_content
    ).hexdigest()
    project_content = b"[Design]\nVersion=1.0\n"
    project_hash = hashlib.sha256(project_content).hexdigest()
    compile_raw_content = b"Altium compile: 0 errors, 0 warnings\n"
    compile_raw_hash = hashlib.sha256(
        compile_raw_content
    ).hexdigest()
    compile_report_content = json.dumps(
        {
            "schema": "ALTIUM-COMPILE-REPORT-001",
            "status": "PASS",
            "errors": 0,
            "warnings": 0,
            "source_report": (
                "hardware/system_carrier/altium/equivalence/"
                "compile_report_raw.txt"
            ),
            "source_report_sha256": compile_raw_hash,
            "source_project": (
                "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb"
            ),
            "source_project_sha256": project_hash,
            "source_schematic": native_paths["schematic"],
            "source_schematic_sha256": native_hashes["schematic"],
            "layout_authority": "NOT_AUTHORIZED",
            "production_authority": "NOT_AUTHORIZED",
        },
        sort_keys=True,
    ).encode()

    no_mmwave_result_content = json.dumps(
        {
            "schema": "ALTIUM-NO-MMWAVE-REVIEW-RESULT-001",
            "status": "PASS",
            "errors": [],
            "reason_codes": [],
            "reviewer": "Synthetic CI",
            "input_sha256": {
                "review": no_mmwave_review_hash,
                "pcb": native_hashes["pcb"],
                "component_inventory": raw_hashes["component_inventory"],
                "net_inventory": raw_hashes["net_inventory"],
            },
            "verified_checks": {
                "no_76_81GHz_rf_on_system_carrier": "PASS",
            },
        },
        sort_keys=True,
    ).encode()

    entries = {
        "project": (
            "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb",
            project_content,
        ),
        "schematic": (
            native_paths["schematic"],
            native_content["schematic"],
        ),
        "pcb": (
            native_paths["pcb"],
            native_content["pcb"],
        ),
        "native_file_preflight": (
            "equivalence/native_file_preflight.json",
            native_file_preflight_content,
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
        "compile_report_raw": (
            "hardware/system_carrier/altium/equivalence/compile_report_raw.txt",
            compile_raw_content,
        ),
        "compile_report": (
            "hardware/system_carrier/altium/equivalence/compile_report.json",
            compile_report_content,
        ),
        "bom_export": (
            "equivalence/bom_export.csv",
            bom_export_content,
        ),
        "bom_validation_result": (
            "equivalence/bom_validation_result.json",
            bom_validation_content,
        ),
        "connector_validation_result": (
            "equivalence/connector_validation_result.json",
            connector_validation_content,
        ),
        "kicad_netlist_baseline": (
            "equivalence/kicad_netlist_baseline.csv",
            baseline_content,
        ),
        "netlist_validation_result": (
            "equivalence/netlist_validation_result.json",
            netlist_validation_content,
        ),
        "netlist_export": (
            "equivalence/netlist_export.csv",
            b"net,ref,pin\n3V3,U1,23\n",
        ),
        "footprint_report": (
            "equivalence/footprint_report.json",
            footprint_validation_content,
        ),
        "hierarchy_export": (
            "equivalence/hierarchy_export.csv",
            hierarchy_export_content,
        ),
        "hierarchy_validation_result": (
            "equivalence/hierarchy_validation_result.json",
            hierarchy_validation_content,
        ),
        "no_mmwave_review": (
            "equivalence/no_mmwave_review.json",
            no_mmwave_review_content,
        ),
        "no_mmwave_review_result": (
            "equivalence/no_mmwave_review_result.json",
            no_mmwave_result_content,
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
    assert result["errors"] == []
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



def test_import_receipt_native_snapshot_may_differ_from_prerouting_files(
    tmp_path,
):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    receipt_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())

    # These are import-time snapshots. The later pre-routing SchDoc/PcbDoc
    # may legitimately differ after applying approved native preparation.
    receipt["native_artifacts"]["schematic"]["sha256"] = "1" * 64
    receipt["native_artifacts"]["pcb"]["sha256"] = "2" * 64

    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "TEST_READY"
    assert "import_receipt_hash:schematic" not in result["errors"]
    assert "import_receipt_hash:pcb" not in result["errors"]


def test_import_receipt_rejects_malformed_native_snapshot_hash(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    receipt_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["native_artifacts"]["pcb"]["sha256"] = "not-a-sha256"

    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "import_receipt_snapshot_hash:pcb" in result["errors"]


def test_import_receipt_import_log_must_remain_exact(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    receipt_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["native_artifacts"]["import_log"]["sha256"] = "0" * 64

    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "import_receipt_hash:import_log" in result["errors"]


def test_import_receipt_requires_snapshot_role(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    receipt_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())
    receipt.pop("snapshot_role")

    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "import_receipt_snapshot_role" in result["errors"]


def test_bom_validation_input_hash_mismatch_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "bom_validation_result"
    )
    path = tmp_path / item["path"]
    result = json.loads(path.read_text())
    result["input_sha256"]["bom_export"] = "0" * 64
    content = json.dumps(result, sort_keys=True).encode()
    path.write_bytes(content)
    item["sha256"] = hashlib.sha256(content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    checked = validate_manifest(manifest, tmp_path)

    assert checked["status"] == "INVALID"
    assert "bom_validation_hash:bom_export" in checked["errors"]


def test_footprint_validation_input_hash_mismatch_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "footprint_report"
    )
    path = tmp_path / item["path"]
    result = json.loads(path.read_text())
    result["input_sha256"]["component_inventory"] = "0" * 64
    content = json.dumps(result, sort_keys=True).encode()
    path.write_bytes(content)
    item["sha256"] = hashlib.sha256(content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    checked = validate_manifest(manifest, tmp_path)

    assert checked["status"] == "INVALID"
    assert (
        "footprint_report_hash:component_inventory"
        in checked["errors"]
    )



def test_connector_validation_input_hash_mismatch_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "connector_validation_result"
    )
    path = tmp_path / item["path"]
    result = json.loads(path.read_text())
    result["input_sha256"]["pad_net_inventory"] = "0" * 64
    content = json.dumps(result, sort_keys=True).encode()
    path.write_bytes(content)
    item["sha256"] = hashlib.sha256(content).hexdigest()
    manifest.write_text(json.dumps(data, indent=2) + "\n")

    checked = validate_manifest(manifest, tmp_path)

    assert checked["status"] == "INVALID"
    assert (
        "connector_validation_hash:pad_net_inventory"
        in checked["errors"]
    )



def test_netlist_baseline_must_be_bound_to_import_package(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    package_item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "import_package_manifest"
    )
    package_path = tmp_path / package_item["path"]
    package = json.loads(package_path.read_text())
    package["files"][0]["sha256"] = "0" * 64
    package_content = json.dumps(package, sort_keys=True).encode()
    package_path.write_bytes(package_content)
    package_item["sha256"] = hashlib.sha256(package_content).hexdigest()

    receipt_item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "import_receipt"
    )
    receipt_path = tmp_path / receipt_item["path"]
    receipt = json.loads(receipt_path.read_text())
    receipt["import_package_manifest"]["sha256"] = package_item["sha256"]
    receipt_content = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_content)
    receipt_item["sha256"] = hashlib.sha256(receipt_content).hexdigest()

    manifest.write_text(json.dumps(data, indent=2) + "\n")

    checked = validate_manifest(manifest, tmp_path)

    assert checked["status"] == "INVALID"
    assert (
        "netlist_baseline_not_bound_to_import_package"
        in checked["errors"]
    )



def test_changed_raw_compile_report_invalidates_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    raw_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "compile_report_raw"
    )
    raw_path = tmp_path / raw_item["path"]
    raw_path.write_bytes(b"CHANGED_RAW_COMPILE_REPORT")
    raw_item["sha256"] = hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "compile_evidence:source_report_hash" in result["errors"]



def test_noncanonical_native_pcb_path_invalidates_equivalence_gate(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    pcb_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "pcb"
    )
    canonical = tmp_path / pcb_item["path"]
    alternate = tmp_path / "hardware/system_carrier/altium/native/ALT.PcbDoc"
    alternate.parent.mkdir(parents=True, exist_ok=True)
    alternate.write_bytes(canonical.read_bytes())

    pcb_item["path"] = (
        "hardware/system_carrier/altium/native/ALT.PcbDoc"
    )
    pcb_item["sha256"] = hashlib.sha256(
        alternate.read_bytes()
    ).hexdigest()
    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "canonical_path:pcb" in result["errors"]



def test_final_native_preflight_must_match_prerouting_pcb(tmp_path):
    manifest = _manifest(tmp_path)
    data = json.loads(manifest.read_text())

    pcb_item = next(
        item
        for item in data["artifacts"]
        if item["id"] == "pcb"
    )
    pcb_path = tmp_path / pcb_item["path"]
    pcb_path.write_bytes(_cfb_stub() + b"PRE_ROUTING_CHANGED")
    pcb_item["sha256"] = hashlib.sha256(
        pcb_path.read_bytes()
    ).hexdigest()

    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert "native_file_preflight_hash:pcb" in result["errors"]
