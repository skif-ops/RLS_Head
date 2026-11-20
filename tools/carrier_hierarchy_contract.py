from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-HIERARCHY-CONTRACT-001"

EXPECTED_SHEETS = {
    "POWER_INPUT",
    "MCU_CORE",
    "TIME_GNSS",
    "IMU",
    "RADAR_IO_CAN",
    "HOST_UART",
    "DEBUG_BOOT",
}

PIN_TYPES = {
    "input",
    "output",
    "bidirectional",
    "passive",
}


def load_rows(
    path: str | Path,
) -> list[dict[str, str]]:
    with Path(path).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        required = {
            "sheet",
            "net_name",
            "pin_type",
            "anchor_ref",
            "anchor_pin",
            "criticality",
            "notes",
        }
        if (
            reader.fieldnames is None
            or not required.issubset(
                reader.fieldnames
            )
        ):
            raise ValueError(
                "hierarchy contract missing required columns"
            )
        return list(reader)


def validate_contract(
    path: str | Path,
) -> dict:
    rows = load_rows(path)
    errors: list[str] = []

    seen: set[tuple[str, str]] = set()
    nets: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)
    sheets = set()

    for index, row in enumerate(
        rows,
        start=2,
    ):
        sheet = str(
            row.get("sheet", "")
        ).strip()
        net = str(
            row.get("net_name", "")
        ).strip()
        pin_type = str(
            row.get("pin_type", "")
        ).strip()
        ref = str(
            row.get("anchor_ref", "")
        ).strip()
        pin = str(
            row.get("anchor_pin", "")
        ).strip()
        criticality = str(
            row.get("criticality", "")
        ).strip()

        if sheet not in EXPECTED_SHEETS:
            errors.append(
                f"invalid_sheet:{index}:{sheet}"
            )
        else:
            sheets.add(sheet)

        if not net:
            errors.append(
                f"missing_net:{index}"
            )

        if pin_type not in PIN_TYPES:
            errors.append(
                f"invalid_pin_type:{index}:{pin_type}"
            )

        if not ref or not pin:
            errors.append(
                f"missing_anchor:{index}"
            )

        if criticality not in {
            "P0",
            "P1",
            "P2",
        }:
            errors.append(
                f"invalid_criticality:{index}:{criticality}"
            )

        key = (sheet, net)
        if key in seen:
            errors.append(
                f"duplicate_sheet_net:{sheet}:{net}"
            )
        seen.add(key)
        nets[net].append(row)

    missing_sheets = sorted(
        EXPECTED_SHEETS - sheets
    )
    errors.extend(
        f"missing_sheet:{sheet}"
        for sheet in missing_sheets
    )

    for net, endpoints in nets.items():
        if len(endpoints) < 2:
            errors.append(
                f"single_endpoint_net:{net}"
            )

        types = {
            str(
                item.get(
                    "pin_type",
                    "",
                )
            ).strip()
            for item in endpoints
        }

        if types == {"input"}:
            errors.append(
                f"input_only_net:{net}"
            )

        output_count = sum(
            str(
                item.get(
                    "pin_type",
                    "",
                )
            ).strip()
            == "output"
            for item in endpoints
        )
        if output_count > 1:
            errors.append(
                f"multiple_outputs:{net}"
            )

    per_sheet = Counter(
        str(row["sheet"]).strip()
        for row in rows
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
        "row_count": len(rows),
        "net_count": len(nets),
        "sheet_count": len(sheets),
        "per_sheet": dict(
            sorted(per_sheet.items())
        ),
        "notes": [
            (
                "PASS validates the authoritative hierarchy interface "
                "contract only; CAD sheet-pin/HLabel realization is "
                "validated separately."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    result = validate_contract(
        args.csv
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
