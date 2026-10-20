from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-AUTHORITY-RECONCILE-001"

SYSTEM_REL = Path("hardware/system_carrier")
ALTIUM_REL = SYSTEM_REL / "altium"
NATIVE_REL = ALTIUM_REL / "native"
EQUIV_REL = ALTIUM_REL / "equivalence"
RELEASE_REL = ALTIUM_REL / "release"

PATHS = {
    "schematic": NATIVE_REL / "EVT_SYS_CARRIER.SchDoc",
    "pcb": NATIVE_REL / "EVT_SYS_CARRIER.PcbDoc",
    "equivalence_result": EQUIV_REL / "altium_equivalence_result.json",
    "production_result": RELEASE_REL / "production_release_result.json",
    "native_status": ALTIUM_REL / "ALTIUM_NATIVE_STATUS_SYS_001.json",
    "implementation_status": ALTIUM_REL / "ALTIUM_STATUS_SYS_001.json",
    "cad_authority": SYSTEM_REL / "CAD_AUTHORITY_SYS_001.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _equivalence_schematic_hash(payload: dict) -> str:
    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        return ""
    schematic = integrity.get("schematic")
    if not isinstance(schematic, dict):
        return ""
    return str(
        schematic.get("sha256_actual", "")
    ).strip().lower()


def reconcile(
    *,
    repository_root: str | Path = ".",
    apply: bool = False,
) -> dict:
    root = Path(repository_root)
    resolved = {
        key: root / relative
        for key, relative in PATHS.items()
    }

    errors: list[str] = []
    actions: list[str] = []

    for key in (
        "native_status",
        "implementation_status",
        "cad_authority",
    ):
        if not resolved[key].is_file():
            errors.append(f"missing:{key}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": sorted(errors),
            "actions": actions,
            "applied": False,
            "layout_authority_effective": False,
            "production_authority_effective": False,
        }

    try:
        native_status = _read_json(resolved["native_status"])
        implementation = _read_json(resolved["implementation_status"])
        authority = _read_json(resolved["cad_authority"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": [f"status_parse:{exc}"],
            "actions": actions,
            "applied": False,
            "layout_authority_effective": False,
            "production_authority_effective": False,
        }

    tracked_layout = (
        native_status.get("layout_authority") == "AUTHORIZED"
        or authority.get("pcb_layout_authority") == "ALTIUM_AUTHORIZED"
    )
    tracked_production = (
        native_status.get("production_authority") == "AUTHORIZED"
        or implementation.get("altium", {}).get(
            "production_release_authorized"
        )
        is True
        or authority.get("production_release_authorized") is True
    )

    equivalence_valid = False
    equivalence_reason = "NOT_AUTHORIZED"
    current_schematic_hash = ""
    approved_schematic_hash = ""

    if tracked_layout:
        if not resolved["equivalence_result"].is_file():
            equivalence_reason = "MISSING_EQUIVALENCE_RESULT"
        elif not resolved["schematic"].is_file():
            equivalence_reason = "MISSING_NATIVE_SCHEMATIC"
        else:
            try:
                equivalence = _read_json(
                    resolved["equivalence_result"]
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                equivalence_reason = "INVALID_EQUIVALENCE_RESULT"
            else:
                current_schematic_hash = sha256_file(
                    resolved["schematic"]
                )
                approved_schematic_hash = _equivalence_schematic_hash(
                    equivalence
                )
                equivalence_valid = (
                    equivalence.get("schema")
                    == "ALTIUM-EQUIVALENCE-RESULT-001"
                    and equivalence.get("status") == "PASS"
                    and equivalence.get("layout_authority")
                    == "AUTHORIZED"
                    and len(approved_schematic_hash) == 64
                    and current_schematic_hash
                    == approved_schematic_hash
                )
                equivalence_reason = (
                    "PASS"
                    if equivalence_valid
                    else "STALE_OR_INVALID_EQUIVALENCE"
                )

    production_valid = False
    production_reason = "NOT_AUTHORIZED"
    current_pcb_hash = ""
    approved_pcb_hash = ""

    if tracked_production:
        if not equivalence_valid:
            production_reason = "EQUIVALENCE_NOT_VALID"
        elif not resolved["production_result"].is_file():
            production_reason = "MISSING_PRODUCTION_RESULT"
        elif not resolved["pcb"].is_file():
            production_reason = "MISSING_NATIVE_PCB"
        else:
            try:
                production = _read_json(
                    resolved["production_result"]
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                production_reason = "INVALID_PRODUCTION_RESULT"
            else:
                current_pcb_hash = sha256_file(resolved["pcb"])
                approved_pcb_hash = str(
                    production.get("native_pcb_sha256", "")
                ).strip().lower()
                production_valid = (
                    production.get("schema")
                    == "ALTIUM-PRODUCTION-RELEASE-RESULT-001"
                    and production.get("status") == "PASS"
                    and production.get("production_authority")
                    == "AUTHORIZED"
                    and len(approved_pcb_hash) == 64
                    and current_pcb_hash == approved_pcb_hash
                )
                production_reason = (
                    "PASS"
                    if production_valid
                    else "STALE_OR_INVALID_PRODUCTION_RELEASE"
                )

    layout_revoked = tracked_layout and not equivalence_valid
    production_revoked = tracked_production and not production_valid

    if layout_revoked:
        actions.append("REVOKE_LAYOUT_AUTHORITY")
        actions.append("REVOKE_PRODUCTION_AUTHORITY")
    elif production_revoked:
        actions.append("REVOKE_PRODUCTION_AUTHORITY")

    if apply and actions:
        if layout_revoked:
            native_status["equivalence_gate_status"] = "STALE"
            native_status["layout_authority"] = "NOT_AUTHORIZED"
            native_status["production_authority"] = "NOT_AUTHORIZED"
            native_status["equivalence_stale"] = True

            altium = implementation.setdefault("altium", {})
            altium["equivalence_gate"] = False
            altium["production_release_authorized"] = False
            implementation["current_phase"] = "EQUIVALENCE_STALE"
            implementation["next_required_phase"] = (
                "NATIVE_ALTIUM_REEQUIVALENCE"
            )
            routing = implementation.setdefault(
                "routing_readiness",
                {},
            )
            routing["expected_status"] = "STALE_EQUIVALENCE"
            routing["routing_authorized"] = False
            routing["required_to_authorize"] = [
                "RERUN_NATIVE_ALTIUM_EQUIVALENCE_GATE"
            ]

            authority["native_document_status"] = (
                "NATIVE_EQUIVALENCE_STALE"
            )
            authority["pcb_layout_authority"] = "NOT_AUTHORIZED"
            authority["pcb_design_phase"] = (
                "ALTIUM_REEQUIVALENCE_REQUIRED"
            )
            authority["production_release_authorized"] = False
            routing_gate = authority.setdefault(
                "routing_readiness_gate",
                {},
            )
            routing_gate["current_expected_status"] = (
                "STALE_EQUIVALENCE"
            )

        elif production_revoked:
            native_status["production_authority"] = "NOT_AUTHORIZED"
            native_status["production_release_stale"] = True

            altium = implementation.setdefault("altium", {})
            altium["production_release_authorized"] = False
            implementation["current_phase"] = "READY_FOR_ROUTING"
            implementation["next_required_phase"] = (
                "RERUN_PRODUCTION_RELEASE"
            )

            authority["production_release_authorized"] = False
            authority["pcb_design_phase"] = "ALTIUM_NATIVE_ROUTING"

        _write_json(resolved["native_status"], native_status)
        _write_json(
            resolved["implementation_status"],
            implementation,
        )
        _write_json(resolved["cad_authority"], authority)

    if errors:
        status = "INVALID"
    elif actions:
        status = "REVOKED" if apply else "REVOCATION_REQUIRED"
    else:
        status = "UNCHANGED"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "actions": actions,
        "applied": bool(apply and actions),
        "tracked_layout_authority": tracked_layout,
        "tracked_production_authority": tracked_production,
        "layout_authority_effective": (
            tracked_layout and equivalence_valid
        ),
        "production_authority_effective": (
            tracked_production and production_valid
        ),
        "equivalence_validation": {
            "status": equivalence_reason,
            "approved_schematic_sha256": approved_schematic_hash,
            "current_schematic_sha256": current_schematic_hash,
        },
        "production_validation": {
            "status": production_reason,
            "approved_pcb_sha256": approved_pcb_hash,
            "current_pcb_sha256": current_pcb_hash,
        },
        "notes": [
            (
                "This tool is revoke-only. It never grants layout or "
                "production authority."
            ),
            (
                "Use --apply only to synchronize tracked JSON after stale "
                "authority is detected."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = reconcile(
        repository_root=args.repository_root,
        apply=args.apply,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] != "INVALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
