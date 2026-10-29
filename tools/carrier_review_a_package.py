from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from tools.carrier_design_inputs import validate_design_inputs
from tools.carrier_hierarchy_contract import validate_contract as validate_hierarchy
from tools.carrier_schematic_contract import validate_contract as validate_schematic


SCHEMA = "CARRIER-REVIEW-A-PACKAGE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": target.name,
        "sha256": sha256_file(target),
        "size": target.stat().st_size,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def contains_component(
    rows: list[dict[str, str]],
    ref_or_pattern: str,
    value_or_mpn: str,
) -> bool:
    return any(
        str(row.get("ref_or_pattern", "")).strip() == ref_or_pattern
        and str(row.get("value_or_mpn", "")).strip() == value_or_mpn
        for row in rows
    )


def hierarchy_nets(rows: list[dict[str, str]], sheet: str) -> set[str]:
    return {
        str(row.get("net_name", "")).strip()
        for row in rows
        if str(row.get("sheet", "")).strip() == sheet
    }


def derive_audits(system: Path) -> tuple[dict[str, str], dict]:
    design = validate_design_inputs(system)
    hierarchy = validate_hierarchy(
        system / "HIERARCHY_INTERFACE_SYS_001.csv"
    )
    schematic = validate_schematic(system)

    components = read_csv(
        system / "SCHEMATIC_COMPONENTS_SYS_001.csv"
    )
    hierarchy_rows = read_csv(
        system / "HIERARCHY_INTERFACE_SYS_001.csv"
    )

    mcu_nets = hierarchy_nets(hierarchy_rows, "MCU_CORE")
    imu_nets = hierarchy_nets(hierarchy_rows, "IMU")
    time_gnss_nets = hierarchy_nets(hierarchy_rows, "TIME_GNSS")
    host_uart_nets = hierarchy_nets(hierarchy_rows, "HOST_UART")
    can_nets = hierarchy_nets(hierarchy_rows, "RADAR_IO_CAN")
    all_hierarchy_nets = {
        str(row.get("net_name", "")).strip()
        for row in hierarchy_rows
    }

    reset_boot_ok = (
        contains_component(components, "R_BOOT0", "10k 1%")
        and {"BOOT0", "NRST"}.issubset(mcu_nets)
    )

    timing_ok = (
        design.get("pinmap", {}).get("status") == "PASS"
        and {
            "GNSS_PPS",
            "RADAR_REF",
            "IMU_DRDY",
        }.issubset(mcu_nets)
    )

    imu_ok = (
        design.get("bom", {}).get("status") == "PASS"
        and {
            "3V3",
            "GND",
            "IMU_DRDY",
            "IMU_NSS",
            "IMU_SCK",
            "IMU_MISO",
            "IMU_MOSI",
        }.issubset(imu_nets)
    )

    host_uart_ok = (
        design.get("bom", {}).get("status") == "PASS"
        and {
            "3V3",
            "GND",
            "HOST_UART1_TX",
            "HOST_UART1_RX",
            "HOST_UART2_TX",
            "HOST_UART2_RX",
        }.issubset(host_uart_nets)
    )

    external_gnss_ok = (
        design.get("bom", {}).get("status") == "PASS"
        and contains_component(
            components,
            "J_GNSS_EXT",
            "SM06B-GHS-TB(LF)(SN)",
        )
        and contains_component(
            components,
            "D_GNSS_EXT",
            "TPD4E05U06DQAR",
        )
        and {
            "5V_GNSS",
            "GND",
            "GNSS_PPS",
            "GNSS_RX_EXT",
            "GNSS_TX_EXT",
        }.issubset(time_gnss_nets)
    )

    obsolete_nets = {
        "GNSS_RF",
        "GNSS_VCC_RF",
        "GNSS_VUSB_LOCAL",
        "GNSS_BCKP_LOCAL",
        "GNSS_BIAS_FILTER",
    }
    obsolete_net_present = any(
        net in obsolete_nets
        or net.startswith("ETH_")
        or net.startswith("RMII_")
        for net in all_hierarchy_nets
    )
    component_text = " ".join(
        str(value).lower()
        for row in components
        for value in row.values()
    )
    obsolete_component_present = any(
        token in component_text
        for token in (
            "ethernet",
            "rmii",
            "rj45",
            "onboard gnss",
            "gnss rf",
        )
    )
    no_obsolete_interfaces_ok = (
        {
            "HOST_UART1_TX",
            "HOST_UART1_RX",
            "HOST_UART2_TX",
            "HOST_UART2_RX",
        }.issubset(host_uart_nets)
        and not obsolete_net_present
        and not obsolete_component_present
    )

    can_ok = (
        design.get("radar_interface", {}).get("status") == "PASS"
        and {
            "CAN_TX",
            "CAN_RX",
            "RADAR_REF",
            "RADAR_12V",
            "GND",
        }.issubset(can_nets)
    )

    audits = {
        "power": (
            "PASS"
            if design.get("power_tree", {}).get("status") == "PASS"
            and schematic.get("power_budget", {}).get("status") == "PASS"
            else "FAIL"
        ),
        "clock": (
            "PASS"
            if design.get("clock_tree", {}).get("status") == "PASS"
            else "FAIL"
        ),
        "reset_boot": "PASS" if reset_boot_ok else "FAIL",
        "timing_capture": "PASS" if timing_ok else "FAIL",
        "imu": "PASS" if imu_ok else "FAIL",
        "host_uart": "PASS" if host_uart_ok else "FAIL",
        "external_gnss": "PASS" if external_gnss_ok else "FAIL",
        "can_fd": "PASS" if can_ok else "FAIL",
        "no_obsolete_interfaces": (
            "PASS" if no_obsolete_interfaces_ok else "FAIL"
        ),
    }

    details = {
        "design_inputs": design,
        "hierarchy": hierarchy,
        "schematic_contract": schematic,
        "checks": {
            "reset_boot": reset_boot_ok,
            "timing_capture": timing_ok,
            "imu": imu_ok,
            "host_uart": host_uart_ok,
            "external_gnss": external_gnss_ok,
            "can_fd": can_ok,
            "no_obsolete_interfaces": no_obsolete_interfaces_ok,
        },
    }

    return audits, details


