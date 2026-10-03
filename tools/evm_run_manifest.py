from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")

MEASURED_LEVELS = {
    "MEASURED_EVM",
    "MEASURED_BENCH",
    "MEASURED_INTEGRATED",
    "MEASURED_FIELD",
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_nonempty_string(data: dict, key: str, errors: list[str]) -> str:
    value = data.get(key)

    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing_or_invalid:{key}")
        return ""

    return value.strip()


def validate_run_manifest(manifest: dict) -> dict:
    if manifest.get("schema") != "EVM-RUN-MANIFEST-001":
        raise ValueError("unexpected EVM run manifest schema")

    errors: list[str] = []
    holds: list[str] = []

    run_id = _require_nonempty_string(manifest, "run_id", errors)
    mode = _require_nonempty_string(manifest, "mode", errors)
    profile_id = _require_nonempty_string(manifest, "profile_id", errors)
    target_id = _require_nonempty_string(manifest, "target_id", errors)
    evidence_level = _require_nonempty_string(
        manifest,
        "evidence_level",
        errors,
    )

    if mode not in {"EXPLORE", "QUALIFY"}:
        errors.append("invalid_mode")

    profile_hash = str(manifest.get("profile_config_sha256", ""))

    if not SHA256_RE.fullmatch(profile_hash):
        errors.append("invalid_profile_config_sha256")

    source_commit = str(manifest.get("source_commit", ""))

    if not SHA1_RE.fullmatch(source_commit):
        errors.append("invalid_source_commit")

    try:
        start_time_us = int(manifest["start_time_us"])
        end_time_us = int(manifest["end_time_us"])
    except (KeyError, TypeError, ValueError):
        errors.append("invalid_time_bounds")
        start_time_us = 0
        end_time_us = 0

    if start_time_us < 0 or end_time_us <= start_time_us:
        errors.append("invalid_time_bounds")

    try:
        range_nominal_m = float(manifest["range_nominal_m"])
        rcs_m2 = float(manifest["rcs_m2"])
    except (KeyError, TypeError, ValueError):
        errors.append("invalid_range_or_rcs")
        range_nominal_m = math.nan
        rcs_m2 = math.nan

    if (
        not math.isfinite(range_nominal_m)
        or range_nominal_m <= 0.0
        or not math.isfinite(rcs_m2)
        or rcs_m2 <= 0.0
    ):
        errors.append("invalid_range_or_rcs")

    truth_status = str(manifest.get("truth_status", ""))
    time_alignment_valid = manifest.get("time_alignment_valid")
    config_locked = manifest.get("config_locked")
    synthetic_fixture = bool(manifest.get("synthetic_fixture", False))
    raw_capture_enabled = bool(manifest.get("raw_capture_enabled", False))

    if truth_status not in {"VALID", "INVALID", "PARTIAL"}:
        errors.append("invalid_truth_status")

    if not isinstance(time_alignment_valid, bool):
        errors.append("invalid_time_alignment_flag")

    if not isinstance(config_locked, bool):
        errors.append("invalid_config_locked_flag")

    if synthetic_fixture and evidence_level in MEASURED_LEVELS:
        errors.append("synthetic_marked_measured")

    environment = manifest.get("environment")

    if not isinstance(environment, dict):
        errors.append("missing_environment")
    else:
        try:
            temperature_c = float(environment["temperature_c"])
        except (KeyError, TypeError, ValueError):
            errors.append("invalid_environment_temperature")
        else:
            if not math.isfinite(temperature_c):
                errors.append("invalid_environment_temperature")

        precipitation_state = environment.get("precipitation_state")

        if not isinstance(precipitation_state, str) or not precipitation_state.strip():
            errors.append("invalid_precipitation_state")

    files = manifest.get("files")

    if not isinstance(files, list) or not files:
        errors.append("missing_files")
        files = []

    seen_paths = set()
    kinds = set()

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"invalid_file_entry:{index}")
            continue

        path = item.get("path")
        sha256 = item.get("sha256")
        kind = item.get("kind")

        if not isinstance(path, str) or not path.strip():
            errors.append(f"invalid_file_path:{index}")
        elif path in seen_paths:
            errors.append(f"duplicate_file_path:{path}")
        else:
            seen_paths.add(path)

        if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
            errors.append(f"invalid_file_sha256:{index}")

        if not isinstance(kind, str) or not kind.strip():
            errors.append(f"invalid_file_kind:{index}")
        else:
            kinds.add(kind.strip())

    for required_kind in {"truth", "radar", "diagnostics"}:
        if required_kind not in kinds:
            errors.append(f"missing_file_kind:{required_kind}")

    if raw_capture_enabled and "raw_capture" not in kinds:
        errors.append("raw_capture_enabled_without_file")

    if mode == "QUALIFY":
        if config_locked is not True:
            holds.append("qualification_config_not_locked")

        if truth_status != "VALID":
            holds.append("qualification_truth_not_valid")

        if time_alignment_valid is not True:
            holds.append("qualification_time_alignment_not_valid")

    if errors:
        status = "INVALID"
    elif synthetic_fixture:
        status = "TEST_READY"
    elif mode == "QUALIFY" and evidence_level not in MEASURED_LEVELS:
        status = "HOLD"
        holds.append("qualification_not_measured")
    elif holds:
        status = "HOLD"
    elif evidence_level in MEASURED_LEVELS:
        status = "MEASURED_READY"
    else:
        status = "EXPLORE_READY"

    return {
        "schema": "EVM-RUN-VALIDATION-001",
        "status": status,
        "run_id": run_id,
        "mode": mode,
        "profile_id": profile_id,
        "target_id": target_id,
        "evidence_level": evidence_level,
        "synthetic_fixture": synthetic_fixture,
        "errors": errors,
        "hold_reasons": holds,
        "file_kinds": sorted(kinds),
        "range_nominal_m": (
            range_nominal_m if math.isfinite(range_nominal_m) else None
        ),
        "rcs_m2": rcs_m2 if math.isfinite(rcs_m2) else None,
    }


