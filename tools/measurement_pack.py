from __future__ import annotations

import argparse
import json
from pathlib import Path


PACK_SCHEMA = "MEASUREMENT-EXECUTION-PACK-001"

PACKS = {
    "m300": {
        "item_id": "M300_MEASURED",
        "evidence_level": "MEASURED_EVM",
        "result_schema": "M300-REPORT-001",
        "files": {
            "run_manifest.json": {
                "schema": "EVM-RUN-MANIFEST-001",
                "run_id": "<FILL>",
                "mode": "QUALIFY",
                "profile_id": "<FILL>",
                "profile_config_sha256": "<FILL_SHA256>",
                "source_commit": "<FILL_SHA1>",
                "target_id": "<FILL>",
                "range_nominal_m": 300.0,
                "rcs_m2": 0.01,
                "start_time_us": 0,
                "end_time_us": 0,
                "truth_status": "VALID",
                "time_alignment_valid": True,
                "config_locked": True,
                "evidence_level": "MEASURED_EVM",
                "synthetic_fixture": False,
                "raw_capture_enabled": False,
                "environment": {
                    "temperature_c": 0.0,
                    "precipitation_state": "<FILL>",
                },
                "files": [],
            },
            "range_samples.csv": (
                "range_m,detected,track_valid,fresh,detector_margin_db\n"
            ),
        },
    },
    "reference_range": {
        "item_id": "REFERENCE_RANGE_MEASURED",
        "evidence_level": "MEASURED_EVM",
        "result_schema": "REFERENCE-RANGE-RESULT-001",
        "files": {
            "reference_range.csv": (
                "run_id,range_m,signal_db,detector_margin_db,detected,track_valid\n"
            ),
            "README_RANGES.txt": (
                "Required ranges: 50,100,150,200,250,300 m\n"
                "Use one validated EVM-RUN-MANIFEST-001 per range.\n"
            ),
        },
    },
    "hil_r2_bench": {
        "item_id": "HIL_R2_BENCH_MEASURED",
        "evidence_level": "MEASURED_BENCH",
        "result_schema": "HIL-R2-BENCH-EVIDENCE-001",
        "files": {
            "timing_capture.csv": "kind,value_us,count\n",
        },
    },
    "sys_err": {
        "item_id": "SYS_ERR_MEASURED",
        "evidence_level": "MEASURED_BENCH",
        "result_schema": "SYS-ERR-GATE-001",
        "files": {
            "sys_err_manifest.json": {
                "schema": "SYS-ERR-MEASUREMENT-MANIFEST-001",
                "synthetic_fixture": False,
                "evidence_level": "MEASURED_BENCH",
                "timing_evidence": {
                    "path": "<FILL>",
                    "sha256": "<FILL_SHA256>",
                },
                "cells_csv": {
                    "path": "sys_err_cells.csv",
                    "sha256": "<FILL_SHA256>",
                },
            },
            "sys_err_cells.csv": (
                "cell_id,range_m,sigma_range_m,sigma_az_deg,sigma_el_deg,"
                "host_attitude_sigma_deg,extrinsic_sigma_deg,angular_rate_deg_s\n"
            ),
        },
    },
    "physical_antenna": {
        "item_id": "PHYSICAL_ANT_MEASUREMENT",
        "evidence_level": "MEASURED_EM",
        "result_schema": "ANT-MEASUREMENT-001",
        "files": {
            "antenna_measurement_manifest.json": {
                "schema": "ANT-MEASUREMENT-MANIFEST-001",
                "measurement_id": "<FILL>",
                "synthetic_fixture": False,
                "evidence_level": "MEASURED_EM",
                "instrument_id": "<FILL>",
                "calibration_id": "<FILL>",
                "measurement_csv": {
                    "path": "antenna_measurement.csv",
                    "sha256": "<FILL_SHA256>",
                },
            },
            "antenna_measurement.csv": (
                "measurement_id,frequency_hz,az_deg,el_deg,realized_gain_db,"
                "gain_uncertainty_db,sigma_az_deg,sigma_el_deg,ambiguity_flag,"
                "track_usable,high_acc_usable,repeat_count\n"
            ),
        },
    },
    "evm_profile": {
        "item_id": "AWR_EVM_PROFILE_MEASURED",
        "evidence_level": "MEASURED_EVM",
        "result_schema": "EVM-PROFILE-RESULT-001",
        "files": {
            "profile_metrics.csv": (
                "run_id,profile_id,profile_class,range_m,rcs_m2,dynamics_class,"
                "fov_class,pd,track_availability,fresh_fraction,margin_db,"
                "sigma_az_deg,sigma_el_deg,update_hz,radar_latency_p99_ms,"
                "compute_util_p99_pct,ram_peak_pct,overrun_count,"
                "deadline_miss_count,edma_error_count,angle_status\n"
            ),
            "README_PROFILES.txt": (
                "Provide validated EVM-RUN-MANIFEST-001 files for TRACK/LR1/LR2/LRX.\n"
            ),
        },
    },
}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_pack(kind: str, output_dir: str | Path) -> dict:
    if kind not in PACKS:
        raise ValueError(f"unsupported pack kind: {kind}")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    spec = PACKS[kind]

    generated = []

    for name, payload in spec["files"].items():
        path = output / name

        if isinstance(payload, dict):
            _write_json(path, payload)
        else:
            path.write_text(str(payload), encoding="utf-8")

        generated.append(name)

    claim = {
        "schema": "MEASURED-EVIDENCE-CLAIM-001",
        "item_id": spec["item_id"],
        "result": {
            "path": "<FILL_RESULT_PATH>",
            "sha256": "<FILL_RESULT_SHA256>",
            "schema": spec["result_schema"],
        },
        "provenance": {
            "evidence_level": spec["evidence_level"],
            "synthetic": False,
            "artifacts": [],
        },
    }

    _write_json(
        output / "evidence_claim.template.json",
        claim,
    )
    generated.append("evidence_claim.template.json")

    pack_manifest = {
        "schema": PACK_SCHEMA,
        "kind": kind,
        "item_id": spec["item_id"],
        "required_evidence_level": spec["evidence_level"],
        "result_schema": spec["result_schema"],
        "generated_files": sorted(generated),
        "template_only": True,
        "notes": [
            "Replace all <FILL...> placeholders before use.",
            "Compute SHA-256 after data collection; do not pre-populate hashes.",
            "Run the domain validator before evidence promotion.",
            "A generated pack is not measurement evidence.",
        ],
    }

    _write_json(
        output / "pack_manifest.json",
        pack_manifest,
    )

    (output / "README.md").write_text(
        (
            f"# {kind} measurement execution pack\n\n"
            "This directory is a template only. It does not prove any measured result.\n\n"
            "Workflow:\n"
            "1. collect data;\n"
            "2. fill manifests and CSVs;\n"
            "3. compute hashes;\n"
            "4. run the domain validator;\n"
            "5. create the result JSON;\n"
            "6. fill evidence_claim.template.json;\n"
            "7. run tools.evidence_promote;\n"
            "8. review the candidate project manifest before merge.\n"
        ),
        encoding="utf-8",
    )

    pack_manifest["generated_files"] = sorted(
        pack_manifest["generated_files"] + [
            "pack_manifest.json",
            "README.md",
        ]
    )

    _write_json(
        output / "pack_manifest.json",
        pack_manifest,
    )

    return pack_manifest