def build(
    *,
    generated_dir: str | Path,
    system_root: str | Path,
    output_dir: str | Path,
    source_commit: str,
    source_run_id: str,
) -> dict:
    generated = Path(generated_dir)
    system = Path(system_root)
    output = Path(output_dir)

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    generated_schematic = generated / "EVT_SYS_CARRIER.kicad_sch"
    generated_erc = generated / "erc.json"
    bom = system / "BOM_SYS_CARRIER_003.csv"
    pinmap = system / "PINMAP_SYS_001.csv"

    required = [
        generated_schematic,
        generated_erc,
        bom,
        pinmap,
    ]
    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "missing Review A inputs: "
            + ", ".join(missing)
        )

    copied = {
        "schematic": copy_file(
            generated_schematic,
            output / "EVT_SYS_CARRIER.kicad_sch",
        ),
        "erc_json": copy_file(
            generated_erc,
            output / "erc.json",
        ),
        "pinmap": copy_file(
            pinmap,
            output / "PINMAP_SYS_001.csv",
        ),
        "bom": copy_file(
            bom,
            output / "BOM_SYS_CARRIER_003.csv",
        ),
    }

    erc_data = json.loads(
        (output / "erc.json").read_text(
            encoding="utf-8"
        )
    )

    violations = [
        violation
        for sheet in erc_data.get("sheets", [])
        for violation in sheet.get("violations", [])
    ]
    if violations:
        raise ValueError(
            f"Review A package requires zero ERC violations; got {len(violations)}"
        )

    audits, audit_details = derive_audits(system)

    if any(value != "PASS" for value in audits.values()):
        raise ValueError(
            "Review A audit derivation failed: "
            + json.dumps(audits, sort_keys=True)
        )

    manifest = {
        "schema": "CARRIER-REVIEW-A-MANIFEST-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "cad_tool": "KiCad",
        "cad_version": str(
            erc_data.get("kicad_version", "9.0.9")
        ),
        "synthetic_fixture": False,
        "evidence_level": "CAD_REVIEW",
        "source_commit": source_commit,
        "source_ci_run_id": source_run_id,
        "artifacts": [
            {
                "id": artifact_id,
                "path": item["path"],
                "sha256": item["sha256"],
            }
            for artifact_id, item in copied.items()
        ],
        "erc_policy": {
            "errors_allowed": 0,
            "warnings_allowed": 0,
        },
        "audits": audits,
    }

    (output / "manifest.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (output / "audit_details.json").write_text(
        json.dumps(
            audit_details,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = {
        "schema": SCHEMA,
        "status": "READY_FOR_REVIEW_A_VALIDATION",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "source_commit": source_commit,
        "source_ci_run_id": source_run_id,
        "erc_violation_count": 0,
        "audits": audits,
        "artifact_count": len(copied),
        "manifest": "manifest.json",
        "audit_details": "audit_details.json",
    }

    (output / "package_summary.json").write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args()

    result = build(
        generated_dir=args.generated_dir,
        system_root=args.system_root,
        output_dir=args.output_dir,
        source_commit=args.source_commit,
        source_run_id=args.source_run_id,
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
