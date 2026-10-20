from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-SCRIPT-RUNTIME-RESULT-001"
RECEIPT_SCHEMA = "ALTIUM-SCRIPT-RUNTIME-RECEIPT-001"

CANONICAL = {
    "schematic": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc",
    "pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
    "pcb_audit_script": (
        "hardware/system_carrier/altium/scripts/"
        "EVT_SYS_CARRIER_Audit.pas"
    ),
    "hierarchy_audit_script": (
        "hardware/system_carrier/altium/scripts/"
        "EVT_SYS_CARRIER_Hierarchy_Audit.pas"
    ),
    "api_contract": (
        "hardware/system_carrier/altium/"
        "ALTIUM_SCRIPT_API_COMPAT_SYS_001.json"
    ),
}

OUTPUTS = {
    "component_inventory": (
        "hardware/system_carrier/altium/equivalence/"
        "component_inventory.csv"
    ),
    "net_inventory": (
        "hardware/system_carrier/altium/equivalence/"
        "net_inventory.csv"
    ),
    "rule_inventory": (
        "hardware/system_carrier/altium/equivalence/"
        "rule_inventory.csv"
    ),
    "pad_net_inventory": (
        "hardware/system_carrier/altium/equivalence/"
        "pad_net_inventory.csv"
    ),
    "layer_stack_inventory": (
        "hardware/system_carrier/altium/equivalence/"
        "layer_stack_inventory.csv"
    ),
    "hierarchy_export": (
        "hardware/system_carrier/altium/equivalence/"
        "hierarchy_export.csv"
    ),
}

PROCEDURES = (
    "ExportNativeAudit",
    "ExportNativeHierarchy",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_text(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and not text.startswith("<")


def validate(
    *,
    receipt_json: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    root = Path(repository_root)
    receipt_path = Path(receipt_json)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path

    errors: list[str] = []
    reasons: list[str] = []

    if not receipt_path.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": ["missing:receipt"],
            "reason_codes": [],
            "runtime_validated": False,
        }

    try:
        receipt = json.loads(
            receipt_path.read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"receipt_parse:{exc}"],
            "reason_codes": [],
            "runtime_validated": False,
        }

    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("receipt_schema")
    if receipt.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")
    if receipt.get("status") != "PASS":
        reasons.append("RECEIPT_NOT_PASS")
    if not _valid_text(receipt.get("altium_version")):
        errors.append("altium_version")
    if not _valid_text(receipt.get("operator")):
        errors.append("operator")

    procedures = receipt.get("procedures")
    if not isinstance(procedures, dict):
        errors.append("procedures")
        procedures = {}

    for procedure in PROCEDURES:
        record = procedures.get(procedure)
        if not isinstance(record, dict):
            errors.append(f"procedure:{procedure}")
            continue
        if record.get("status") != "PASS":
            reasons.append(f"PROCEDURE_NOT_PASS:{procedure}")
        try:
            runtime_errors = int(record.get("runtime_errors", -1))
            runtime_warnings = int(
                record.get("runtime_warnings", -1)
            )
        except (TypeError, ValueError):
            errors.append(f"procedure_counts:{procedure}")
            continue
        if runtime_errors != 0:
            reasons.append(
                f"PROCEDURE_ERRORS:{procedure}:{runtime_errors}"
            )
        if runtime_warnings != 0:
            reasons.append(
                f"PROCEDURE_WARNINGS:{procedure}:{runtime_warnings}"
            )

    claimed_inputs = receipt.get("input_sha256")
    if not isinstance(claimed_inputs, dict):
        errors.append("input_sha256")
        claimed_inputs = {}

    claimed_outputs = receipt.get("output_sha256")
    if not isinstance(claimed_outputs, dict):
        errors.append("output_sha256")
        claimed_outputs = {}

    actual_inputs: dict[str, str] = {}
    actual_outputs: dict[str, str] = {}

    for artifact_id, relative in CANONICAL.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
            continue
        actual = sha256_file(path)
        actual_inputs[artifact_id] = actual
        claimed = str(
            claimed_inputs.get(artifact_id, "")
        ).strip().lower()
        if claimed != actual:
            errors.append(f"hash_mismatch:{artifact_id}")

    for artifact_id, relative in OUTPUTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
            continue
        actual = sha256_file(path)
        actual_outputs[artifact_id] = actual
        claimed = str(
            claimed_outputs.get(artifact_id, "")
        ).strip().lower()
        if claimed != actual:
            errors.append(f"hash_mismatch:{artifact_id}")

    status = "PASS" if not errors and not reasons else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "runtime_validated": status == "PASS",
        "altium_version": receipt.get("altium_version"),
        "operator": receipt.get("operator"),
        "input_sha256": actual_inputs,
        "output_sha256": actual_outputs,
        "receipt_sha256": sha256_file(receipt_path),
        "notes": [
            (
                "PASS validates the operator runtime receipt against the exact "
                "pre-routing native documents, scripts, API contract and CSV "
                "outputs used for equivalence."
            ),
            (
                "The receipt is explicit external Altium Designer execution "
                "evidence; it is never synthesized by repository automation."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        receipt_json=args.receipt,
        repository_root=args.repository_root,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
