import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_manifest import build_manifest


def test_manifest_builder_hashes_artifacts_and_marks_native_audit(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    data_path = evidence / "data.bin"
    data_path.write_bytes(b"DATA")

    bom_result_path = evidence / "bom_validation_result.json"
    bom_result_path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NATIVE-BOM-RESULT-001",
                "status": "PASS",
                "verified_checks": {
                    "bom_designator_mpn_equivalence": "PASS",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    footprint_result_path = evidence / "footprint_report.json"
    footprint_result_path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NATIVE-FOOTPRINT-RESULT-001",
                "status": "PASS",
                "verified_checks": {
                    "footprint_equivalence": "PASS",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    connector_result_path = evidence / "connector_validation_result.json"
    connector_result_path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NATIVE-CONNECTOR-RESULT-001",
                "status": "PASS",
                "verified_checks": {
                    "connector_pinout_equivalence": "PASS",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    audit_path = evidence / "native_audit_result.json"
    audit_path.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NATIVE-AUDIT-RESULT-001",
                "status": "PASS",
                "verified_checks": {
                    "native_pcb_audit": "PASS",
                    "pinmap_equivalence": "PASS",
                    "rules_equivalence": "PASS",
                    "stackup_equivalence": "PASS",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    template = tmp_path / "template.json"
    template.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-EQUIVALENCE-MANIFEST-001",
                "artifacts": [
                    {
                        "id": "data",
                        "path": "evidence/data.bin",
                        "sha256": "<SHA256>",
                    },
                    {
                        "id": "native_audit_result",
                        "path": "evidence/native_audit_result.json",
                        "sha256": "<SHA256>",
                    },
                    {
                        "id": "bom_validation_result",
                        "path": "evidence/bom_validation_result.json",
                        "sha256": "<SHA256>",
                    },
                    {
                        "id": "footprint_report",
                        "path": "evidence/footprint_report.json",
                        "sha256": "<SHA256>",
                    },
                    {
                        "id": "connector_validation_result",
                        "path": "evidence/connector_validation_result.json",
                        "sha256": "<SHA256>",
                    },
                ],
                "checks": {
                    "bom_designator_mpn_equivalence": "PENDING",
                    "footprint_equivalence": "PENDING",
                    "connector_pinout_equivalence": "PENDING",
                    "native_pcb_audit": "PENDING",
                    "pinmap_equivalence": "PENDING",
                    "rules_equivalence": "PENDING",
                    "stackup_equivalence": "PENDING",
                    "netlist_equivalence": "PENDING",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = build_manifest(
        template_path=template,
        repository_root=tmp_path,
    )

    assert result["status"] == "READY"
    assert result["errors"] == []
    manifest = result["manifest"]
    by_id = {item["id"]: item for item in manifest["artifacts"]}
    assert by_id["data"]["sha256"] == hashlib.sha256(b"DATA").hexdigest()
    assert len(by_id["native_audit_result"]["sha256"]) == 64
    assert manifest["checks"]["bom_designator_mpn_equivalence"] == "PASS"
    assert manifest["checks"]["footprint_equivalence"] == "PASS"
    assert manifest["checks"]["connector_pinout_equivalence"] == "PASS"
    assert manifest["checks"]["native_pcb_audit"] == "PASS"
    assert manifest["checks"]["pinmap_equivalence"] == "PASS"
    assert manifest["checks"]["rules_equivalence"] == "PASS"
    assert manifest["checks"]["stackup_equivalence"] == "PASS"
    assert manifest["checks"]["netlist_equivalence"] == "PENDING"


def test_manifest_builder_refuses_missing_artifact(tmp_path):
    template = tmp_path / "template.json"
    template.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-EQUIVALENCE-MANIFEST-001",
                "artifacts": [
                    {
                        "id": "missing",
                        "path": "missing.bin",
                        "sha256": "<SHA256>",
                    }
                ],
                "checks": {"native_pcb_audit": "PENDING"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = build_manifest(
        template_path=template,
        repository_root=tmp_path,
    )

    assert result["status"] == "INCOMPLETE"
    assert "missing_artifact:missing" in result["errors"]
