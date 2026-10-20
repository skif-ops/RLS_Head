import json
from pathlib import Path

from tools.altium_script_api_compatibility import validate


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = (
    ROOT
    / "hardware/system_carrier/altium/"
    "ALTIUM_SCRIPT_API_COMPAT_SYS_001.json"
)


def test_altium_script_api_contract_passes_repository_scripts():
    result = validate(
        contract_path=CONTRACT,
        repository_root=ROOT,
    )

    assert result["schema"] == "ALTIUM-SCRIPT-API-COMPAT-RESULT-001"
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["documented_symbol_count"] > 0
    assert result["runtime_verify_symbol_count"] > 0
    assert result["runtime_validation_required"] is True
    assert set(result["scripts"]) == {
        "pcb_native_audit",
        "schematic_hierarchy_audit",
    }
    assert all(
        item["status"] == "PASS"
        for item in result["scripts"].values()
    )


def test_altium_script_api_contract_declares_official_references():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    refs = data["references"]

    assert refs
    assert all(
        value.startswith("https://www.altium.com/")
        for value in refs.values()
    )
    assert data["runtime_gate"]["status"] == (
        "REQUIRED_IN_ALTIUM_DESIGNER"
    )


def test_altium_script_api_validator_rejects_mutation_token(tmp_path):
    script = tmp_path / "audit.pas"
    script.write_text(
        "Procedure ExportNativeAudit; Begin "
        "PCBServer.PreProcess; End;",
        encoding="utf-8",
    )
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-SCRIPT-API-COMPAT-001",
                "board_id": "EVT-SYS-CARRIER",
                "runtime_validation_required": True,
                "scripts": [
                    {
                        "id": "test",
                        "path": "audit.pas",
                        "run_procedure": "ExportNativeAudit",
                        "required_symbols": [
                            {
                                "symbol": "ExportNativeAudit",
                                "status": "DOCUMENTED",
                                "access": "READ",
                            }
                        ],
                        "forbidden_tokens": [
                            "PCBServer.PreProcess"
                        ],
                        "expected_outputs": ["ExportNativeAudit"],
                    }
                ],
                "runtime_gate": {
                    "status": "REQUIRED_IN_ALTIUM_DESIGNER"
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate(
        contract_path=contract,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert any(
        "forbidden_token:PCBServer.PreProcess" in item
        for item in result["errors"]
    )
