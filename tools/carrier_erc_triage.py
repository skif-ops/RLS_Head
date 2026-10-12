from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


SCHEMA = "SYSTEM-CARRIER-ERC-TRIAGE-001"
REF_RE = re.compile(r"\b([A-Z][A-Z0-9_]*\d+)\b")


def _load(path: str | Path) -> dict:
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def _extract_ref(item: dict) -> str | None:
    description = str(item.get("description", ""))
    match = REF_RE.search(description)
    return match.group(1) if match else None


def build_triage(
    erc: dict,
    *,
    baseline: dict | None = None,
) -> dict:
    sheets = erc.get("sheets")
    if not isinstance(sheets, list):
        raise ValueError("KiCad ERC JSON must contain sheets[]")

    by_severity = collections.Counter()
    by_type = collections.Counter()
    by_sheet = collections.Counter()
    by_ref = collections.Counter()
    sheet_type = collections.Counter()

    for sheet in sheets:
        if not isinstance(sheet, dict):
            raise ValueError("invalid ERC sheet entry")

        sheet_name = str(sheet.get("path", ""))
        violations = sheet.get("violations", [])
        if not isinstance(violations, list):
            raise ValueError("ERC sheet violations must be a list")

        for violation in violations:
            if not isinstance(violation, dict):
                raise ValueError("invalid ERC violation entry")

            severity = str(violation.get("severity", "")).lower()
            kind = str(violation.get("type", ""))

            by_severity[severity] += 1
            by_type[kind] += 1
            by_sheet[sheet_name] += 1
            sheet_type[(sheet_name, kind)] += 1

            for item in violation.get("items", []):
                if not isinstance(item, dict):
                    continue
                ref = _extract_ref(item)
                if ref:
                    by_ref[ref] += 1

    total = sum(by_severity.values())

    result = {
        "schema": SCHEMA,
        "status": "READY",
        "source_kicad_version": str(
            erc.get("kicad_version", "")
        ),
        "total_violations": total,
        "by_severity": dict(
            sorted(by_severity.items())
        ),
        "by_type": dict(
            by_type.most_common()
        ),
        "by_sheet": dict(
            by_sheet.most_common()
        ),
        "by_ref": dict(
            by_ref.most_common()
        ),
        "sheet_type": [
            {
                "sheet": sheet,
                "type": kind,
                "count": count,
            }
            for (sheet, kind), count
            in sorted(
                sheet_type.items(),
                key=lambda item: (
                    -item[1],
                    item[0][0],
                    item[0][1],
                ),
            )
        ],
        "delta": None,
        "notes": [
            (
                "This report is diagnostic only. "
                "It does not waive or suppress ERC findings."
            ),
        ],
    }

    if baseline is not None:
        base = build_triage(
            baseline,
            baseline=None,
        )
        all_types = set(base["by_type"]) | set(result["by_type"])
        all_sheets = set(base["by_sheet"]) | set(result["by_sheet"])

        result["delta"] = {
            "total": (
                result["total_violations"]
                - base["total_violations"]
            ),
            "by_type": {
                key: (
                    result["by_type"].get(key, 0)
                    - base["by_type"].get(key, 0)
                )
                for key in sorted(all_types)
            },
            "by_sheet": {
                key: (
                    result["by_sheet"].get(key, 0)
                    - base["by_sheet"].get(key, 0)
                )
                for key in sorted(all_sheets)
            },
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize System Carrier KiCad ERC findings"
    )
    parser.add_argument("erc_json")
    parser.add_argument("--baseline")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = build_triage(
        _load(args.erc_json),
        baseline=(
            _load(args.baseline)
            if args.baseline
            else None
        ),
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["total_violations"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