def validate_pack(path: str | Path) -> dict:
    root = Path(path)
    manifest_path = root / "pack_manifest.json"

    if not manifest_path.is_file():
        return {
            "schema": "MEASUREMENT-EXECUTION-PACK-VALIDATION-001",
            "status": "INVALID",
            "errors": ["missing_pack_manifest"],
        }

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    errors = []

    if manifest.get("schema") != PACK_SCHEMA:
        errors.append("schema")

    if manifest.get("kind") not in PACKS:
        errors.append("kind")

    if manifest.get("template_only") is not True:
        errors.append("template_only")

    files = manifest.get("generated_files")

    if not isinstance(files, list) or not files:
        errors.append("generated_files")
        files = []

    missing = [
        name
        for name in files
        if not (root / name).is_file()
    ]

    errors.extend(
        f"missing_file:{name}"
        for name in missing
    )

    placeholders = []

    for name in files:
        file_path = root / name

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in {
            ".json",
            ".csv",
            ".txt",
            ".md",
        }:
            continue

        text = file_path.read_text(encoding="utf-8")

        if "<FILL" in text:
            placeholders.append(name)

    return {
        "schema": "MEASUREMENT-EXECUTION-PACK-VALIDATION-001",
        "status": "TEMPLATE_READY" if not errors else "INVALID",
        "errors": errors,
        "kind": manifest.get("kind"),
        "item_id": manifest.get("item_id"),
        "placeholder_files": sorted(placeholders),
        "generated_files": sorted(files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or validate measurement execution packs"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("--kind", required=True, choices=sorted(PACKS))
    generate.add_argument("--output-dir", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("path")

    args = parser.parse_args()

    if args.command == "generate":
        result = build_pack(args.kind, args.output_dir)
        print(result["kind"])
        return 0

    result = validate_pack(args.path)
    print(result["status"])
    return 0 if result["status"] == "TEMPLATE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
