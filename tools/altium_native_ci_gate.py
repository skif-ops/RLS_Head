from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_gate import validate_manifest as validate_equivalence
from tools.altium_native_handoff_status import evaluate as evaluate_handoff
from tools.altium_production_release_gate import (
    validate_manifest as validate_production_release,
)
from tools.altium_routing_readiness import validate as validate_routing


SCHEMA = "ALTIUM-NATIVE-CI-GATE-001"

SYSTEM_REL = Path("hardware/system_carrier")
ALTIUM_REL = SYSTEM_REL / "altium"
NATIVE_REL = ALTIUM_REL / "native"
EQUIV_REL = ALTIUM_REL / "equivalence"

SCHDOC_REL = NATIVE_REL / "EVT_SYS_CARRIER.SchDoc"
PCBDOC_REL = NATIVE_REL / "EVT_SYS_CARRIER.PcbDoc"
MANIFEST_REL = EQUIV_REL / "manifest.json"
GATE_RESULT_REL = EQUIV_REL / "altium_equivalence_result.json"
NATIVE_STATUS_REL = ALTIUM_REL / "ALTIUM_NATIVE_STATUS_SYS_001.json"
IMPLEMENTATION_STATUS_REL = ALTIUM_REL / "ALTIUM_STATUS_SYS_001.json"
CAD_AUTHORITY_REL = SYSTEM_REL / "CAD_AUTHORITY_SYS_001.json"
RELEASE_REL = ALTIUM_REL / "release"
RELEASE_MANIFEST_REL = RELEASE_REL / "manifest.json"
PRODUCTION_RESULT_REL = RELEASE_REL / "production_release_result.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_production_surfaces(root: Path) -> dict[str, bool] | None:
    paths = {
        "native_status": root / NATIVE_STATUS_REL,
        "implementation_status": root / IMPLEMENTATION_STATUS_REL,
        "cad_authority": root / CAD_AUTHORITY_REL,
    }
    if not all(path.is_file() for path in paths.values()):
        return None

    try:
        native_status = read_json(paths["native_status"])
        implementation = read_json(paths["implementation_status"])
        authority = read_json(paths["cad_authority"])
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    altium = implementation.get("altium")
    if not isinstance(altium, dict):
        altium = {}

    return {
        "native_status": (
            native_status.get("production_authority") == "AUTHORIZED"
        ),
        "implementation_status": (
            altium.get("production_release_authorized") is True
        ),
        "cad_authority": (
            authority.get("production_release_authorized") is True
        ),
    }


