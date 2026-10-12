from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEMA = "ANT-SIM-REAL-EXTERNAL-PREFLIGHT-001"


def _load_optional(
    path: str | Path,
    *,
    label: str,
    expected_schema: str,
) -> tuple[dict | None, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    source = Path(path)

    if not source.is_file():
        warnings.append(
            f"{label}:not_present_yet"
        )
        return None, errors, warnings

    try:
        data = json.loads(
            source.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        errors.append(
            f"{label}:invalid_json"
        )
        return None, errors, warnings

    if (
        data.get("schema")
        != expected_schema
    ):
        errors.append(
            f"{label}:unexpected_schema"
        )

    return data, errors, warnings


def evaluate_preflight(
    *,
    map_validation: str | Path,
    mc_summary: str | Path,
    revb: str | Path,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    validation, e, w = (
        _load_optional(
            map_validation,
            label="map_validation",
            expected_schema=(
                "ANT-D1-MAP-"
                "VALIDATION-001"
            ),
        )
    )
    errors.extend(e)
    warnings.extend(w)

    mc, e, w = _load_optional(
        mc_summary,
        label="mc_summary",
        expected_schema=(
            "ANT-D1-MC-SUMMARY-001"
        ),
    )
    errors.extend(e)
    warnings.extend(w)

    revb_data, e, w = (
        _load_optional(
            revb,
            label="revb",
            expected_schema=(
                "RAD-LB-006-REVB"
            ),
        )
    )
    errors.extend(e)
    warnings.extend(w)

    ready = {
        "map_validation":
            False,
        "mc_summary":
            False,
        "revb":
            False,
    }

    if validation is not None:
        status = str(
            validation.get(
                "status",
                "",
            )
        )
        if status == "DATA_READY":
            ready[
                "map_validation"
            ] = True
        elif status in {
            "FAIL",
            "INVALID",
        }:
            errors.append(
                "map_validation:not_ready"
            )
        else:
            warnings.append(
                "map_validation:waiting"
            )

    if mc is not None:
        status = str(
            mc.get(
                "status",
                "",
            )
        )
        if status == "PASS":
            ready[
                "mc_summary"
            ] = True
        elif status == "FAIL":
            errors.append(
                "mc_summary:fail"
            )
        else:
            warnings.append(
                "mc_summary:waiting"
            )

    if revb_data is not None:
        status = str(
            revb_data.get(
                "status",
                "",
            )
        )
        if status == "PROJECTED":
            ready[
                "revb"
            ] = True
        elif status in {
            "ANTENNA_UNUSABLE",
            "FAIL",
        }:
            errors.append(
                "revb:not_usable"
            )
        else:
            warnings.append(
                "revb:waiting"
            )

    if errors:
        status = "BLOCKED"
    elif all(
        ready.values()
    ):
        status = (
            "READY_FOR_GATE_ASSEMBLY"
        )
    else:
        status = (
            "WAITING_FOR_UPSTREAM"
        )

    return {
        "schema":
            SCHEMA,
        "status":
            status,
        "errors":
            sorted(
                set(errors)
            ),
        "warnings":
            sorted(
                set(warnings)
            ),
        "input_ready":
            ready,
        "notes": [
            (
                "READY_FOR_GATE_ASSEMBLY means the three simulation-evidence "
                "results are structurally ready for tools.ant_sim_gate."
            ),
            (
                "This preflight does not evaluate ANT-SIM-GATE-001 and does "
                "not imply physical antenna or field-range validation."
            ),
            (
                "No production Tx/Rx physical coordinates are encoded by "
                "this preflight."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight real ANT-SIM gate "
            "assembly inputs"
        )
    )
    parser.add_argument(
        "--validation",
        required=True,
    )
    parser.add_argument(
        "--mc",
        required=True,
    )
    parser.add_argument(
        "--revb",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = evaluate_preflight(
        map_validation=
            args.validation,
        mc_summary=
            args.mc,
        revb=
            args.revb,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        result["status"]
    )

    return (
        0
        if result["status"]
        in {
            "WAITING_FOR_UPSTREAM",
            "READY_FOR_GATE_ASSEMBLY",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
