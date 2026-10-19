from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_production_release_gate import (
    validate_manifest as validate_release_gate,
)
from tools.altium_production_release_manifest import build_manifest
from tools.altium_production_release_status import evaluate as evaluate_release_status


SCHEMA = "ALTIUM-PRODUCTION-TRANSITION-001"

SYSTEM_REL = Path("hardware/system_carrier")
ALTIUM_REL = SYSTEM_REL / "altium"
RELEASE_REL = ALTIUM_REL / "release"

PATHS = {
    "native_pcb": ALTIUM_REL / "native" / "EVT_SYS_CARRIER.PcbDoc",
    "native_status": ALTIUM_REL / "ALTIUM_NATIVE_STATUS_SYS_001.json",
    "implementation_status": ALTIUM_REL / "ALTIUM_STATUS_SYS_001.json",
    "cad_authority": SYSTEM_REL / "CAD_AUTHORITY_SYS_001.json",
    "manifest_template": RELEASE_REL / "manifest.template.json",
    "manifest": RELEASE_REL / "manifest.json",
    "release_status": RELEASE_REL / "production_release_status.json",
    "release_result": RELEASE_REL / "production_release_result.json",
}


def _absolute(root: Path, key: str) -> Path:
    return root / PATHS[key]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sync_production_authority(
    root: Path,
    release_result: dict,
) -> None:
    if (
        release_result.get("status") != "PASS"
        or release_result.get("production_authority") != "AUTHORIZED"
    ):
        raise ValueError("cannot synchronize production status without release PASS")

    native_status_path = _absolute(root, "native_status")
    implementation_status_path = _absolute(root, "implementation_status")
    authority_path = _absolute(root, "cad_authority")
    result_path = _absolute(root, "release_result")
    pcb_path = _absolute(root, "native_pcb")

    native_status = _read_json(native_status_path)
    implementation = _read_json(implementation_status_path)
    authority = _read_json(authority_path)

    result_hash = _sha256_file(result_path)
    pcb_hash = _sha256_file(pcb_path)

    gate_pcb_hash = str(
        release_result.get("native_pcb_sha256", "")
    ).strip().lower()
    if (
        len(gate_pcb_hash) != 64
        or gate_pcb_hash != pcb_hash
    ):
        raise ValueError(
            "final native PcbDoc changed after production gate PASS"
        )

    native_status["production_authority"] = "AUTHORIZED"
    native_status["production_release_result"] = (
        PATHS["release_result"].as_posix()
    )
    native_status["production_release_result_sha256"] = result_hash
    native_status["native_pcb_sha256"] = pcb_hash
    native_status["production_release_source_pcb_sha256"] = gate_pcb_hash

    altium = implementation.setdefault("altium", {})
    altium["native_schdoc"] = True
    altium["native_pcbdoc"] = True
    altium["equivalence_gate"] = True
    altium["placement_started"] = True
    altium["routing_started"] = True
    altium["production_release_authorized"] = True
    altium["native_pcb_sha256"] = pcb_hash
    altium["production_release_source_pcb_sha256"] = gate_pcb_hash

    implementation["current_phase"] = "PRODUCTION_RELEASED"
    implementation["next_required_phase"] = "NONE"
    implementation["blockers"] = []

    routing = implementation.setdefault("routing_readiness", {})
    routing["expected_status"] = "READY_FOR_ROUTING"
    routing["routing_authorized"] = True
    routing["required_to_authorize"] = []

    authority["native_document_status"] = "NATIVE_EQUIVALENCE_PASS"
    authority["pcb_layout_authority"] = "ALTIUM_AUTHORIZED"
    authority["pcb_design_phase"] = "PRODUCTION_RELEASED"
    authority["production_release_authorized"] = True
    authority["native_pcb_sha256"] = pcb_hash
    authority["production_release_source_pcb_sha256"] = gate_pcb_hash
    authority["production_release_result"] = (
        PATHS["release_result"].as_posix()
    )
    authority["production_release_result_sha256"] = result_hash
    routing_authority = authority.setdefault("routing_readiness_gate", {})
    routing_authority["current_expected_status"] = "READY_FOR_ROUTING"

    _write_json(native_status_path, native_status)
    _write_json(implementation_status_path, implementation)
    _write_json(authority_path, authority)


