from __future__ import annotations

import argparse
import json
from pathlib import Path

import kicad_sch_api as ksa


SCHEMA = "SYSTEM-CARRIER-HIERARCHY-CAD-001"


def validate(
    root_path: str | Path,
) -> dict:
    root_path = Path(root_path)
    schematic = ksa.load_schematic(
        str(root_path)
    )

    schematic.hierarchy.build_hierarchy_tree(
        schematic,
        root_path,
    )

    connections = (
        schematic.hierarchy
        .validate_sheet_pins()
    )
    validation_errors = (
        schematic.hierarchy
        .get_validation_errors()
    )

    failed = [
        connection
        for connection in connections
        if not bool(
            getattr(
                connection,
                "validated",
                False,
            )
        )
    ]

    errors: list[str] = []

    for item in validation_errors:
        if isinstance(item, dict):
            pin_name = str(
                item.get(
                    "pin_name",
                    "",
                )
            )
            error = str(
                item.get(
                    "error",
                    "",
                )
            )
            errors.append(
                f"{pin_name}:{error}"
            )
        else:
            errors.append(
                str(item)
            )

    for item in failed:
        errors.append(
            "unvalidated:"
            + str(
                getattr(
                    item,
                    "sheet_pin_name",
                    "",
                )
            )
        )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS"
            if not errors
            else "FAIL"
        ),
        "errors": sorted(
            set(errors)
        ),
        "connection_count":
            len(connections),
        "validated_connection_count":
            len(connections)
            - len(failed),
        "notes": [
            (
                "PASS means every generated root sheet pin has a "
                "matching compatible hierarchical label in its child "
                "sheet."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root_schematic",
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = validate(
        args.root_schematic
    )
    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])
    return (
        0
        if result["status"] == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