def validate_reference_ladder(manifests: list[dict]) -> dict:
    expected_ranges = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0)

    validations = [
        validate_run_manifest(manifest)
        for manifest in manifests
    ]

    run_ids = [result["run_id"] for result in validations]

    duplicate_run_ids = sorted(
        {
            run_id
            for run_id in run_ids
            if run_ids.count(run_id) > 1
        }
    )

    measured_ready = [
        result
        for result in validations
        if result["status"] == "MEASURED_READY"
    ]

    measured_ranges = sorted(
        {
            float(result["range_nominal_m"])
            for result in measured_ready
            if result["range_nominal_m"] is not None
        }
    )

    missing_ranges = [
        range_m
        for range_m in expected_ranges
        if not any(
            math.isclose(
                measured,
                range_m,
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
            for measured in measured_ranges
        )
    ]

    common_profile_ids = sorted(
        {
            result["profile_id"]
            for result in measured_ready
        }
    )

    common_target_ids = sorted(
        {
            result["target_id"]
            for result in measured_ready
        }
    )

    reason_codes = []

    if duplicate_run_ids:
        reason_codes.append("duplicate_run_ids")

    if missing_ranges:
        reason_codes.append("missing_measured_ranges")

    if len(common_profile_ids) > 1:
        reason_codes.append("mixed_profiles")

    if len(common_target_ids) > 1:
        reason_codes.append("mixed_targets")

    status = "DATA_READY" if not reason_codes else "INCOMPLETE"

    return {
        "schema": "EVM-REFERENCE-LADDER-VALIDATION-001",
        "status": status,
        "reason_codes": reason_codes,
        "expected_ranges_m": list(expected_ranges),
        "measured_ranges_m": measured_ranges,
        "missing_ranges_m": missing_ranges,
        "duplicate_run_ids": duplicate_run_ids,
        "profile_ids": common_profile_ids,
        "target_ids": common_target_ids,
        "runs": validations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one EVM run manifest"
    )
    parser.add_argument("manifest")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = validate_run_manifest(load_json(args.manifest))

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {
        "TEST_READY",
        "EXPLORE_READY",
        "MEASURED_READY",
        "HOLD",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
