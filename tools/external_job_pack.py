from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.ant_d1_em_external_preflight import (
    evaluate_preflight as evaluate_ant_d1_em_preflight,
)
from tools.carrier_review_a_external_preflight import (
    evaluate_preflight as evaluate_carrier_review_a_preflight,
)
from tools.evm_profile_external_preflight import (
    evaluate_preflight as evaluate_evm_profile_preflight,
)
from tools.external_execution_recipe import build_recipes
from tools.hil_r2_external_preflight import (
    evaluate_preflight as evaluate_hil_r2_preflight,
)
from tools.m300_external_preflight import (
    evaluate_preflight as evaluate_m300_preflight,
)
from tools.measurement_pack import build_pack
from tools.reference_range_external_preflight import (
    evaluate_preflight as evaluate_reference_range_preflight,
)


SCHEMA = "EXTERNAL-EVIDENCE-JOB-PACK-001"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _repo_text(relative: str) -> str:
    path = (
        Path(__file__).resolve().parents[1]
        / relative
    )
    return path.read_text(encoding="utf-8")


def _load_evm_profile_gate_config() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "evm_profile_gate_evt.json"
    )
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def _load_d1_map_validation_config() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "d1_map_validation_evt.json"
    )
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def _load_hil_r2_gate_config() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "hil_r2_evidence_evt.json"
    )
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def build_job_pack(
    queue: dict,
    output_dir: str | Path,
    *,
    priority: int = 1,
) -> dict:
    if priority <= 0:
        raise ValueError("priority must be >= 1")

    recipes = build_recipes(queue)

    ready = [
        row
        for row in recipes["recipes"]
        if row.get("status") == "READY"
    ]

    selected = next(
        (
            row
            for row in ready
            if int(row.get("priority", 0)) == priority
        ),
        None,
    )

    if selected is None:
        raise ValueError(
            f"no READY execution recipe at priority {priority}"
        )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []

    selected = dict(selected)

    if selected["item_id"] == "ANT_D1_EM_REAL":
        selected["validator_command"] = (
            "python -m tools.ant_em_evidence "
            "--manifest em_package/d1_em_manifest.json "
            "--map-config d1_map_validation_config.json "
            "--repository-root . "
            "--output result.json"
        )

    elif selected["item_id"] == "CARRIER_REVIEW_A":
        selected["validator_command"] = (
            "python -m tools.carrier_review_a "
            "carrier_package/carrier_review_a_manifest.json "
            "--repository-root . "
            "--output result.json"
        )

    elif selected["item_id"] == "AWR_EVM_PROFILE_MEASURED":
        selected["validator_command"] = (
            "python -m tools.evm_profile_gate "
            "--metrics measurement_pack/profile_metrics.csv "
            "--manifest measurement_pack/run_manifests/TRACK.json "
            "--manifest measurement_pack/run_manifests/LR1.json "
            "--manifest measurement_pack/run_manifests/LR2.json "
            "--manifest measurement_pack/run_manifests/LRX.json "
            "--config evm_profile_gate_config.json "
            "--output result.json"
        )

    recipe_path = root / "execution_recipe.json"
    _write_json(recipe_path, selected)
    generated.append(recipe_path.name)

    pack_kind = selected.get("pack_kind")
    measurement_pack = None
    preflight = None

    if pack_kind:
        measurement_dir = root / "measurement_pack"
        measurement_pack = build_pack(
            str(pack_kind),
            measurement_dir,
        )
        for path in sorted(measurement_dir.rglob("*")):
            if path.is_file():
                generated.append(
                    str(path.relative_to(root))
                )

    if selected["item_id"] == "M300_MEASURED":
        preflight = {
            "schema": "M300-JOB-PACK-PREFLIGHT-001",
            "run_manifest": "measurement_pack/run_manifest.json",
            "range_csv": "measurement_pack/range_samples.csv",
            "output": "m300_preflight_result.json",
            "command": (
                "python -m tools.m300_external_preflight "
                "--run-manifest measurement_pack/run_manifest.json "
                "--range-csv measurement_pack/range_samples.csv "
                "--output m300_preflight_result.json"
            ),
            "expected_ready_status": "READY_FOR_COLLECTION",
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append("preflight_config.json")

    elif selected["item_id"] == "HIL_R2_BENCH_MEASURED":
        gate_config = _load_hil_r2_gate_config()
        _write_json(
            root / "hil_r2_gate_config.json",
            gate_config,
        )
        generated.append("hil_r2_gate_config.json")

        preflight = {
            "schema": "HIL-R2-JOB-PACK-PREFLIGHT-001",
            "timing_csv": "measurement_pack/timing_capture.csv",
            "gate_config": "hil_r2_gate_config.json",
            "output": "hil_r2_preflight_result.json",
            "command": (
                "python -m tools.hil_r2_external_preflight "
                "--timing-csv measurement_pack/timing_capture.csv "
                "--config hil_r2_gate_config.json "
                "--output hil_r2_preflight_result.json"
            ),
            "expected_ready_status": "READY_FOR_COLLECTION",
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append("preflight_config.json")

    elif selected["item_id"] == "REFERENCE_RANGE_MEASURED":
        manifest_dir = (
            root
            / "measurement_pack"
            / "run_manifests"
        )
        manifest_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        readme = manifest_dir / "README.txt"
        readme.write_text(
            (
                "Place one completed EVM-RUN-MANIFEST-001 JSON file here "
                "for each required range: 50, 100, 150, 200, 250, 300 m.\n"
            ),
            encoding="utf-8",
        )
        generated.append(
            str(readme.relative_to(root))
        )

        preflight = {
            "schema": "REFERENCE-RANGE-JOB-PACK-PREFLIGHT-001",
            "reference_csv": "measurement_pack/reference_range.csv",
            "manifest_dir": "measurement_pack/run_manifests",
            "output": "reference_range_preflight_result.json",
            "command": (
                "python -m tools.reference_range_external_preflight "
                "--reference-csv measurement_pack/reference_range.csv "
                "--manifest-dir measurement_pack/run_manifests "
                "--output reference_range_preflight_result.json"
            ),
            "expected_ready_status": "READY_FOR_COLLECTION",
            "required_ranges_m": [
                50,
                100,
                150,
                200,
                250,
                300,
            ],
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append("preflight_config.json")

    elif selected["item_id"] == "ANT_D1_EM_REAL":
        package = root / "em_package"
        model_dir = package / "model"
        output_dir_em = package / "output"
        model_dir.mkdir(parents=True, exist_ok=True)
        output_dir_em.mkdir(parents=True, exist_ok=True)

        manifest_template = {
            "schema": "ANT-D1-EM-MANIFEST-001",
            "model_id": "<FILL_MODEL_ID>",
            "model_revision": "<FILL_MODEL_REVISION>",
            "solver_name": "<FILL_SOLVER_NAME>",
            "solver_version": "<FILL_SOLVER_VERSION>",
            "synthetic_fixture": False,
            "evidence_level": "SIMULATED_EM",
            "artifacts": [
                {
                    "kind": "model_input",
                    "path": "em_package/model/model_input.dat",
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "kind": "material_definition",
                    "path": "em_package/model/material_definition.json",
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "kind": "solver_export",
                    "path": "em_package/output/solver_export.dat",
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "kind": "antenna_map",
                    "path": "em_package/output/antenna_map.csv",
                    "sha256": "<FILL_SHA256>",
                },
            ],
        }
        _write_json(
            package / "d1_em_manifest.json",
            manifest_template,
        )
        generated.append(
            "em_package/d1_em_manifest.json"
        )

        (model_dir / "README.txt").write_text(
            (
                "Place the real solver model input and material definition "
                "files here using the paths declared in d1_em_manifest.json.\n"
            ),
            encoding="utf-8",
        )
        generated.append(
            "em_package/model/README.txt"
        )

        (output_dir_em / "README.txt").write_text(
            (
                "After external EM execution, place the raw solver export "
                "and machine-readable antenna map here.\n"
            ),
            encoding="utf-8",
        )
        generated.append(
            "em_package/output/README.txt"
        )

        map_config = _load_d1_map_validation_config()
        _write_json(
            root / "d1_map_validation_config.json",
            map_config,
        )
        generated.append(
            "d1_map_validation_config.json"
        )

        preflight = {
            "schema": "ANT-D1-EM-JOB-PACK-PREFLIGHT-001",
            "manifest": "em_package/d1_em_manifest.json",
            "repository_root": ".",
            "output": "ant_d1_em_preflight_result.json",
            "command": (
                "python -m tools.ant_d1_em_external_preflight "
                "--manifest em_package/d1_em_manifest.json "
                "--repository-root . "
                "--output ant_d1_em_preflight_result.json"
            ),
            "expected_ready_status": "READY_FOR_SOLVER_EXECUTION",
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append("preflight_config.json")

    elif selected["item_id"] == "CARRIER_REVIEW_A":
        package = root / "carrier_package"
        inputs_dir = package / "inputs"
        output_dir_carrier = package / "output"
        inputs_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_dir_carrier.mkdir(
            parents=True,
            exist_ok=True,
        )

        pinmap_path = inputs_dir / "pinmap.csv"
        pinmap_path.write_text(
            _repo_text(
                "hardware/system_carrier/PINMAP_SYS_001.csv"
            ),
            encoding="utf-8",
        )
        generated.append(
            "carrier_package/inputs/pinmap.csv"
        )

        bom_path = inputs_dir / "bom.csv"
        bom_path.write_text(
            _repo_text(
                "hardware/system_carrier/BOM_SYS_CARRIER_002.csv"
            ),
            encoding="utf-8",
        )
        generated.append(
            "carrier_package/inputs/bom.csv"
        )

        manifest_template = {
            "schema": "CARRIER-REVIEW-A-MANIFEST-001",
            "board_id": "EVT-SYS-CARRIER",
            "hardware_revision": "A",
            "cad_tool": "KiCad",
            "cad_version": "<FILL_CAD_VERSION>",
            "synthetic_fixture": False,
            "evidence_level": "CAD_REVIEW",
            "erc_policy": {
                "errors_allowed": 0,
                "warnings_allowed": 0,
            },
            "artifacts": [
                {
                    "id": "schematic",
                    "path": (
                        "carrier_package/output/"
                        "system_carrier.kicad_sch"
                    ),
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "id": "erc_json",
                    "path": (
                        "carrier_package/output/"
                        "erc.json"
                    ),
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "id": "pinmap",
                    "path": (
                        "carrier_package/inputs/"
                        "pinmap.csv"
                    ),
                    "sha256": "<FILL_SHA256>",
                },
                {
                    "id": "bom",
                    "path": (
                        "carrier_package/inputs/"
                        "bom.csv"
                    ),
                    "sha256": "<FILL_SHA256>",
                },
            ],
            "audits": {
                "power": "PENDING",
                "clock": "PENDING",
                "reset_boot": "PENDING",
                "timing_capture": "PENDING",
                "imu": "PENDING",
                "ethernet": "PENDING",
                "can_fd": "PENDING",
            },
        }
        _write_json(
            package
            / "carrier_review_a_manifest.json",
            manifest_template,
        )
        generated.append(
            "carrier_package/"
            "carrier_review_a_manifest.json"
        )

        (
            output_dir_carrier
            / "README.txt"
        ).write_text(
            (
                "Place the captured KiCad schematic and ERC JSON "
                "here using the manifest paths.\n"
            ),
            encoding="utf-8",
        )
        generated.append(
            "carrier_package/output/README.txt"
        )

        preflight = {
            "schema": (
                "CARRIER-REVIEW-A-JOB-PACK-"
                "PREFLIGHT-001"
            ),
            "manifest": (
                "carrier_package/"
                "carrier_review_a_manifest.json"
            ),
            "repository_root": ".",
            "output": (
                "carrier_review_a_preflight_result.json"
            ),
            "command": (
                "python -m "
                "tools.carrier_review_a_external_preflight "
                "--manifest carrier_package/"
                "carrier_review_a_manifest.json "
                "--repository-root . "
                "--output "
                "carrier_review_a_preflight_result.json"
            ),
            "expected_ready_status": (
                "READY_FOR_CAD_REVIEW_EXECUTION"
            ),
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append("preflight_config.json")

    elif selected["item_id"] == "AWR_EVM_PROFILE_MEASURED":
        manifest_dir = (
            root
            / "measurement_pack"
            / "run_manifests"
        )
        manifest_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        readme = manifest_dir / "README.txt"
        readme.write_text(
            (
                "Place completed EVM-RUN-MANIFEST-001 files here using "
                "canonical names TRACK.json, LR1.json, LR2.json, LRX.json.\n"
            ),
            encoding="utf-8",
        )
        generated.append(
            str(readme.relative_to(root))
        )

        profile_gate_config = (
            _load_evm_profile_gate_config()
        )
        _write_json(
            root
            / "evm_profile_gate_config.json",
            profile_gate_config,
        )
        generated.append(
            "evm_profile_gate_config.json"
        )

        preflight = {
            "schema": (
                "EVM-PROFILE-JOB-PACK-"
                "PREFLIGHT-001"
            ),
            "metrics": (
                "measurement_pack/"
                "profile_metrics.csv"
            ),
            "manifest_dir": (
                "measurement_pack/"
                "run_manifests"
            ),
            "output": (
                "evm_profile_preflight_result.json"
            ),
            "command": (
                "python -m "
                "tools.evm_profile_external_preflight "
                "--metrics measurement_pack/"
                "profile_metrics.csv "
                "--manifest-dir measurement_pack/"
                "run_manifests "
                "--output "
                "evm_profile_preflight_result.json"
            ),
            "expected_ready_status": (
                "READY_FOR_COLLECTION"
            ),
            "required_profiles": [
                "TRACK",
                "LR1",
                "LR2",
                "LRX",
            ],
        }
        _write_json(
            root / "preflight_config.json",
            preflight,
        )
        generated.append(
            "preflight_config.json"
        )

    checklist = [
        "Confirm target/range/geometry and measurement conditions before capture.",
        "Collect only real external measurements; do not use CI fixtures.",
        "Replace every <FILL...> placeholder before validation.",
    ]

    if preflight is not None:
        checklist.extend(
            [
                "Run the preflight command from preflight_config.json before external execution or collection.",
                "Do not start the external step unless preflight reports its expected ready status.",
            ]
        )

    checklist.extend(
        [
            "Compute hashes only after collection is complete.",
            "Run the domain validator command from execution_recipe.json.",
            "Build EXTERNAL-EVIDENCE-BUNDLE-001 from the result and source artifacts.",
            "Run tools.external_evidence_ingest.",
            "Run tools.evidence_promotion_pipeline.",
            "Review the candidate manifest before any repository merge.",
        ]
    )

    (root / "EXECUTION_CHECKLIST.txt").write_text(
        "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(checklist, start=1)
        )
        + "\n",
        encoding="utf-8",
    )
    generated.append("EXECUTION_CHECKLIST.txt")

    manifest = {
        "schema": SCHEMA,
        "item_id": selected["item_id"],
        "priority": selected["priority"],
        "next_action": selected.get("next_action"),
        "directly_unlocks": selected.get(
            "directly_unlocks", 0
        ),
        "pack_kind": pack_kind,
        "result_schema": selected.get(
            "result_schema"
        ),
        "validator_command": selected.get(
            "validator_command"
        ),
        "collect": selected.get("collect", []),
        "generated_files": sorted(generated),
        "template_only": True,
        "measurement_pack_manifest": measurement_pack,
        "preflight": preflight,
        "notes": [
            "This job pack is execution scaffolding only.",
            "No generated file counts as measured evidence.",
            "Real measurements and validator outputs are required before promotion.",
        ],
    }

    _write_json(
        root / "job_manifest.json",
        manifest,
    )
    manifest["generated_files"] = sorted(
        manifest["generated_files"]
        + ["job_manifest.json"]
    )
    _write_json(
        root / "job_manifest.json",
        manifest,
    )

    return manifest


def validate_job_pack(path: str | Path) -> dict:
    root = Path(path)
    manifest_path = root / "job_manifest.json"

    if not manifest_path.is_file():
        return {
            "schema": "EXTERNAL-EVIDENCE-JOB-PACK-VALIDATION-001",
            "status": "INVALID",
            "errors": ["missing_job_manifest"],
        }

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    errors: list[str] = []

    if manifest.get("schema") != SCHEMA:
        errors.append("schema")

    if manifest.get("template_only") is not True:
        errors.append("template_only")

    files = manifest.get("generated_files")
    if not isinstance(files, list) or not files:
        errors.append("generated_files")
        files = []

    for name in files:
        if not (root / name).is_file():
            errors.append(f"missing_file:{name}")

    if not str(
        manifest.get("validator_command", "")
    ).strip():
        errors.append("validator_command")

    if not str(
        manifest.get("result_schema", "")
    ).strip():
        errors.append("result_schema")

    preflight_status = None
    preflight_errors: list[str] = []
    preflight_warnings: list[str] = []

    if not errors:
        try:
            if manifest.get("item_id") == "M300_MEASURED":
                run_manifest = json.loads(
                    (
                        root
                        / "measurement_pack"
                        / "run_manifest.json"
                    ).read_text(encoding="utf-8")
                )
                preflight_result = evaluate_m300_preflight(
                    run_manifest=run_manifest,
                    range_csv=(
                        root
                        / "measurement_pack"
                        / "range_samples.csv"
                    ),
                )

            elif manifest.get("item_id") == "HIL_R2_BENCH_MEASURED":
                gate_config = json.loads(
                    (
                        root
                        / "hil_r2_gate_config.json"
                    ).read_text(encoding="utf-8")
                )
                preflight_result = evaluate_hil_r2_preflight(
                    timing_csv=(
                        root
                        / "measurement_pack"
                        / "timing_capture.csv"
                    ),
                    gate_config=gate_config,
                )

            elif manifest.get("item_id") == "REFERENCE_RANGE_MEASURED":
                preflight_result = evaluate_reference_range_preflight(
                    reference_csv=(
                        root
                        / "measurement_pack"
                        / "reference_range.csv"
                    ),
                    manifest_dir=(
                        root
                        / "measurement_pack"
                        / "run_manifests"
                    ),
                )

            elif manifest.get("item_id") == "ANT_D1_EM_REAL":
                em_manifest = json.loads(
                    (
                        root
                        / "em_package"
                        / "d1_em_manifest.json"
                    ).read_text(encoding="utf-8")
                )
                preflight_result = evaluate_ant_d1_em_preflight(
                    manifest=em_manifest,
                    repository_root=root,
                )

            elif manifest.get("item_id") == "CARRIER_REVIEW_A":
                carrier_manifest = json.loads(
                    (
                        root
                        / "carrier_package"
                        / "carrier_review_a_manifest.json"
                    ).read_text(encoding="utf-8")
                )
                preflight_result = evaluate_carrier_review_a_preflight(
                    manifest=carrier_manifest,
                    repository_root=root,
                )

            elif manifest.get("item_id") == "AWR_EVM_PROFILE_MEASURED":
                preflight_result = evaluate_evm_profile_preflight(
                    metrics_csv=(
                        root
                        / "measurement_pack"
                        / "profile_metrics.csv"
                    ),
                    manifest_dir=(
                        root
                        / "measurement_pack"
                        / "run_manifests"
                    ),
                )

            else:
                preflight_result = None

            if preflight_result is not None:
                preflight_status = preflight_result["status"]
                preflight_errors = preflight_result["errors"]
                preflight_warnings = preflight_result["warnings"]

        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
        ):
            preflight_status = "BLOCKED"
            preflight_errors = [
                "preflight_execution_error"
            ]

    return {
        "schema": "EXTERNAL-EVIDENCE-JOB-PACK-VALIDATION-001",
        "status": "TEMPLATE_READY" if not errors else "INVALID",
        "errors": sorted(set(errors)),
        "item_id": manifest.get("item_id"),
        "priority": manifest.get("priority"),
        "pack_kind": manifest.get("pack_kind"),
        "preflight_status": preflight_status,
        "preflight_errors": sorted(
            set(preflight_errors)
        ),
        "preflight_warnings": sorted(
            set(preflight_warnings)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or validate an external evidence execution job pack"
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build = sub.add_parser("build")
    build.add_argument("queue")
    build.add_argument("--output-dir", required=True)
    build.add_argument("--priority", type=int, default=1)

    validate = sub.add_parser("validate")
    validate.add_argument("path")

    args = parser.parse_args()

    if args.command == "build":
        queue = json.loads(
            Path(args.queue).read_text(
                encoding="utf-8"
            )
        )
        result = build_job_pack(
            queue,
            args.output_dir,
            priority=args.priority,
        )
        print(result["item_id"])
        return 0

    result = validate_job_pack(args.path)
    print(result["status"])
    return 0 if result["status"] == "TEMPLATE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