def run_transition(
    *,
    repository_root: str | Path = ".",
    synchronize_status: bool = True,
) -> dict:
    root = Path(repository_root)
    generated: list[str] = []
    stage_results: dict[str, dict] = {}

    status = evaluate_release_status(root)
    stage_results["release_status_initial"] = status

    if status.get("status") == "WAITING_RELEASE_MANIFEST":
        manifest_build = build_manifest(
            template_path=_absolute(root, "manifest_template"),
            repository_root=root,
        )
        stage_results["manifest_builder"] = manifest_build
        if manifest_build.get("status") != "READY":
            return {
                "schema": SCHEMA,
                "status": "BLOCKED_RELEASE_MANIFEST",
                "next_action": "FIX_RELEASE_MANIFEST_INPUTS",
                "generated_artifacts": generated,
                "stage_results": stage_results,
                "errors": manifest_build.get("errors", []),
                "production_authorized": False,
            }

        _write_json(
            _absolute(root, "manifest"),
            manifest_build["manifest"],
        )
        generated.append(PATHS["manifest"].as_posix())

        status = evaluate_release_status(root)
        stage_results["release_status_after_manifest"] = status

    _write_json(_absolute(root, "release_status"), status)
    generated.append(PATHS["release_status"].as_posix())

    if status.get("status") != "READY_TO_RUN_PRODUCTION_RELEASE_GATE":
        return {
            "schema": SCHEMA,
            "status": status.get(
                "status",
                "BLOCKED_PRODUCTION_RELEASE_HANDOFF",
            ),
            "next_action": status.get(
                "next_action",
                "FIX_PRODUCTION_RELEASE_HANDOFF",
            ),
            "generated_artifacts": generated,
            "stage_results": stage_results,
            "errors": (
                list(status.get("invalid_artifacts", []))
                + list(status.get("non_pass_artifacts", []))
                + list(status.get("manifest_errors", []))
            ),
            "missing_inputs": status.get("missing_artifacts", []),
            "production_authorized": False,
        }

    gate = validate_release_gate(
        _absolute(root, "manifest"),
        repository_root=root,
    )
    _write_json(_absolute(root, "release_result"), gate)
    generated.append(PATHS["release_result"].as_posix())
    stage_results["production_release_gate"] = gate

    if gate.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "BLOCKED_PRODUCTION_RELEASE_GATE",
            "next_action": "FIX_PRODUCTION_RELEASE_GATE_FINDINGS",
            "generated_artifacts": generated,
            "stage_results": stage_results,
            "errors": (
                list(gate.get("errors", []))
                + list(gate.get("reason_codes", []))
            ),
            "production_authorized": False,
        }

    if synchronize_status:
        try:
            _sync_production_authority(root, gate)
        except (
            FileNotFoundError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            return {
                "schema": SCHEMA,
                "status": "PASS_STATUS_SYNC_FAILED",
                "next_action": "FIX_TRACKED_PRODUCTION_STATUS_SYNC",
                "generated_artifacts": generated,
                "stage_results": stage_results,
                "errors": [f"status_sync:{exc}"],
                "production_authorized": True,
            }
        generated.extend(
            [
                PATHS["native_status"].as_posix(),
                PATHS["implementation_status"].as_posix(),
                PATHS["cad_authority"].as_posix(),
            ]
        )

    return {
        "schema": SCHEMA,
        "status": "PRODUCTION_RELEASED",
        "next_action": "RELEASE_NATIVE_ALTIUM_MANUFACTURING_PACKAGE",
        "generated_artifacts": generated,
        "stage_results": stage_results,
        "errors": [],
        "production_authorized": True,
        "notes": [
            (
                "Production authority is synchronized only after a real "
                "ALTIUM_PRODUCTION_RELEASE_GATE PASS."
            ),
            (
                "The release gate remains SHA-256-bound to one final native PcbDoc."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--no-status-sync",
        action="store_true",
        help="Do not update tracked production authority JSON after gate PASS.",
    )
    parser.add_argument(
        "--output",
        default=(
            "hardware/system_carrier/altium/release/"
            "production_transition_result.json"
        ),
    )
    args = parser.parse_args()

    result = run_transition(
        repository_root=args.repository_root,
        synchronize_status=not args.no_status_sync,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(args.repository_root) / output
    _write_json(output, result)

    print(result["status"])
    return 0 if result["status"] == "PRODUCTION_RELEASED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
