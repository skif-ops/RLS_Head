from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_equivalence_gate import validate_manifest as validate_equivalence
from tools.altium_native_handoff_status import evaluate as evaluate_handoff
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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

    phase = "POST_EQUIVALENCE"

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

    for label, path in (
        ("manifest", manifest_path),
        ("equivalence_result", committed_gate_path),
        ("native_status", native_status_path),
        ("implementation_status", implementation_status_path),
        ("cad_authority", authority_path),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    rerun_gate = None
    committed_gate = None
    native_status = None
    implementation_status = None
    authority = None

    if manifest_path.is_file():
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
            if (
                rerun_gate is not None
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
            if native_status.get("production_authority") != "NOT_AUTHORIZED":
                errors.append("native_production_authority")

            expected_hashes = {
                "native_schematic_sha256": sha256_file(schdoc),
                "native_pcb_sha256": sha256_file(pcbdoc),
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
            if authority.get("production_release_authorized") is not False:
                errors.append("cad_authority_production_authority")

            expected_hashes = {
                "native_schematic_sha256": sha256_file(schdoc),
                "native_pcb_sha256": sha256_file(pcbdoc),
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
            if implementation_status.get("current_phase") != "READY_FOR_ROUTING":
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
                if altium.get("production_release_authorized") is not False:
                    errors.append(
                        "implementation_production_release_authorized"
                    )
                if (
                    str(altium.get("native_pcb_sha256", "")).lower()
                    != sha256_file(pcbdoc)
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

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "phase": phase,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "native_schdoc_present": True,
        "native_pcbdoc_present": True,
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
        "routing_authorized": (
            status == "PASS"
            and (
                routing is None
                or routing.get("routing_authorized") is True
            )
        ),
        "production_authorized": False,
        "notes": [
            (
                "POST_EQUIVALENCE PASS requires reproducible equivalence PASS, "
                "synchronized tracked status and READY_FOR_ROUTING."
            ),
            (
                "This CI gate never grants production authority."
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
