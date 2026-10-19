from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.altium_cad_policy import validate as validate_cad_policy
from tools.altium_impedance_gate import validate as validate_impedance
from tools.altium_placement_gate import validate as validate_placement
from tools.altium_power_width_gate import validate as validate_power_width
from tools.altium_room_gate import validate as validate_rooms
from tools.altium_rule_scope_gate import validate as validate_rule_scope
from tools.carrier_prelayout_validate import validate as validate_prelayout


SCHEMA = "ALTIUM-ROUTING-READINESS-001"


def validate(
    *,
    system_root: str | Path,
    generated_dir: str | Path,
) -> dict:
    system = Path(system_root)
    generated = Path(generated_dir)
    altium = system / "altium"

    checks = {
        "cad_policy": validate_cad_policy(system),
        "prelayout": validate_prelayout(
            system_root=system,
            generated_dir=generated,
        ),
        "placement": validate_placement(system),
        "rooms": validate_rooms(system),
        "impedance": validate_impedance(system),
        "power_width": validate_power_width(system),
        "rule_scope": validate_rule_scope(system),
    }

    failed = sorted(
        name
        for name, result in checks.items()
        if result.get("status") != "PASS"
    )

    native_status_path = (
        altium / "ALTIUM_NATIVE_STATUS_SYS_001.json"
    )
    implementation_status_path = (
        altium / "ALTIUM_STATUS_SYS_001.json"
    )

    errors: list[str] = []
    warnings: list[str] = []

    if not native_status_path.is_file():
        errors.append("missing_native_status")
        native_status = {}
    else:
        native_status = json.loads(
            native_status_path.read_text(encoding="utf-8")
        )

    if not implementation_status_path.is_file():
        errors.append("missing_implementation_status")
        implementation_status = {}
    else:
        implementation_status = json.loads(
            implementation_status_path.read_text(
                encoding="utf-8"
            )
        )

    if failed:
        errors.extend(
            f"failed_check:{name}"
            for name in failed
        )

    native_import = str(
        native_status.get(
            "native_import_status",
            "UNKNOWN",
        )
    )
    equivalence = str(
        native_status.get(
            "equivalence_gate_status",
            "UNKNOWN",
        )
    )
    layout_authority = str(
        native_status.get(
            "layout_authority",
            "UNKNOWN",
        )
    )

    production_authority = str(
        native_status.get(
            "production_authority",
            "UNKNOWN",
        )
    )

    production_authorized = (
        production_authority == "AUTHORIZED"
    )

    prep_ok = not errors

    native_ready = (
        native_import in {
            "IMPORTED",
            "PASS",
            "NATIVE_FILES_READY",
        }
        and equivalence == "PASS"
        and layout_authority == "AUTHORIZED"
    )

    if not prep_ok:
        status = "BLOCKED"
        routing_authorized = False
        next_action = "FIX_PREPARATORY_GATES"
    elif native_ready:
        status = "READY_FOR_ROUTING"
        routing_authorized = True
        next_action = "BEGIN_NATIVE_ALTIUM_PLACEMENT_AND_ROUTING"
    else:
        status = "READY_FOR_NATIVE_IMPORT"
        routing_authorized = False
        next_action = "RUN_NATIVE_ALTIUM_IMPORT_AND_EQUIVALENCE"

    current_phase = str(
        implementation_status.get(
            "current_phase",
            "UNKNOWN",
        )
    )

    if status == "READY_FOR_NATIVE_IMPORT":
        warnings.append(
            "routing_not_authorized_until_native_equivalence_pass"
        )

    return {
        "schema": SCHEMA,
        "status": status,
        "routing_authorized": routing_authorized,
        "production_authorized": production_authorized,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "failed_checks": failed,
        "current_phase": current_phase,
        "native_import_status": native_import,
        "equivalence_gate_status": equivalence,
        "layout_authority": layout_authority,
        "production_authority": production_authority,
        "next_action": next_action,
        "checks": {
            name: {
                "schema": result.get("schema"),
                "status": result.get("status"),
                "error_count": len(
                    result.get("errors", [])
                ),
                "warning_count": len(
                    result.get("warnings", [])
                ),
            }
            for name, result in checks.items()
        },
        "notes": [
            (
                "READY_FOR_NATIVE_IMPORT means all repository-controlled "
                "routing prerequisites pass; it does not authorize routing."
            ),
            (
                "READY_FOR_ROUTING is possible only after native Altium "
                "SchDoc/PcbDoc import and ALTIUM_EQUIVALENCE_GATE PASS."
            ),
            (
                "Production authority remains separate from routing authority; "
                "when already AUTHORIZED by the production-release gate it does "
                "not invalidate READY_FOR_ROUTING."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
        generated_dir=args.generated_dir,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
