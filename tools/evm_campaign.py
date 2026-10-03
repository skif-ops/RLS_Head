from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.evm_run_manifest import validate_run_manifest


REFERENCE_RANGES_M = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assemble_reference_campaign(
    manifests: list[tuple[str, dict]],
) -> dict:
    if not manifests:
        raise ValueError("at least one manifest is required")

    runs = []

    for path, manifest in manifests:
        validation = validate_run_manifest(manifest)

        runs.append(
            {
                "manifest_path": str(path),
                "run_id": validation["run_id"],
                "status": validation["status"],
                "profile_id": validation["profile_id"],
                "target_id": validation["target_id"],
                "range_nominal_m": validation["range_nominal_m"],
                "rcs_m2": validation["rcs_m2"],
                "evidence_level": validation["evidence_level"],
                "synthetic_fixture": validation["synthetic_fixture"],
                "errors": validation["errors"],
                "hold_reasons": validation["hold_reasons"],
                "file_kinds": validation["file_kinds"],
            }
        )

    run_ids = [run["run_id"] for run in runs]

    duplicate_run_ids = sorted(
        {
            run_id
            for run_id in run_ids
            if run_ids.count(run_id) > 1
        }
    )

    invalid_runs = [
        run["run_id"]
        for run in runs
        if run["status"] == "INVALID"
    ]

    hold_runs = [
        run["run_id"]
        for run in runs
        if run["status"] == "HOLD"
    ]

    measured_runs = [
        run
        for run in runs
        if run["status"] == "MEASURED_READY"
    ]

    test_runs = [
        run
        for run in runs
        if run["status"] == "TEST_READY"
    ]

    explore_runs = [
        run
        for run in runs
        if run["status"] == "EXPLORE_READY"
    ]

    measured_ranges = sorted(
        {
            float(run["range_nominal_m"])
            for run in measured_runs
            if run["range_nominal_m"] is not None
        }
    )

    test_ranges = sorted(
        {
            float(run["range_nominal_m"])
            for run in test_runs
            if run["range_nominal_m"] is not None
        }
    )

    missing_measured_ranges = [
        expected
        for expected in REFERENCE_RANGES_M
        if not any(
            math.isclose(
                actual,
                expected,
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
            for actual in measured_ranges
        )
    ]

    missing_test_ranges = [
        expected
        for expected in REFERENCE_RANGES_M
        if not any(
            math.isclose(
                actual,
                expected,
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
            for actual in test_ranges
        )
    ]

    measured_profiles = sorted(
        {run["profile_id"] for run in measured_runs}
    )
    measured_targets = sorted(
        {run["target_id"] for run in measured_runs}
    )

    test_profiles = sorted(
        {run["profile_id"] for run in test_runs}
    )
    test_targets = sorted(
        {run["target_id"] for run in test_runs}
    )

    reason_codes: list[str] = []

    if duplicate_run_ids:
        reason_codes.append("duplicate_run_ids")

    if invalid_runs:
        reason_codes.append("invalid_runs")

    if hold_runs:
        reason_codes.append("hold_runs")

    if measured_runs:
        if missing_measured_ranges:
            reason_codes.append("missing_measured_ranges")
        if len(measured_profiles) != 1:
            reason_codes.append("mixed_measured_profiles")
        if len(measured_targets) != 1:
            reason_codes.append("mixed_measured_targets")

    if duplicate_run_ids or invalid_runs:
        status = "INVALID"
    elif measured_runs:
        if (
            not missing_measured_ranges
            and len(measured_profiles) == 1
            and len(measured_targets) == 1
            and not hold_runs
        ):
            status = "MEASURED_READY"
        else:
            status = "INCOMPLETE"
    elif test_runs:
        if (
            not missing_test_ranges
            and len(test_profiles) == 1
            and len(test_targets) == 1
            and not hold_runs
            and not explore_runs
        ):
            status = "TEST_READY"
        else:
            status = "INCOMPLETE"
    else:
        status = "INCOMPLETE"

    return {
        "schema": "EVM-REFERENCE-CAMPAIGN-001",
        "status": status,
        "reason_codes": reason_codes,
        "expected_ranges_m": list(REFERENCE_RANGES_M),
        "measured_ranges_m": measured_ranges,
        "test_ranges_m": test_ranges,
        "missing_measured_ranges_m": missing_measured_ranges,
        "missing_test_ranges_m": missing_test_ranges,
        "measured_profile_ids": measured_profiles,
        "measured_target_ids": measured_targets,
        "test_profile_ids": test_profiles,
        "test_target_ids": test_targets,
        "invalid_runs": invalid_runs,
        "hold_runs": hold_runs,
        "explore_runs": [run["run_id"] for run in explore_runs],
        "runs": sorted(
            runs,
            key=lambda run: (
                float(run["range_nominal_m"])
                if run["range_nominal_m"] is not None
                else float("inf"),
                run["run_id"],
            ),
        ),
        "notes": [
            "TEST_READY never implies measured campaign readiness.",
            "MEASURED_READY requires all six reference ranges with one profile and one target.",
            "Run manifests remain the authoritative source for file hashes and truth/time validity.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble validated EVM reference-range campaign"
    )
    parser.add_argument(
        "--manifest",
        action="append",
        required=True,
        help="Path to EVM-RUN-MANIFEST-001; repeat for each run",
    )
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    manifests = [
        (path, load_json(path))
        for path in args.manifest
    ]

    result = assemble_reference_campaign(manifests)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] in {
        "TEST_READY",
        "MEASURED_READY",
        "INCOMPLETE",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
