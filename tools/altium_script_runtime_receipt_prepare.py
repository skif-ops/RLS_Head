from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.altium_script_runtime_receipt import (
    CANONICAL,
    OUTPUTS,
    sha256_file,
    sha256_runtime_input,
)


SCHEMA = "ALTIUM-SCRIPT-RUNTIME-RECEIPT-PREPARE-001"


def _valid_text(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and not text.startswith("<")


def prepare(
    *,
    repository_root: str | Path = ".",
    altium_version: str,
    operator: str,
) -> dict:
    root = Path(repository_root)
    errors: list[str] = []

    if not _valid_text(altium_version):
        errors.append("altium_version")
    if not _valid_text(operator):
        errors.append("operator")

    input_hashes: dict[str, str] = {}
    output_hashes: dict[str, str] = {}

    for artifact_id, relative in CANONICAL.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
            continue
        input_hashes[artifact_id] = sha256_runtime_input(path, artifact_id)

    for artifact_id, relative in OUTPUTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{artifact_id}")
            continue
        output_hashes[artifact_id] = sha256_file(path)

    receipt = {
        "schema": "ALTIUM-SCRIPT-RUNTIME-RECEIPT-001",
        "status": "PENDING",
        "board_id": "EVT-SYS-CARRIER",
        "altium_version": altium_version,
        "operator": operator,
        "procedures": {
            "ExportNativeAudit": {
                "status": "PENDING",
                "runtime_errors": None,
                "runtime_warnings": None,
            },
            "ExportNativeHierarchy": {
                "status": "PENDING",
                "runtime_errors": None,
                "runtime_warnings": None,
            },
        },
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
        "prepared_by": "tools.altium_script_runtime_receipt_prepare",
        "attestation_required": True,
        "notes": [
            (
                "Hashes are generated from the current canonical project, "
                "native documents, script sources/API contract and exporter "
                "outputs. They are not an execution PASS assertion."
            ),
            (
                "After confirming the real Altium Designer run, the operator "
                "must explicitly set top-level status and both procedure status "
                "fields to PASS and record zero runtime errors/warnings before "
                "running the validator."
            ),
        ],
    }

    return {
        "schema": SCHEMA,
        "status": "READY" if not errors else "INCOMPLETE",
        "errors": sorted(set(errors)),
        "receipt": receipt,
        "attestation_required": True,
        "notes": [
            (
                "READY only means all hash inputs/outputs exist. This tool "
                "never marks the runtime receipt PASS."
            )
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--altium-version", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = prepare(
        repository_root=args.repository_root,
        altium_version=args.altium_version,
        operator=args.operator,
    )

    if result["status"] == "READY":
        Path(args.output).write_text(
            json.dumps(result["receipt"], indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    print(result["status"])
    return 0 if result["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