def evaluate(
    *,
    repository_root: str | Path = ".",
    generated_dir: str | Path | None = None,
) -> dict:
    root = Path(repository_root)
    system = root / SYSTEM_REL
    schdoc = root / SCHDOC_REL
    pcbdoc = root / PCBDOC_REL
    errors: list[str] = []
    warnings: list[str] = []

    sch_present = schdoc.is_file()
    pcb_present = pcbdoc.is_file()

    handoff = evaluate_handoff(root)
    routing = None

    if generated_dir is not None:
        generated_path = Path(generated_dir)
        if not generated_path.is_absolute():
            generated_path = root / generated_path
        routing = validate_routing(
            system_root=system,
            generated_dir=generated_path,
        )

    if not sch_present and not pcb_present:
        phase = "PRE_IMPORT"

        if handoff.get("status") != "WAITING_NATIVE_IMPORT":
            errors.append(
                "pre_import_handoff_status:"
                + str(handoff.get("status"))
            )

        if routing is not None:
            if routing.get("status") != "READY_FOR_NATIVE_IMPORT":
                errors.append(
                    "pre_import_routing_status:"
                    + str(routing.get("status"))
                )
            if routing.get("routing_authorized") is not False:
                errors.append("pre_import_routing_authorized")

        status = "PASS" if not errors else "FAIL"
        return {
            "schema": SCHEMA,
            "status": status,
            "phase": phase,
            "errors": sorted(set(errors)),
            "warnings": warnings,
            "native_schdoc_present": False,
            "native_pcbdoc_present": False,
            "handoff_status": handoff.get("status"),
            "routing_status": (
                routing.get("status")
                if isinstance(routing, dict)
                else None
            ),
            "routing_authorized": False,
            "production_authorized": False,
            "notes": [
                (
                    "PRE_IMPORT PASS requires no native Altium documents and "
                    "repository readiness to remain at the import boundary."
                )
            ],
        }

    if sch_present != pcb_present:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "phase": "INCOMPLETE_NATIVE_PAIR",
            "errors": ["native_document_pair_incomplete"],
            "warnings": warnings,
            "native_schdoc_present": sch_present,
            "native_pcbdoc_present": pcb_present,
            "handoff_status": handoff.get("status"),
            "routing_status": (
                routing.get("status")
                if isinstance(routing, dict)
                else None
            ),
            "routing_authorized": False,
            "production_authorized": False,
            "notes": [
                "SchDoc and PcbDoc must enter the repository as a complete native pair."
            ],
        }

    production_result_path = root / PRODUCTION_RESULT_REL
    production_result_present = production_result_path.is_file()
    production_result_pass = False
    production_authority_surfaces = _tracked_production_surfaces(root)
    production_released = False

    if production_result_present:
        try:
            production_probe = read_json(production_result_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"production_result_parse:{exc}")
        else:
            if (
                production_probe.get("schema")
                != "ALTIUM-PRODUCTION-RELEASE-RESULT-001"
            ):
                errors.append("production_result_schema")
            if production_probe.get("status") != "PASS":
                errors.append("committed_production_not_pass")
            if production_probe.get("layout_authority") != "AUTHORIZED":
                errors.append("committed_production_layout_authority")
            if (
                production_probe.get("production_authority")
                != "AUTHORIZED"
            ):
                errors.append("committed_production_authority")

            production_result_pass = (
                production_probe.get("schema")
                == "ALTIUM-PRODUCTION-RELEASE-RESULT-001"
                and production_probe.get("status") == "PASS"
                and production_probe.get("layout_authority") == "AUTHORIZED"
                and production_probe.get("production_authority")
                == "AUTHORIZED"
            )

    if (
        production_result_pass
        and isinstance(production_authority_surfaces, dict)
    ):
        surface_values = list(
            production_authority_surfaces.values()
        )
        if any(surface_values) and not all(surface_values):
            errors.append("production_authority_surface_consensus")
        elif all(surface_values):
            production_released = True
        else:
            warnings.append(
                "historical_production_result_inactive"
            )

    phase = (
        "POST_PRODUCTION"
        if production_released
        else "POST_EQUIVALENCE"
    )

    if handoff.get("status") != "READY_TO_RUN_EQUIVALENCE_GATE":
        errors.append(
            "post_import_handoff_status:"
            + str(handoff.get("status"))
        )

    manifest_path = root / MANIFEST_REL
    committed_gate_path = root / GATE_RESULT_REL
    native_status_path = root / NATIVE_STATUS_REL
    implementation_status_path = root / IMPLEMENTATION_STATUS_REL
    authority_path = root / CAD_AUTHORITY_REL
    release_manifest_path = root / RELEASE_MANIFEST_REL

    for label, path in (
        ("manifest", manifest_path),
        ("equivalence_result", committed_gate_path),
        ("native_status", native_status_path),
        ("implementation_status", implementation_status_path),
        ("cad_authority", authority_path),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if production_released and not release_manifest_path.is_file():
        errors.append("missing:production_release_manifest")

    rerun_gate = None
    committed_gate = None
    approved_schematic_hash = ""
    approved_pcb_hash = ""
    current_schematic_hash = sha256_file(schdoc)
    current_pcb_hash = sha256_file(pcbdoc)
    layout_evolved_since_equivalence = False
    native_status = None
    implementation_status = None
    authority = None
    rerun_production = None
    committed_production = None

    if committed_gate_path.is_file():
        try:
            committed_gate = read_json(committed_gate_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"equivalence_result_parse:{exc}")
        else:
            if committed_gate.get("status") != "PASS":
                errors.append("committed_equivalence_not_pass")
            if committed_gate.get("layout_authority") != "AUTHORIZED":
                errors.append("committed_layout_authority")
            if committed_gate.get("production_authority") != "NOT_AUTHORIZED":
                errors.append("committed_production_authority")

            integrity = committed_gate.get("integrity")
            if not isinstance(integrity, dict):
                errors.append("committed_equivalence_integrity")
            else:
                schematic_integrity = integrity.get("schematic")
                pcb_integrity = integrity.get("pcb")
                if not isinstance(schematic_integrity, dict):
                    errors.append("committed_equivalence_schematic_integrity")
                else:
                    approved_schematic_hash = str(
                        schematic_integrity.get("sha256_actual", "")
                    ).strip().lower()
                if not isinstance(pcb_integrity, dict):
                    errors.append("committed_equivalence_pcb_integrity")
                else:
                    approved_pcb_hash = str(
                        pcb_integrity.get("sha256_actual", "")
                    ).strip().lower()

            if (
                len(approved_schematic_hash) != 64
                or approved_schematic_hash != current_schematic_hash
            ):
                errors.append("equivalence_schematic_hash_mismatch")

            if len(approved_pcb_hash) != 64:
                errors.append("equivalence_pcb_baseline_hash")
            else:
                layout_evolved_since_equivalence = (
                    current_pcb_hash != approved_pcb_hash
                )
                if layout_evolved_since_equivalence:
                    warnings.append(
                        "pcb_layout_evolved_since_equivalence"
                    )

    if manifest_path.is_file():
        if layout_evolved_since_equivalence:
            # The equivalence gate intentionally binds the pre-routing PcbDoc.
            # Once layout authority is granted, routing changes PcbDoc by design.
            # Keep the committed electrical baseline and validate SchDoc continuity
            # instead of trying to replay the pre-routing PCB hash gate.
            rerun_gate = committed_gate
        else:
            try:
                rerun_gate = validate_equivalence(
                    manifest_path,
                    repository_root=root,
                )
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                errors.append(f"equivalence_rerun:{exc}")
            else:
                if rerun_gate.get("status") != "PASS":
                    errors.append(
                        "equivalence_rerun_status:"
                        + str(rerun_gate.get("status"))
                    )
                if rerun_gate.get("layout_authority") != "AUTHORIZED":
                    errors.append("equivalence_rerun_layout_authority")

                if (
                    committed_gate is not None
                    and committed_gate != rerun_gate
                ):
                    errors.append("equivalence_result_not_reproducible")

    if native_status_path.is_file():
        try:
            native_status = read_json(native_status_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"native_status_parse:{exc}")
        else:
            if native_status.get("native_import_status") not in {
                "IMPORTED",
                "PASS",
                "NATIVE_FILES_READY",
            }:
                errors.append("native_import_status")
            if native_status.get("equivalence_gate_status") != "PASS":
                errors.append("native_equivalence_status")
            if native_status.get("layout_authority") != "AUTHORIZED":
                errors.append("native_layout_authority")
            expected_production = (
                "AUTHORIZED"
                if production_released
                else "NOT_AUTHORIZED"
            )
            if native_status.get("production_authority") != expected_production:
                errors.append("native_production_authority")

            expected_pcb_tracking_hash = (
                current_pcb_hash
                if production_released
                else approved_pcb_hash
            )
            expected_hashes = {
                "native_schematic_sha256": current_schematic_hash,
                "native_pcb_sha256": expected_pcb_tracking_hash,
            }
            if committed_gate_path.is_file():
                expected_hashes["equivalence_result_sha256"] = (
                    sha256_file(committed_gate_path)
                )

            for field, expected in expected_hashes.items():
                if str(native_status.get(field, "")).lower() != expected:
                    errors.append(f"native_status_hash:{field}")

    if authority_path.is_file():
        try:
            authority = read_json(authority_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"cad_authority_parse:{exc}")
        else:
            if authority.get("native_document_status") != "NATIVE_EQUIVALENCE_PASS":
                errors.append("cad_authority_native_status")
            if authority.get("pcb_layout_authority") != "ALTIUM_AUTHORIZED":
                errors.append("cad_authority_layout_authority")
            if (
                authority.get("production_release_authorized")
                is not production_released
            ):
                errors.append("cad_authority_production_authority")
            if production_released:
                if authority.get("pcb_design_phase") != "PRODUCTION_RELEASED":
                    errors.append("cad_authority_design_phase")
            elif authority.get("pcb_design_phase") == "PRODUCTION_RELEASED":
                errors.append("cad_authority_design_phase")

            expected_pcb_tracking_hash = (
                current_pcb_hash
                if production_released
                else approved_pcb_hash
            )
            expected_hashes = {
                "native_schematic_sha256": current_schematic_hash,
                "native_pcb_sha256": expected_pcb_tracking_hash,
            }
            if committed_gate_path.is_file():
                expected_hashes["equivalence_result_sha256"] = (
                    sha256_file(committed_gate_path)
                )
            for field, expected in expected_hashes.items():
                if str(authority.get(field, "")).lower() != expected:
                    errors.append(f"cad_authority_hash:{field}")

            routing_authority = authority.get("routing_readiness_gate")
            if (
                not isinstance(routing_authority, dict)
                or routing_authority.get("current_expected_status")
                != "READY_FOR_ROUTING"
            ):
                errors.append("cad_authority_routing_status")

    if implementation_status_path.is_file():
        try:
            implementation_status = read_json(
                implementation_status_path
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"implementation_status_parse:{exc}")
        else:
            expected_phase = (
                "PRODUCTION_RELEASED"
                if production_released
                else "READY_FOR_ROUTING"
            )
            if implementation_status.get("current_phase") != expected_phase:
                errors.append("implementation_phase")
            altium = implementation_status.get("altium")
            if not isinstance(altium, dict):
                errors.append("implementation_altium")
            else:
                for field in (
                    "native_schdoc",
                    "native_pcbdoc",
                    "equivalence_gate",
                ):
                    if altium.get(field) is not True:
                        errors.append(f"implementation_{field}")
                if (
                    altium.get("production_release_authorized")
                    is not production_released
                ):
                    errors.append(
                        "implementation_production_release_authorized"
                    )
                if production_released:
                    for field in ("placement_started", "routing_started"):
                        if altium.get(field) is not True:
                            errors.append(f"implementation_{field}")
                expected_implementation_pcb_hash = (
                    current_pcb_hash
                    if production_released
                    else approved_pcb_hash
                )
                if (
                    str(altium.get("native_pcb_sha256", "")).lower()
                    != expected_implementation_pcb_hash
                ):
                    errors.append("implementation_native_pcb_sha256")

            readiness = implementation_status.get("routing_readiness")
            if not isinstance(readiness, dict):
                errors.append("implementation_routing_readiness")
            else:
                if readiness.get("expected_status") != "READY_FOR_ROUTING":
                    errors.append("implementation_expected_routing_status")
                if readiness.get("routing_authorized") is not True:
                    errors.append("implementation_routing_authorized")

    if routing is not None:
        if routing.get("status") != "READY_FOR_ROUTING":
            errors.append(
                "post_import_routing_status:"
                + str(routing.get("status"))
            )
        if routing.get("routing_authorized") is not True:
            errors.append("post_import_routing_authorized")
        if routing.get("production_authorized") is not production_released:
            errors.append("post_import_production_authorized")

    if production_released:
        if release_manifest_path.is_file():
            try:
                rerun_production = validate_production_release(
                    release_manifest_path,
                    repository_root=root,
                )
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                errors.append(f"production_rerun:{exc}")
            else:
                if rerun_production.get("status") != "PASS":
                    errors.append(
                        "production_rerun_status:"
                        + str(rerun_production.get("status"))
                    )
                if (
                    rerun_production.get("production_authority")
                    != "AUTHORIZED"
                ):
                    errors.append("production_rerun_authority")

        try:
            committed_production = read_json(production_result_path)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"production_result_parse:{exc}")
        else:
            if committed_production.get("status") != "PASS":
                errors.append("committed_production_not_pass")
            if (
                committed_production.get("production_authority")
                != "AUTHORIZED"
            ):
                errors.append("committed_production_authority")
            if (
                rerun_production is not None
                and committed_production != rerun_production
            ):
                errors.append("production_result_not_reproducible")

            result_hash = sha256_file(production_result_path)
            if isinstance(native_status, dict):
                if (
                    str(
                        native_status.get(
                            "production_release_result_sha256",
                            "",
                        )
                    ).lower()
                    != result_hash
                ):
                    errors.append(
                        "native_status_hash:production_release_result_sha256"
                    )
            if isinstance(authority, dict):
                if (
                    str(
                        authority.get(
                            "production_release_result_sha256",
                            "",
                        )
                    ).lower()
                    != result_hash
                ):
                    errors.append(
                        "cad_authority_hash:production_release_result_sha256"
                    )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "phase": phase,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "native_schdoc_present": True,
        "native_pcbdoc_present": True,
        "production_result_present": production_result_present,
        "approved_schematic_sha256": approved_schematic_hash,
        "approved_prerouting_pcb_sha256": approved_pcb_hash,
        "current_schematic_sha256": current_schematic_hash,
        "current_pcb_sha256": current_pcb_hash,
        "layout_evolved_since_equivalence": (
            layout_evolved_since_equivalence
        ),
        "handoff_status": handoff.get("status"),
        "routing_status": (
            routing.get("status")
            if isinstance(routing, dict)
            else None
        ),
        "equivalence_status": (
            rerun_gate.get("status")
            if isinstance(rerun_gate, dict)
            else None
        ),
        "production_release_status": (
            rerun_production.get("status")
            if isinstance(rerun_production, dict)
            else None
        ),
        "production_result_present": production_result_present,
        "production_result_pass": production_result_pass,
        "production_authority_surfaces": production_authority_surfaces,
        "routing_authorized": (
            status == "PASS"
            and (
                routing is None
                or routing.get("routing_authorized") is True
            )
        ),
        "production_authorized": (
            status == "PASS" and production_released
        ),
        "notes": [
            (
                "POST_EQUIVALENCE keeps the equivalence-approved SchDoc fixed. "
                "The PcbDoc may evolve after layout authority; the full pre-routing "
                "equivalence gate is replayed only while PcbDoc still matches its "
                "approved pre-routing hash."
            ),
            (
                "POST_PRODUCTION additionally requires a reproducible "
                "production-release PASS and synchronized production authority."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--generated-dir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(
        repository_root=args.repository_root,
        generated_dir=args.generated_dir,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"], result["phase"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
