from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-CONNECTOR-RESULT-001"


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


def validate(
    *,
    system_root: str | Path,
    pad_net_inventory: str | Path,
) -> dict:
    system = Path(system_root)
    inventory_path = Path(pad_net_inventory)
    logical_path = system / "CONNECTOR_PINOUT_SYS_001.csv"
    native_map_path = system / "CONNECTOR_NATIVE_PINMAP_SYS_001.csv"

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in (
        (inventory_path, "pad_net_inventory"),
        (logical_path, "connector_pinout_contract"),
        (native_map_path, "connector_native_map"),
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

    logical_rows = read_csv(logical_path)
    map_rows = read_csv(native_map_path)
    pad_rows = read_csv(inventory_path)

    logical: dict[tuple[str, str], dict[str, str]] = {}
    for row in logical_rows:
        key = (clean(row.get("connector")), clean(row.get("pin")))
        if key in logical:
            errors.append(
                f"duplicate_logical_connector_pin:{key[0]}:{key[1]}"
            )
        logical[key] = row

    mapped_logical = Counter()
    physical_keys: set[tuple[str, str]] = set()
    allowed_policies = {"CONNECT", "NC", "AGGREGATE"}

    for row in map_rows:
        connector = clean(row.get("connector"))
        logical_pin = clean(row.get("logical_pin"))
        logical_signal = clean(row.get("logical_signal"))
        ref = clean(row.get("physical_ref"))
        pad = clean(row.get("physical_pad"))
        policy = clean(row.get("policy"))
        key = (connector, logical_pin)

        source = logical.get(key)
        if source is None:
            errors.append(
                f"native_map_unknown_logical_pin:{connector}:{logical_pin}"
            )
        elif clean(source.get("signal")) != logical_signal:
            errors.append(
                "native_map_signal_mismatch:"
                f"{connector}:{logical_pin}:"
                f"{clean(source.get('signal'))}!={logical_signal}"
            )

        if not ref or not pad:
            errors.append(
                f"native_map_missing_physical_pin:{connector}:{logical_pin}"
            )
        physical_key = (ref, pad)
        if physical_key in physical_keys:
            errors.append(
                f"duplicate_physical_pin:{ref}:{pad}"
            )
        physical_keys.add(physical_key)

        if policy not in allowed_policies:
            errors.append(
                f"invalid_native_map_policy:{connector}:{logical_pin}:{policy}"
            )

        mapped_logical[key] += 1

    missing_logical = sorted(
        f"{connector}:{pin}"
        for connector, pin in logical
        if mapped_logical[(connector, pin)] == 0
    )
    if missing_logical:
        errors.append(
            "unmapped_logical_connector_pins:"
            + ",".join(missing_logical)
        )

    aggregate_counts = {
        key: count
        for key, count in mapped_logical.items()
        if count > 1
    }
    for key, count in aggregate_counts.items():
        policies = {
            clean(row.get("policy"))
            for row in map_rows
            if (
                clean(row.get("connector")),
                clean(row.get("logical_pin")),
            )
            == key
        }
        if policies != {"AGGREGATE"}:
            errors.append(
                f"nonaggregate_multi_map:{key[0]}:{key[1]}:{count}"
            )

    pad_map: dict[tuple[str, str], str] = {}
    for row in pad_rows:
        ref = clean(row.get("designator"))
        pad = clean(row.get("pad_name"))
        net = clean(row.get("net_name"))
        if ref and pad:
            pad_map[(ref, pad)] = net

    mismatches: list[str] = []
    checked = 0
    for row in map_rows:
        connector = clean(row.get("connector"))
        logical_pin = clean(row.get("logical_pin"))
        ref = clean(row.get("physical_ref"))
        pad = clean(row.get("physical_pad"))
        expected_net = clean(row.get("native_net"))
        policy = clean(row.get("policy"))
        actual_net = pad_map.get((ref, pad))

        if actual_net is None:
            mismatches.append(
                f"{connector}.{logical_pin}->{ref}.{pad}:MISSING_PAD"
            )
            continue

        checked += 1
        if policy == "NC":
            if actual_net:
                mismatches.append(
                    f"{connector}.{logical_pin}->{ref}.{pad}:NC!={actual_net}"
                )
        elif actual_net != expected_net:
            mismatches.append(
                f"{connector}.{logical_pin}->{ref}.{pad}:"
                f"{expected_net}!={actual_net or 'UNNAMED'}"
            )

    if mismatches:
        errors.append(
            "connector_pad_net_mismatch:"
            + ",".join(sorted(mismatches))
        )

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "logical_connector_pin_count": len(logical),
        "native_map_row_count": len(map_rows),
        "checked_native_pad_count": checked,
        "aggregate_logical_pin_count": len(aggregate_counts),
        "input_sha256": {
            "pad_net_inventory": sha256_file(inventory_path),
            "connector_pinout_contract": sha256_file(logical_path),
            "connector_native_map": sha256_file(native_map_path),
        },
        "verified_checks": {
            "connector_pinout_equivalence": status,
        },
        "notes": [
            (
                "The native mapping bridges logical harness connector names "
                "to actual System Carrier PCB designators and pad numbers."
            ),
            (
                "J_ETH MDI is an aggregate contract mapped to the four "
                "PHY-side MagJack pair pads."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--pad-net-inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        system_root=args.system_root,
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
