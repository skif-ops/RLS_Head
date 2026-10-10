from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.external_execution_recipe import build_recipes
from tools.m300_external_preflight import evaluate_preflight
from tools.measurement_pack import build_pack


SCHEMA = "EXTERNAL-EVIDENCE-JOB-PACK-001"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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

    checklist = [
        "Confirm target/range/geometry and measurement conditions before capture.",
        "Collect only real external measurements; do not use CI fixtures.",
        "Replace every <FILL...> placeholder before validation.",
    ]

    if preflight is not None:
        checklist.extend(
            [
                "Run the M300 preflight command from preflight_config.json before collection.",
                "Do not start qualification collection unless preflight status is READY_FOR_COLLECTION.",
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

    if (
        manifest.get("item_id") == "M300_MEASURED"
        and not errors
    ):
        try:
            run_manifest = json.loads(
                (
                    root
                    / "measurement_pack"
                    / "run_manifest.json"
                ).read_text(encoding="utf-8")
            )
            preflight_result = evaluate_preflight(
                run_manifest=run_manifest,
                range_csv=(
                    root
                    / "measurement_pack"
                    / "range_samples.csv"
                ),
            )
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
