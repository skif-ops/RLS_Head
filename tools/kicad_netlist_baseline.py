from __future__ import annotations

import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


SCHEMA = "KICAD-NETLIST-BASELINE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def physical_refs(system_root: Path) -> set[str]:
    path = system_root / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        str(row.get("ref", "")).strip()
        for row in rows
        if str(row.get("ref", "")).strip()
    }


def open_pin_contract(system_root: Path) -> set[tuple[str, str]]:
    path = system_root / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {
            (str(row["ref"]).strip(), str(row["pin_number"]).strip())
            for row in rows
            if str(row["connection"]).strip().startswith(("OPEN", "NC"))
        }


def build(
    *,
    system_root: str | Path,
    xml_netlist: str | Path,
    output_csv: str | Path,
) -> dict:
    system = Path(system_root)
    xml_path = Path(xml_netlist)
    output = Path(output_csv)
    bom_path = system / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    pin_contract_path = system / "SYMBOL_PIN_CONTRACT_SYS_001.csv"

    errors: list[str] = []
    for path, label in (
        (xml_path, "xml_netlist"),
        (bom_path, "bom_contract"),
        (pin_contract_path, "pin_contract"),
    ):
        if not path.is_file():
            errors.append(f"missing:{label}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": sorted(errors),
        }

    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"xml_parse:{exc}"],
        }

    refs = physical_refs(system)
    endpoints: dict[tuple[str, str], str] = {}
    conflicts: list[str] = []

    nets_parent = root.find("nets")
    if nets_parent is None:
        errors.append("missing_nets")
    else:
        for net in nets_parent.findall("net"):
            net_name = str(net.get("name", "")).strip()
            for node in net.findall("node"):
                ref = str(node.get("ref", "")).strip()
                pin = str(node.get("pin", "")).strip()
                if ref not in refs or not pin:
                    continue
                key = (ref, pin)
                previous = endpoints.get(key)
                if previous is not None and previous != net_name:
                    conflicts.append(
                        f"{ref}.{pin}:{previous}|{net_name}"
                    )
                endpoints[key] = net_name

    if conflicts:
        errors.append(
            "endpoint_multiple_nets:"
            + ",".join(sorted(set(conflicts)))
        )

    for ref, pin in sorted(open_pin_contract(system)):
        net_name = endpoints.get((ref, pin), "")
        if net_name and not net_name.startswith("unconnected-"):
            errors.append(f"open_pin_connected:{ref}.{pin}:{net_name}")

    rows = [
        {
            "designator": ref,
            "pin": pin,
            "net_name": net,
        }
        for (ref, pin), net in sorted(endpoints.items())
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["designator", "pin", "net_name"],
        )
        writer.writeheader()
        writer.writerows(rows)

    status = "PASS" if not errors and rows else "FAIL"
    if not rows:
        errors.append("empty_physical_netlist")

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "physical_ref_count": len(refs),
        "connected_endpoint_count": len(rows),
        "input_sha256": {
            "xml_netlist": sha256_file(xml_path),
            "bom_contract": sha256_file(bom_path),
            "pin_contract": sha256_file(pin_contract_path),
        },
        "output": {
            "path": output.as_posix(),
            "sha256": sha256_file(output),
        },
        "notes": [
            (
                "Only endpoints whose designators exist in the authoritative "
                "layout BOM are retained; KiCad power symbols are excluded."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--xml-netlist", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-result", required=True)
    args = parser.parse_args()

    result = build(
        system_root=args.system_root,
        xml_netlist=args.xml_netlist,
        output_csv=args.output_csv,
    )
    Path(args.output_result).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
