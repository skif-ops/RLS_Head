from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "M300-EXTERNAL-PREFLIGHT-001"


def _filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and "<FILL" not in text
    return True


def evaluate_preflight(
    *,
    run_manifest: dict,
    range_csv: str | Path,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    if run_manifest.get("schema") != "EVM-RUN-MANIFEST-001":
        errors.append("manifest_schema")

    required_values = {
        "run_id": run_manifest.get("run_id"),
        "profile_id": run_manifest.get("profile_id"),
        "profile_config_sha256": run_manifest.get(
            "profile_config_sha256"
        ),
        "source_commit": run_manifest.get("source_commit"),
        "target_id": run_manifest.get("target_id"),
    }

    for name, value in required_values.items():
        if not _filled(value):
            errors.append(f"missing_or_placeholder:{name}")

    if run_manifest.get("mode") != "QUALIFY":
        errors.append("mode_not_qualify")

    try:
        range_m = float(run_manifest.get("range_nominal_m"))
    except (TypeError, ValueError):
        errors.append("range_nominal_m")
        range_m = None

    if range_m is not None and abs(range_m - 300.0) > 1.0e-6:
        errors.append("range_not_300m")

    try:
        rcs_m2 = float(run_manifest.get("rcs_m2"))
    except (TypeError, ValueError):
        errors.append("rcs_m2")
        rcs_m2 = None

    if rcs_m2 is not None and abs(rcs_m2 - 0.01) > 1.0e-9:
        errors.append("rcs_not_0p01m2")

    if run_manifest.get("truth_status") != "VALID":
        errors.append("truth_status_not_valid")

    if run_manifest.get("time_alignment_valid") is not True:
        errors.append("time_alignment_not_valid")

    if run_manifest.get("config_locked") is not True:
        errors.append("config_not_locked")

    if run_manifest.get("evidence_level") != "MEASURED_EVM":
        errors.append("evidence_level")

    if run_manifest.get("synthetic_fixture") is not False:
        errors.append("synthetic_fixture_not_false")

    start = run_manifest.get("start_time_us")
    end = run_manifest.get("end_time_us")

    try:
        start_i = int(start)
        end_i = int(end)
        if start_i <= 0 or end_i <= start_i:
            errors.append("invalid_time_window")
    except (TypeError, ValueError):
        errors.append("invalid_time_window")

    environment = run_manifest.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment_missing")
    else:
        if not _filled(environment.get("precipitation_state")):
            errors.append("precipitation_state")
        try:
            float(environment.get("temperature_c"))
        except (TypeError, ValueError):
            errors.append("temperature_c")

    csv_path = Path(range_csv)
    if not csv_path.is_file():
        errors.append("range_csv_missing")
    else:
        text = csv_path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        expected = (
            "range_m,detected,track_valid,fresh,detector_margin_db"
        )
        if first_line.strip() != expected:
            errors.append("range_csv_header")
        if "<FILL" in text:
            errors.append("range_csv_placeholder")
        if len(text.splitlines()) <= 1:
            warnings.append("range_csv_has_no_samples")

    files = run_manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest_files_not_list")

    status = "READY_FOR_COLLECTION" if not errors else "BLOCKED"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "checks": {
            "target_range_m": 300.0,
            "target_rcs_m2": 0.01,
            "qualify_mode_required": True,
            "truth_required": True,
            "time_alignment_required": True,
            "config_lock_required": True,
            "measured_evm_required": True,
        },
        "notes": [
            "READY_FOR_COLLECTION means the job is structurally ready to collect real data.",
            "It does not mean M300 has passed and does not create measured evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight an M300 external measurement job"
    )
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--range-csv", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(
        Path(args.run_manifest).read_text(encoding="utf-8")
    )
    result = evaluate_preflight(
        run_manifest=manifest,
        range_csv=args.range_csv,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "READY_FOR_COLLECTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
