from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_cad_policy import validate as validate_cad_policy
from tools.altium_evt_mechanical_datum_gate import (
    validate as validate_evt_mechanical_datum,
)
from tools.altium_evt_routing_stack_gate import (
    validate as validate_evt_routing_stack,
)
from tools.altium_impedance_gate import validate as validate_impedance
from tools.altium_placement_gate import validate as validate_placement
from tools.altium_power_width_gate import validate as validate_power_width
from tools.altium_room_gate import validate as validate_rooms
from tools.altium_rule_scope_gate import validate as validate_rule_scope
from tools.carrier_prelayout_validate import validate as validate_prelayout


SCHEMA = "ALTIUM-ROUTING-READINESS-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "evt_mechanical_datum": validate_evt_mechanical_datum(system),
        "rooms": validate_rooms(system),
        "impedance": validate_impedance(system),
        "evt_routing_stack": validate_evt_routing_stack(system),
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
    cad_authority_path = system / "CAD_AUTHORITY_SYS_001.json"
    equivalence_result_path = (
        altium / "equivalence" / "altium_equivalence_result.json"
    )
    production_result_path = (
        altium / "release" / "production_release_result.json"
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

    if not cad_authority_path.is_file():
        errors.append("missing_cad_authority")
        cad_authority = {}
    else:
        cad_authority = json.loads(
            cad_authority_path.read_text(encoding="utf-8")
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

    current_phase = str(
        implementation_status.get(
            "current_phase",
            "UNKNOWN",
        )
    )
    implementation_altium = implementation_status.get("altium")
    if not isinstance(implementation_altium, dict):
        implementation_altium = {}
    implementation_routing = implementation_status.get(
        "routing_readiness"
    )
    if not isinstance(implementation_routing, dict):
        implementation_routing = {}
    authority_routing = cad_authority.get("routing_readiness_gate")
    if not isinstance(authority_routing, dict):
        authority_routing = {}

    native_layout_claim = (
        equivalence == "PASS"
        and layout_authority == "AUTHORIZED"
    )
    implementation_layout_claim = (
        implementation_altium.get("equivalence_gate") is True
        and implementation_routing.get("routing_authorized") is True
        and current_phase in {"READY_FOR_ROUTING", "PRODUCTION_RELEASED"}
    )
    cad_layout_claim = (
        cad_authority.get("native_document_status")
        == "NATIVE_EQUIVALENCE_PASS"
        and cad_authority.get("pcb_layout_authority")
        == "ALTIUM_AUTHORIZED"
        and authority_routing.get("current_expected_status")
        == "READY_FOR_ROUTING"
        and cad_authority.get("pcb_design_phase")
        in {"ALTIUM_NATIVE_ROUTING", "PRODUCTION_RELEASED"}
    )

    layout_claimed = (
        native_layout_claim
        or implementation_layout_claim
        or cad_layout_claim
    )
    layout_authority_consensus = (
        native_layout_claim
        and implementation_layout_claim
        and cad_layout_claim
    )
    authority_consensus_errors: list[str] = []
    current_equivalence_result_sha256 = ""
    current_production_result_sha256 = ""

    def _validate_result_file(
        *,
        path: Path,
        tracked_hash: str,
        expected_production_authority: str,
        prefix: str,
    ) -> str:
        if not path.is_file():
            authority_consensus_errors.append(
                f"result:{prefix}_missing"
            )
            return ""

        actual_hash = sha256_file(path)
        if (
            len(tracked_hash) != 64
            or tracked_hash != actual_hash
        ):
            authority_consensus_errors.append(
                f"hash:{prefix}_result_file"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            authority_consensus_errors.append(
                f"result:{prefix}_parse"
            )
            return actual_hash

        expected_schema = (
            "ALTIUM-EQUIVALENCE-RESULT-001"
            if prefix == "equivalence"
            else "ALTIUM-PRODUCTION-RELEASE-RESULT-001"
        )
        if (
            payload.get("schema") != expected_schema
            or payload.get("status") != "PASS"
            or payload.get("layout_authority") != "AUTHORIZED"
            or payload.get("production_authority")
            != expected_production_authority
        ):
            authority_consensus_errors.append(
                f"result:{prefix}_semantics"
            )

        return actual_hash

    if layout_claimed and not layout_authority_consensus:
        if not native_layout_claim:
            authority_consensus_errors.append(
                "layout:native_status"
            )
        if not implementation_layout_claim:
            authority_consensus_errors.append(
                "layout:implementation_status"
            )
        if not cad_layout_claim:
            authority_consensus_errors.append(
                "layout:cad_authority"
            )

    native_production_claim = (
        production_authority == "AUTHORIZED"
    )
    implementation_production_claim = (
        implementation_altium.get(
            "production_release_authorized"
        )
        is True
        and current_phase == "PRODUCTION_RELEASED"
    )
    cad_production_claim = (
        cad_authority.get("production_release_authorized") is True
        and cad_authority.get("pcb_design_phase")
        == "PRODUCTION_RELEASED"
    )
    production_claimed = (
        native_production_claim
        or implementation_production_claim
        or cad_production_claim
    )
    production_authority_consensus = (
        native_production_claim
        and implementation_production_claim
        and cad_production_claim
    )

    if production_claimed and not production_authority_consensus:
        if not native_production_claim:
            authority_consensus_errors.append(
                "production:native_status"
            )
        if not implementation_production_claim:
            authority_consensus_errors.append(
                "production:implementation_status"
            )
        if not cad_production_claim:
            authority_consensus_errors.append(
                "production:cad_authority"
            )

    def _tracked_hash_mismatch(
        field: str,
        values: list[str],
    ) -> bool:
        normalized = [
            str(value or "").strip().lower()
            for value in values
        ]
        return (
            any(len(value) != 64 for value in normalized)
            or len(set(normalized)) != 1
        )

    if layout_authority_consensus:
        if _tracked_hash_mismatch(
            "native_schematic_sha256",
            [
                native_status.get("native_schematic_sha256", ""),
                cad_authority.get("native_schematic_sha256", ""),
            ],
        ):
            authority_consensus_errors.append(
                "hash:native_schematic_sha256"
            )

        if _tracked_hash_mismatch(
            "native_pcb_sha256",
            [
                native_status.get("native_pcb_sha256", ""),
                implementation_altium.get("native_pcb_sha256", ""),
                cad_authority.get("native_pcb_sha256", ""),
            ],
        ):
            authority_consensus_errors.append(
                "hash:native_pcb_sha256"
            )

        tracked_equivalence_hash = str(
            native_status.get("equivalence_result_sha256", "")
        ).strip().lower()
        if _tracked_hash_mismatch(
            "equivalence_result_sha256",
            [
                tracked_equivalence_hash,
                cad_authority.get("equivalence_result_sha256", ""),
            ],
        ):
            authority_consensus_errors.append(
                "hash:equivalence_result_sha256"
            )

        current_equivalence_result_sha256 = _validate_result_file(
            path=equivalence_result_path,
            tracked_hash=tracked_equivalence_hash,
            expected_production_authority="NOT_AUTHORIZED",
            prefix="equivalence",
        )

    if production_authority_consensus:
        if _tracked_hash_mismatch(
            "production_release_source_pcb_sha256",
            [
                native_status.get(
                    "production_release_source_pcb_sha256",
                    "",
                ),
                implementation_altium.get(
                    "production_release_source_pcb_sha256",
                    "",
                ),
                cad_authority.get(
                    "production_release_source_pcb_sha256",
                    "",
                ),
            ],
        ):
            authority_consensus_errors.append(
                "hash:production_release_source_pcb_sha256"
            )

        tracked_production_hash = str(
            native_status.get(
                "production_release_result_sha256",
                "",
            )
        ).strip().lower()
        if _tracked_hash_mismatch(
            "production_release_result_sha256",
            [
                tracked_production_hash,
                cad_authority.get(
                    "production_release_result_sha256",
                    "",
                ),
            ],
        ):
            authority_consensus_errors.append(
                "hash:production_release_result_sha256"
            )

        current_production_result_sha256 = _validate_result_file(
            path=production_result_path,
            tracked_hash=tracked_production_hash,
            expected_production_authority="AUTHORIZED",
            prefix="production",
        )

    if authority_consensus_errors:
        errors.extend(
            f"authority_consensus:{item}"
            for item in authority_consensus_errors
        )

    production_authorized = production_authority_consensus

    equivalence_stale = False
    expected_schematic_hash = str(
        native_status.get(
            "native_schematic_sha256",
            "",
        )
    ).strip().lower()
    current_schematic_hash = ""
    schematic_path = altium / "native" / "EVT_SYS_CARRIER.SchDoc"

    equivalence_authorized = layout_authority_consensus
    if equivalence_authorized:
        if not schematic_path.is_file():
            equivalence_stale = True
            warnings.append("equivalence_native_schematic_missing")
        else:
            current_schematic_hash = sha256_file(schematic_path)
            if (
                len(expected_schematic_hash) != 64
                or current_schematic_hash != expected_schematic_hash
            ):
                equivalence_stale = True
                warnings.append("equivalence_schematic_hash_mismatch")

        if equivalence_stale:
            production_authorized = False

    production_release_stale = False
    expected_release_pcb_hash = str(
        native_status.get(
            "production_release_source_pcb_sha256",
            "",
        )
    ).strip().lower()
    current_pcb_hash = ""
    pcb_path = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"

    if production_authorized:
        if not pcb_path.is_file():
            production_release_stale = True
            warnings.append("production_release_native_pcb_missing")
        else:
            current_pcb_hash = sha256_file(pcb_path)
            if (
                len(expected_release_pcb_hash) != 64
                or current_pcb_hash != expected_release_pcb_hash
            ):
                production_release_stale = True
                warnings.append("production_release_pcb_hash_mismatch")

        if production_release_stale:
            production_authorized = False

    prep_ok = not errors

    native_ready = (
        native_import in {
            "IMPORTED",
            "PASS",
            "NATIVE_FILES_READY",
        }
        and layout_authority_consensus
        and not equivalence_stale
    )

    if not prep_ok:
        status = "BLOCKED"
        routing_authorized = False
        next_action = "FIX_PREPARATORY_GATES"
    elif equivalence_stale:
        status = "STALE_EQUIVALENCE"
        routing_authorized = False
        next_action = "RERUN_NATIVE_ALTIUM_EQUIVALENCE_GATE"
    elif native_ready:
        status = "READY_FOR_ROUTING"
        routing_authorized = True
        next_action = (
            "RERUN_PRODUCTION_RELEASE_GATE"
            if production_release_stale
            else (
                "PRODUCTION_RELEASED"
                if production_authorized
                else "BEGIN_NATIVE_ALTIUM_PLACEMENT_AND_ROUTING"
            )
        )
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
        "layout_authority_consensus": layout_authority_consensus,
        "production_authority_consensus": production_authority_consensus,
        "authority_consensus_errors": sorted(
            set(authority_consensus_errors)
        ),
        "current_equivalence_result_sha256": (
            current_equivalence_result_sha256
        ),
        "current_production_result_sha256": (
            current_production_result_sha256
        ),
        "equivalence_stale": equivalence_stale,
        "expected_schematic_sha256": expected_schematic_hash,
        "current_schematic_sha256": current_schematic_hash,
        "production_release_stale": production_release_stale,
        "expected_release_pcb_sha256": expected_release_pcb_hash,
        "current_pcb_sha256": current_pcb_hash,
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
                "READY_FOR_ROUTING requires consensus across "
                "ALTIUM_NATIVE_STATUS, ALTIUM_STATUS and CAD_AUTHORITY; "
                "a partial tracked-status update fails closed."
            ),
            (
                "Tracked gate-result hashes must also match the canonical "
                "committed equivalence/production result files and their PASS "
                "authority semantics."
            ),
            (
                "READY_FOR_ROUTING is possible only after native Altium "
                "SchDoc/PcbDoc import and ALTIUM_EQUIVALENCE_GATE PASS."
            ),
            (
                "Native SchDoc is the electrical equivalence baseline. If it "
                "changes after equivalence PASS, effective routing and production "
                "authority are withdrawn until equivalence is rerun."
            ),
            (
                "Production authority remains separate from routing authority. "
                "If only the final native PcbDoc changes after production release, "
                "routing authority remains valid but effective production "
                "authorization is withdrawn until the release gate is rerun."
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
