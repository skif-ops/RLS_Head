from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


SCHEMA = "ALTIUM-CONNECTION-INTEGRITY-001"
RECEIPT_SCHEMA = "ALTIUM-CONNECTION-INTEGRITY-RECEIPT-001"
COPPER_LAYERS = {1, 2, 3, 32}
TEXT_EVIDENCE_SUFFIXES = {".csv", ".drc"}
AUDIT_FILES = (
    "component_bounds.csv",
    "pad_geometry.csv",
    "track_inventory.csv",
    "fill_inventory.csv",
    "via_inventory.csv",
    "connection_drc_report.drc",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_evidence_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_EVIDENCE_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _board_size(mechanical_path: Path) -> tuple[float, float]:
    rows = _read_csv(mechanical_path)
    outline = next(
        row
        for row in rows
        if row.get("kind") == "BOARD" and row.get("id") == "OUTLINE"
    )
    return float(outline["width_mm"]), float(outline["height_mm"])


def _drc_counts(path: Path) -> tuple[str, dict[str, int]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    pcb_match = re.search(r"^PCB File\s*:\s*(.+)$", text, re.MULTILINE)
    pcb_file = pcb_match.group(1).strip() if pcb_match else ""
    wanted = {
        "Un-Routed Net Constraint": "unrouted_net_violations",
        "Routing Topology Rule": "routing_topology_violations",
        "Net Antennae": "net_antennae_violations",
    }
    counts: dict[str, int] = {}
    active = ""
    for line in text.splitlines():
        if line.startswith("Processing Rule :"):
            active = line.split(":", 1)[1].strip()
            continue
        match = re.match(r"Rule Violations\s*:\s*(\d+)\s*$", line.strip())
        if not match:
            continue
        for prefix, key in wanted.items():
            if active.startswith(prefix):
                counts[key] = int(match.group(1))
                break
    return pcb_file, counts


def _relative_hashes(system: Path, paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(system).as_posix(): sha256_evidence_file(path)
        for path in paths
    }


def validate(
    system_root: str | Path,
    *,
    refresh_receipt: bool = False,
) -> dict:
    system = Path(system_root)
    altium = system / "altium"
    native_pcb = altium / "native" / "EVT_SYS_CARRIER.PcbDoc"
    audit_dir = altium / "routing" / "connection_audit"
    receipt_path = audit_dir / "connection_integrity_receipt.json"
    mechanical_path = altium / "ALTIUM_BOARD_MECHANICAL_SYS_001.csv"
    baseline_path = altium / "equivalence" / "pad_net_inventory.csv"

    if not native_pcb.is_file():
        return {
            "schema": SCHEMA,
            "status": "NOT_APPLICABLE",
            "reason": "native_pcb_not_present",
            "production_authority": "NOT_AUTHORIZED",
            "errors": [],
            "warnings": [],
        }

    errors: list[str] = []
    warnings: list[str] = []
    required_paths = [audit_dir / name for name in AUDIT_FILES]
    required_paths.extend([mechanical_path, baseline_path, native_pcb])
    missing = [path for path in required_paths if not path.is_file()]
    errors.extend(
        f"missing:{path.relative_to(system).as_posix()}" for path in missing
    )

    result = {
        "schema": SCHEMA,
        "status": "FAIL",
        "production_authority": "NOT_AUTHORIZED",
        "canonical_pcb_sha256": sha256_file(native_pcb),
        "board_width_mm": None,
        "board_height_mm": None,
        "counts": {},
        "outside_board_count": 0,
        "endpoint_baseline_matches": False,
        "baseline_shadow_pad_count": 0,
        "inferred_free_pad_count": 0,
        "free_pad_assignments": {},
        "unrouted_net_violations": None,
        "routing_topology_violations": None,
        "net_antennae_violations": None,
        "receipt_binding": "FAIL",
        "errors": errors,
        "warnings": warnings,
    }
    if missing:
        return result

    width_mm, height_mm = _board_size(mechanical_path)
    max_x = width_mm / 0.0254
    max_y = height_mm / 0.0254
    result["board_width_mm"] = width_mm
    result["board_height_mm"] = height_mm

    tables = {
        name.removesuffix(".csv"): _read_csv(audit_dir / name)
        for name in AUDIT_FILES
        if name.endswith(".csv")
    }
    result["counts"] = {
        "components": len(tables["component_bounds"]),
        "pads": len(tables["pad_geometry"]),
        "tracks": len(tables["track_inventory"]),
        "fills": len(tables["fill_inventory"]),
        "vias": len(tables["via_inventory"]),
    }

    outside: list[str] = []

    def check_bounds(kind: str, index: int, row: dict[str, str]) -> None:
        try:
            left = float(row["left_mil"])
            bottom = float(row["bottom_mil"])
            right = float(row["right_mil"])
            top = float(row["top_mil"])
        except (KeyError, ValueError):
            errors.append(f"invalid_bounds:{kind}:{index}")
            return
        tolerance = 0.01
        if (
            left < -tolerance
            or bottom < -tolerance
            or right > max_x + tolerance
            or top > max_y + tolerance
        ):
            outside.append(
                f"{kind}:{index}:{left:.3f},{bottom:.3f},"
                f"{right:.3f},{top:.3f}"
            )

    for index, row in enumerate(tables["component_bounds"], start=1):
        try:
            x = float(row["x_mil"])
            y = float(row["y_mil"])
        except (KeyError, ValueError):
            errors.append(f"invalid_component_origin:{index}")
            continue
        if x < 0 or y < 0 or x > max_x or y > max_y:
            outside.append(f"component_origin:{row.get('designator', index)}")
        try:
            left = float(row["left_mil"])
            bottom = float(row["bottom_mil"])
            right = float(row["right_mil"])
            top = float(row["top_mil"])
        except (KeyError, ValueError):
            errors.append(f"invalid_component_bounds:{index}")
            continue
        if left < 0 or bottom < 0 or right > max_x or top > max_y:
            warnings.append(
                f"component_courtyard_or_overlay_outside_board:"
                f"{row.get('designator', index)}"
            )

    for index, row in enumerate(tables["pad_geometry"], start=1):
        check_bounds("pad", index, row)

    for table_name in ("track_inventory", "fill_inventory"):
        singular = table_name.split("_", 1)[0]
        for index, row in enumerate(tables[table_name], start=1):
            try:
                is_copper = int(row["layer"]) in COPPER_LAYERS
            except (KeyError, ValueError):
                errors.append(f"invalid_layer:{singular}:{index}")
                continue
            if not is_copper:
                continue
            check_bounds(singular, index, row)
            if not row.get("net_name", "").strip():
                errors.append(f"unassigned_copper:{singular}:{index}")

    for index, row in enumerate(tables["via_inventory"], start=1):
        check_bounds("via", index, row)
        if not row.get("net_name", "").strip():
            errors.append(f"unassigned_copper:via:{index}")

    result["outside_board_count"] = len(outside)
    errors.extend(f"outside_board:{item}" for item in outside)

    baseline_rows = _read_csv(baseline_path)
    owned_pad_identities = {
        (row["pad_name"], row["net_name"])
        for row in baseline_rows
        if row.get("designator", "").strip()
    }

    def is_unowned_shadow(row: dict[str, str]) -> bool:
        return (
            not row.get("designator", "").strip()
            and (row["pad_name"], row["net_name"])
            in owned_pad_identities
        )

    shadow_rows = [
        row
        for row in baseline_rows
        if is_unowned_shadow(row)
    ]
    result["baseline_shadow_pad_count"] = len(shadow_rows)
    if shadow_rows:
        warnings.append(
            f"baseline_unowned_shadow_pads_ignored:{len(shadow_rows)}"
        )

    expected = Counter(
        (row["designator"], row["pad_name"], row["net_name"])
        for row in baseline_rows
        if not is_unowned_shadow(row)
    )
    actual_owned = Counter(
        (row["designator"], row["pad_name"], row["net_name"])
        for row in tables["pad_geometry"]
        if row.get("designator", "").strip()
    )
    extra_endpoints = actual_owned - expected
    remaining = expected - actual_owned
    component_origins = {
        row["designator"]: (float(row["x_mil"]), float(row["y_mil"]))
        for row in tables["component_bounds"]
        if row.get("designator", "").strip()
    }
    inferred = Counter()
    endpoint_errors: list[str] = []
    for index, row in enumerate(tables["pad_geometry"], start=1):
        if row.get("designator", "").strip():
            continue
        pad_name = row.get("pad_name", "")
        net_name = row.get("net_name", "")
        unowned_key = ("", pad_name, net_name)
        if remaining[unowned_key] > 0:
            remaining[unowned_key] -= 1
            continue
        candidates = sorted(
            {
                designator
                for designator, candidate_pad, candidate_net in remaining
                if candidate_pad == pad_name
                and candidate_net == net_name
                and designator
                and remaining[(designator, candidate_pad, candidate_net)] > 0
                and designator in component_origins
            }
        )
        if not candidates:
            endpoint_errors.append(f"free_pad_unmatched:{index}")
            continue
        try:
            pad_x = float(row["x_mil"])
            pad_y = float(row["y_mil"])
        except (KeyError, ValueError):
            endpoint_errors.append(f"free_pad_invalid_position:{index}")
            continue
        ranked = sorted(
            (
                (pad_x - component_origins[designator][0]) ** 2
                + (pad_y - component_origins[designator][1]) ** 2,
                designator,
            )
            for designator in candidates
        )
        distance_sq, owner = ranked[0]
        if distance_sq > 800.0**2:
            endpoint_errors.append(f"free_pad_owner_too_far:{index}")
            continue
        if len(ranked) > 1 and abs(ranked[1][0] - distance_sq) < 0.01:
            endpoint_errors.append(f"free_pad_owner_ambiguous:{index}")
            continue
        remaining[(owner, pad_name, net_name)] -= 1
        inferred[owner] += 1

    missing_endpoints = +remaining
    if missing_endpoints:
        errors.append(f"endpoint_baseline_missing:{sum(missing_endpoints.values())}")
    if extra_endpoints:
        errors.append(f"endpoint_baseline_extra:{sum(extra_endpoints.values())}")
    errors.extend(endpoint_errors)
    result["inferred_free_pad_count"] = sum(inferred.values())
    result["free_pad_assignments"] = dict(sorted(inferred.items()))
    result["endpoint_baseline_matches"] = not (
        missing_endpoints or extra_endpoints or endpoint_errors
    )

    drc_path = audit_dir / "connection_drc_report.drc"
    drc_pcb_file, drc_counts = _drc_counts(drc_path)
    drc_pcb_name = Path(drc_pcb_file.replace("\\", "/")).name.lower()
    if drc_pcb_name != "evt_sys_carrier.pcbdoc":
        errors.append("drc_not_canonical_pcb")
    for key in (
        "unrouted_net_violations",
        "routing_topology_violations",
        "net_antennae_violations",
    ):
        count = drc_counts.get(key)
        result[key] = count
        if count is None:
            errors.append(f"drc_rule_missing:{key}")
        elif count != 0:
            errors.append(f"drc_rule_nonzero:{key}:{count}")

    binding_paths = [native_pcb, mechanical_path, baseline_path]
    binding_paths.extend(audit_dir / name for name in AUDIT_FILES)
    evidence_hashes = _relative_hashes(system, binding_paths)
    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "production_authority": "NOT_AUTHORIZED",
        "evidence_sha256": evidence_hashes,
    }

    if refresh_receipt and not errors:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if not receipt_path.is_file():
        errors.append("missing:altium/routing/connection_audit/connection_integrity_receipt.json")
    else:
        try:
            committed_receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            committed_receipt = {}
            errors.append("receipt_parse")
        if committed_receipt != receipt_payload:
            errors.append("receipt_binding_mismatch")
        else:
            result["receipt_binding"] = "PASS"

    result["errors"] = sorted(set(errors))
    result["warnings"] = sorted(set(warnings))
    if not result["errors"]:
        result["status"] = "PASS"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate native Altium connection integrity evidence."
    )
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--refresh-receipt", action="store_true")
    args = parser.parse_args()

    result = validate(
        args.system_root,
        refresh_receipt=args.refresh_receipt,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
