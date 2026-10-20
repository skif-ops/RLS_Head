from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "ALTIUM-SCRIPT-API-COMPAT-RESULT-001"
CONTRACT_SCHEMA = "ALTIUM-SCRIPT-API-COMPAT-001"
ALLOWED_SYMBOL_STATUS = {"DOCUMENTED", "RUNTIME_VERIFY"}


def _safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe script path: {relative}")
    root_resolved = root.resolve()
    path = (root / rel).resolve()
    path.relative_to(root_resolved)
    return path


def validate(
    *,
    contract_path: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    root = Path(repository_root)
    contract_file = Path(contract_path)
    if not contract_file.is_absolute():
        contract_file = root / contract_file

    errors: list[str] = []
    warnings: list[str] = []

    try:
        contract = json.loads(contract_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"contract_parse:{exc}"],
            "warnings": [],
            "runtime_validation_required": True,
        }

    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("contract_schema")
    if contract.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")
    if contract.get("runtime_validation_required") is not True:
        errors.append("runtime_validation_required")

    scripts = contract.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        errors.append("scripts")
        scripts = []

    script_results: dict[str, dict] = {}
    documented_count = 0
    runtime_verify_count = 0
    seen_ids: set[str] = set()

    for entry in scripts:
        if not isinstance(entry, dict):
            errors.append("script_entry")
            continue

        script_id = str(entry.get("id", "")).strip()
        relative = str(entry.get("path", "")).strip()
        if not script_id:
            errors.append("script_without_id")
            continue
        if script_id in seen_ids:
            errors.append(f"duplicate_script:{script_id}")
            continue
        seen_ids.add(script_id)

        try:
            path = _safe_path(root, relative)
        except (ValueError, OSError) as exc:
            errors.append(f"script_path:{script_id}:{exc}")
            continue

        if not path.is_file():
            errors.append(f"missing_script:{script_id}")
            continue

        text = path.read_text(encoding="utf-8")
        item_errors: list[str] = []
        item_warnings: list[str] = []

        procedure = str(entry.get("run_procedure", "")).strip()
        if not procedure or procedure not in text:
            item_errors.append("run_procedure")

        required = entry.get("required_symbols")
        if not isinstance(required, list) or not required:
            item_errors.append("required_symbols")
            required = []

        symbol_names: set[str] = set()
        for record in required:
            if not isinstance(record, dict):
                item_errors.append("required_symbol_entry")
                continue
            symbol = str(record.get("symbol", "")).strip()
            status = str(record.get("status", "")).strip()
            access = str(record.get("access", "")).strip()

            if not symbol:
                item_errors.append("blank_required_symbol")
                continue
            if symbol in symbol_names:
                item_errors.append(f"duplicate_symbol:{symbol}")
            symbol_names.add(symbol)

            if status not in ALLOWED_SYMBOL_STATUS:
                item_errors.append(f"symbol_status:{symbol}:{status}")
            elif status == "DOCUMENTED":
                documented_count += 1
            else:
                runtime_verify_count += 1
                item_warnings.append(f"runtime_verify:{symbol}")

            if not access:
                item_errors.append(f"symbol_access:{symbol}")
            if symbol not in text:
                item_errors.append(f"missing_symbol:{symbol}")

        forbidden = entry.get("forbidden_tokens")
        if not isinstance(forbidden, list):
            item_errors.append("forbidden_tokens")
            forbidden = []

        for token in forbidden:
            token_text = str(token)
            if token_text and token_text in text:
                item_errors.append(f"forbidden_token:{token_text}")

        outputs = entry.get("expected_outputs")
        if not isinstance(outputs, list) or not outputs:
            item_errors.append("expected_outputs")
            outputs = []
        for output in outputs:
            if str(output) not in text:
                item_errors.append(f"missing_output:{output}")

        if item_errors:
            errors.extend(
                f"{script_id}:{item}" for item in item_errors
            )
        warnings.extend(
            f"{script_id}:{item}" for item in item_warnings
        )
        script_results[script_id] = {
            "path": relative,
            "status": "PASS" if not item_errors else "FAIL",
            "error_count": len(item_errors),
            "warning_count": len(item_warnings),
            "required_symbol_count": len(symbol_names),
            "expected_output_count": len(outputs),
        }

    runtime_gate = contract.get("runtime_gate")
    if not isinstance(runtime_gate, dict):
        errors.append("runtime_gate")
    elif runtime_gate.get("status") != "REQUIRED_IN_ALTIUM_DESIGNER":
        errors.append("runtime_gate_status")

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "documented_symbol_count": documented_count,
        "runtime_verify_symbol_count": runtime_verify_count,
        "runtime_validation_required": True,
        "runtime_gate_status": "REQUIRED_IN_ALTIUM_DESIGNER",
        "scripts": script_results,
        "notes": [
            (
                "PASS proves repository contract coverage and read-only static "
                "policy only; it does not prove DelphiScript execution in Altium."
            ),
            (
                "RUNTIME_VERIFY symbols and both exporter procedures must be "
                "validated on the target Altium Designer installation."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        contract_path=args.contract,
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
