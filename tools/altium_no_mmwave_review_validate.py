from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NO-MMWAVE-REVIEW-RESULT-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(
    *,
    review_json: str | Path,
    pcb_path: str | Path,
    component_inventory: str | Path,
    net_inventory: str | Path,
) -> dict:
    review_path = Path(review_json)
    pcb = Path(pcb_path)
    components = Path(component_inventory)
    nets = Path(net_inventory)

    errors: list[str] = []
    reasons: list[str] = []

    for path, label in (
        (review_path, "review"),
        (pcb, "pcb"),
        (components, "component_inventory"),
        (nets, "net_inventory"),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
            "reason_codes": reasons,
        }

    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"review_parse:{exc}"],
            "reason_codes": [],
        }

    if review.get("schema") != "ALTIUM-NO-MMWAVE-REVIEW-001":
        errors.append("review_schema")
    if review.get("status") != "PASS":
        reasons.append("REVIEW_NOT_PASS")

    reviewer = str(review.get("reviewer", "")).strip()
    if not reviewer or reviewer.startswith("<"):
        errors.append("reviewer")

    hashes = review.get("input_sha256")
    if not isinstance(hashes, dict):
        errors.append("input_sha256")
        hashes = {}

    actual_hashes = {
        "review": sha256_file(review_path),
        "pcb": sha256_file(pcb),
        "component_inventory": sha256_file(components),
        "net_inventory": sha256_file(nets),
    }
    for name, actual in actual_hashes.items():
        if str(hashes.get(name, "")).lower() != actual:
            errors.append(f"hash_mismatch:{name}")

    for field in (
        "no_76_81ghz_components",
        "no_76_81ghz_nets",
        "no_76_81ghz_routing",
        "no_76_81ghz_antenna",
    ):
        if review.get(field) is not True:
            reasons.append(field.upper())

    status = "PASS" if not errors and not reasons else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "reviewer": reviewer,
        "input_sha256": actual_hashes,
        "verified_checks": {
            "no_76_81GHz_rf_on_system_carrier": status,
        },
        "notes": [
            (
                "The review is deliberately human-signoff evidence bound "
                "to the exact native PcbDoc and machine inventories."
            ),
            (
                "This check does not infer the absence of unnetted antenna "
                "geometry from names; the routed-board visual/design review "
                "is mandatory."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-json", required=True)
    parser.add_argument("--pcb", required=True)
    parser.add_argument("--component-inventory", required=True)
    parser.add_argument("--net-inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        review_json=args.review_json,
        pcb_path=args.pcb,
        component_inventory=args.component_inventory,
        net_inventory=args.net_inventory,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
