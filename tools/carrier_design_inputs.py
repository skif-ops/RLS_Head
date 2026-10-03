from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


RESULT_SCHEMA = "CARRIER-DESIGN-INPUTS-001"

FILES = {
    "bom": "BOM_SYS_CARRIER_002.csv",
    "pinmap": "PINMAP_SYS_001.csv",
    "clock_tree": "CLOCK_TREE_SYS_001.csv",
    "power_tree": "POWER_TREE_SYS_001.csv",
    "netlist": "NETLIST_SYS_001.csv",
}

REQUIRED_MPNS = {
    "STM32H753IIT6",
    "ICM-42688-P",
    "LAN8742Ai-CZ-TR",
    "TCAN3404DRBRQ1",
    "TPS62130ARGTR",
    "TPS259470ARPWR",
    "ECS-2520S33-250-FN-TR",
    "ECS-2520S33-500-FN-TR",
}

REQUIRED_PINMAP = {
    "GNSS_PPS": ("PA0", "40", "TIM2_CH1"),
    "RADAR_REF": ("PB10", "79", "TIM2_CH3"),
    "IMU_DRDY": ("PB11", "80", "TIM2_CH4"),
    "IMU_NSS": ("PB12", "92", "SPI2_NSS"),
    "IMU_SCK": ("PB13", "93", "SPI2_SCK"),
    "IMU_MISO": ("PB14", "94", "SPI2_MISO"),
    "IMU_MOSI": ("PB15", "95", "SPI2_MOSI"),
    "GNSS_TX": ("PD8", "96", "USART3_TX"),
    "GNSS_RX": ("PD9", "97", "USART3_RX"),
    "CAN_RX": ("PD0", "141", "FDCAN1_RX"),
    "CAN_TX": ("PD1", "142", "FDCAN1_TX"),
    "ETH_RMII_REF_CLK": ("PA1", "41", "ETH_RMII_REF_CLK"),
    "ETH_MDIO": ("PA2", "42", "ETH_MDIO"),
    "ETH_MDC": ("PC1", "33", "ETH_MDC"),
    "ETH_RMII_CRS_DV": ("PA7", "53", "ETH_RMII_CRS_DV"),
    "ETH_RMII_RXD0": ("PC4", "54", "ETH_RMII_RXD0"),
    "ETH_RMII_RXD1": ("PC5", "55", "ETH_RMII_RXD1"),
    "ETH_RMII_TX_EN": ("PG11", "153", "ETH_RMII_TX_EN"),
    "ETH_RMII_TXD0": ("PG13", "155", "ETH_RMII_TXD0"),
    "ETH_RMII_TXD1": ("PG14", "156", "ETH_RMII_TXD1"),
    "SWDIO": ("PA13", "124", "SWDIO"),
    "SWCLK": ("PA14", "136", "SWCLK"),
    "MCU_HSE": ("PH0", "29", "OSC_IN"),
}

REQUIRED_NETS = {
    "GNSS_PPS",
    "RADAR_REF",
    "IMU_DRDY",
    "IMU_NSS",
    "IMU_SCK",
    "IMU_MISO",
    "IMU_MOSI",
    "ETH_50M",
    "ETH_MDIO",
    "ETH_MDC",
    "ETH_CRS_DV",
    "ETH_RXD0",
    "ETH_RXD1",
    "ETH_TX_EN",
    "ETH_TXD0",
    "ETH_TXD1",
    "CAN_RX",
    "CAN_TX",
    "SWDIO",
    "SWCLK",
    "MCU_HSE_25M",
    "VIN_RAW",
    "VIN_PROTECTED",
    "3V3",
}

REQUIRED_CLOCKS = {
    "MCU_HSE_25M": 25_000_000,
    "ETH_50M": 50_000_000,
    "GNSS_PPS": 1,
    "RADAR_REF": 0,
    "IMU_DRDY": 0,
}

