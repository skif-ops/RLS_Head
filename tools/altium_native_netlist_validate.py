from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-NETLIST-RESULT-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def clean(value: object) -> str:
    return str(value or "").strip()


def endpoint_map(
    rows: list[dict[str, str]],
    *,
    pin_field: str,
) -> tuple[dict[tuple[str, str], str], list[str]]:
    result: dict[tuple[str, str], str] = {}
    conflicts: list[str] = []
    for row in rows:
        ref = clean(row.get("designator"))
        pin = clean(row.get(pin_field))
        net = clean(row.get("net_name"))
        if not ref or not pin or not net:
            continue
        key = (ref, pin)
        previous = result.get(key)
        if previous is not None and previous != net:
            conflicts.append(
                f"{ref}.{pin}:{previous}|{net}"
            )
        result[key] = net
    return result, conflicts


def connectivity_groups(
    mapping: dict[tuple[str, str], str],
) -> set[tuple[str, ...]]:
    by_net: dict[str, list[str]] = defaultdict(list)
    for (ref, pin), net in mapping.items():
        by_net[net].append(f"{ref}.{pin}")
    return {
        tuple(sorted(endpoints))
        for endpoints in by_net.values()
        if endpoints
    }


def validate(
    *,
    baseline_csv: str | Path,
    pad_net_inventory: str | Path,
) -> dict:
    baseline_path = Path(baseline_csv)
    actual_path = Path(pad_net_inventory)
    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (baseline_path, "kicad_netlist_baseline"),
        (actual_path, "pad_net_inventory"),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "warnings": warnings,
        }

    baseline_rows = read_csv(baseline_path)
    actual_rows = read_csv(actual_path)

    baseline, baseline_conflicts = endpoint_map(
        baseline_rows,
        pin_field="pin",
    )
    actual_all, actual_conflicts = endpoint_map(
        actual_rows,
        pin_field="pad_name",
    )

    if baseline_conflicts:
        errors.append(
            "baseline_endpoint_conflict:"
            + ",".join(sorted(set(baseline_conflicts)))
        )
    if actual_conflicts:
        errors.append(
            "native_endpoint_conflict:"
            + ",".join(sorted(set(actual_conflicts)))
        )

    baseline_refs = {
        ref
        for ref, _pin in baseline
    }
    actual = {
        key: net
        for key, net in actual_all.items()
        if key[0] in baseline_refs
    }

    missing_endpoints = sorted(
        f"{ref}.{pin}"
        for ref, pin in set(baseline) - set(actual)
    )
    extra_endpoints = sorted(
        f"{ref}.{pin}"
        for ref, pin in set(actual) - set(baseline)
    )

    if missing_endpoints:
        errors.append(
            "missing_connected_endpoints:"
            + ",".join(missing_endpoints)
        )
    if extra_endpoints:
        errors.append(
            "extra_connected_endpoints:"
            + ",".join(extra_endpoints)
        )

    baseline_groups = connectivity_groups(baseline)
    actual_groups = connectivity_groups(actual)

    missing_groups = sorted(
        "|".join(group)
        for group in baseline_groups - actual_groups
    )
    extra_groups = sorted(
        "|".join(group)
        for group in actual_groups - baseline_groups
    )

    if missing_groups:
        errors.append(
            "missing_connectivity_groups:"
            + ",".join(missing_groups)
        )
    if extra_groups:
        errors.append(
            "extra_connectivity_groups:"
            + ",".join(extra_groups)
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "baseline_endpoint_count": len(baseline),
        "native_endpoint_count": len(actual),
        "baseline_connectivity_group_count": len(baseline_groups),
        "native_connectivity_group_count": len(actual_groups),
        "input_sha256": {
            "kicad_netlist_baseline": sha256_file(baseline_path),
            "pad_net_inventory": sha256_file(actual_path),
        },
        "verified_checks": {
            "netlist_equivalence": status,
        },
        "notes": [
            (
                "Connectivity is compared as endpoint partitions, so "
                "equivalence does not depend on internal net naming."
            ),
            (
                "Named P0/P1 net preservation remains independently "
                "checked by the native audit."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-csv", required=True)
    parser.add_argument("--pad-net-inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        baseline_csv=args.baseline_csv,
        pad_net_inventory=args.pad_net_inventory,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