REQUIRED_POWER_DEVICES = {
    "SMAJ15CA",
    "TPS259470ARPWR",
    "TPS62130ARGTR",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        return list(reader)


def validate_bom(path: Path) -> dict:
    rows = read_csv(path)
    mpns = {
        str(row.get("mpn", "")).strip()
        for row in rows
        if str(row.get("mpn", "")).strip()
    }

    missing = sorted(REQUIRED_MPNS - mpns)

    not_selected = sorted(
        str(row.get("mpn", "")).strip()
        for row in rows
        if str(row.get("mpn", "")).strip() in REQUIRED_MPNS
        and str(row.get("status", "")).strip() != "SELECTED"
    )

    return {
        "status": "PASS" if not missing and not not_selected else "FAIL",
        "row_count": len(rows),
        "missing_mpns": missing,
        "not_selected": not_selected,
    }


def validate_pinmap(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []

    by_signal: dict[str, dict[str, str]] = {}
    seen_mcu: dict[str, str] = {}
    seen_physical: dict[str, str] = {}

    for row in rows:
        signal = str(row.get("signal", "")).strip()
        mcu_pin = str(row.get("mcu_pin", "")).strip()
        physical = str(row.get("physical_pin", "")).strip()

        if not signal:
            findings.append("blank_signal")
            continue

        if signal in by_signal:
            findings.append(f"duplicate_signal:{signal}")

        by_signal[signal] = row

        if mcu_pin:
            previous = seen_mcu.get(mcu_pin)
            if previous is not None and previous != signal:
                findings.append(
                    f"duplicate_mcu_pin:{mcu_pin}:{previous}:{signal}"
                )
            seen_mcu[mcu_pin] = signal

        if physical:
            previous = seen_physical.get(physical)
            if previous is not None and previous != signal:
                findings.append(
                    f"duplicate_physical_pin:{physical}:{previous}:{signal}"
                )
            seen_physical[physical] = signal

    for signal, expected in REQUIRED_PINMAP.items():
        row = by_signal.get(signal)
        if row is None:
            findings.append(f"missing_signal:{signal}")
            continue

        actual = (
            str(row.get("mcu_pin", "")).strip(),
            str(row.get("physical_pin", "")).strip(),
            str(row.get("peripheral", "")).strip(),
        )

        if actual != expected:
            findings.append(
                f"mapping:{signal}:{actual}!={expected}"
            )

        if signal in {"GNSS_PPS", "RADAR_REF", "IMU_DRDY"}:
            if str(row.get("criticality", "")).strip() != "P0":
                findings.append(f"criticality:{signal}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_clock_tree(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []

    grouped: dict[str, list[dict[str, str]]] = {}

    for row in rows:
        clock_id = str(row.get("clock_id", "")).strip()
        grouped.setdefault(clock_id, []).append(row)

    for clock_id, expected_hz in REQUIRED_CLOCKS.items():
        entries = grouped.get(clock_id, [])
        if not entries:
            findings.append(f"missing_clock:{clock_id}")
            continue

        for entry in entries:
            try:
                hz = int(str(entry.get("frequency_hz", "")).strip())
            except ValueError:
                findings.append(f"frequency_parse:{clock_id}")
                continue

            if hz != expected_hz:
                findings.append(
                    f"frequency:{clock_id}:{hz}!={expected_hz}"
                )

            if str(entry.get("criticality", "")).strip() != "P0":
                findings.append(f"criticality:{clock_id}")

    eth_entries = grouped.get("ETH_50M", [])
    eth_targets = {
        str(row.get("target", "")).strip()
        for row in eth_entries
    }

    for target in {"STM32H753_PA1", "LAN8742A_REF_CLK"}:
        if target not in eth_targets:
            findings.append(f"eth_50m_target:{target}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_power_tree(path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []

    devices = {
        str(row.get("device", "")).strip()
        for row in rows
    }

    missing = sorted(REQUIRED_POWER_DEVICES - devices)
    findings.extend(f"missing_device:{item}" for item in missing)

    transitions = {
        (
            str(row.get("input_net", "")).strip(),
            str(row.get("output_net", "")).strip(),
        )
        for row in rows
    }

    for pair in {
        ("VIN_TVS", "VIN_PROTECTED"),
        ("VIN_PROTECTED", "3V3"),
    }:
        if pair not in transitions:
            findings.append(f"missing_transition:{pair[0]}->{pair[1]}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_netlist(path: Path, pinmap_path: Path) -> dict:
    rows = read_csv(path)
    findings: list[str] = []

    nets = {
        str(row.get("net_name", "")).strip()
        for row in rows
        if str(row.get("net_name", "")).strip()
    }

    missing = sorted(REQUIRED_NETS - nets)
    findings.extend(f"missing_net:{item}" for item in missing)

    pinmap = read_csv(pinmap_path)

    for row in pinmap:
        net_name = str(row.get("net_name", "")).strip()
        criticality = str(row.get("criticality", "")).strip()

        if criticality in {"P0", "P1"} and net_name not in nets:
            findings.append(
                f"pinmap_net_missing:{net_name}"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "row_count": len(rows),
        "findings": findings,
    }


def validate_design_inputs(directory: str | Path) -> dict:
    directory = Path(directory)
    errors: list[str] = []
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}

    for key, filename in FILES.items():
        path = directory / filename
        paths[key] = path

        if not path.is_file():
            errors.append(f"missing_file:{filename}")
            continue

        hashes[key] = sha256_file(path)

    if errors:
        return {
            "schema": RESULT_SCHEMA,
            "status": "INVALID",
            "errors": errors,
            "hashes": hashes,
        }

    try:
        bom = validate_bom(paths["bom"])
        pinmap = validate_pinmap(paths["pinmap"])
        clock_tree = validate_clock_tree(paths["clock_tree"])
        power_tree = validate_power_tree(paths["power_tree"])
        netlist = validate_netlist(
            paths["netlist"],
            paths["pinmap"],
        )
    except (ValueError, KeyError) as exc:
        return {
            "schema": RESULT_SCHEMA,
            "status": "INVALID",
            "errors": [f"parse:{exc}"],
            "hashes": hashes,
        }

    components = {
        "bom": bom,
        "pinmap": pinmap,
        "clock_tree": clock_tree,
        "power_tree": power_tree,
        "netlist": netlist,
    }

    failed = [
        name
        for name, value in components.items()
        if value["status"] != "PASS"
    ]

    return {
        "schema": RESULT_SCHEMA,
        "status": (
            "DESIGN_INPUT_READY"
            if not failed
            else "FAIL"
        ),
        "errors": errors,
        "failed_components": failed,
        "hashes": hashes,
        **components,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate authoritative System Carrier design inputs"
    )
    parser.add_argument("directory")
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = validate_design_inputs(args.directory)

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return 0 if result["status"] == "DESIGN_INPUT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
