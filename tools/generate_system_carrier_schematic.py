from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from pathlib import Path

import kicad_sch_api as ksa
from kicad_sch_api.core.types import (
    HierarchicalLabelShape,
)

from tools.generate_system_carrier_symbols import (
    LIBRARY_NAME as LOCAL_SYMBOL_LIBRARY,
    generate as generate_local_symbols,
)


PROJECT_NAME = "EVT_SYS_CARRIER"
STATUS_SCHEMA = "SYSTEM-CARRIER-CAD-SCAFFOLD-001"

SHEETS = [
    ("POWER_INPUT", "10_POWER_INPUT.kicad_sch"),
    ("MCU_CORE", "20_MCU_CORE.kicad_sch"),
    ("TIME_GNSS", "30_TIME_GNSS.kicad_sch"),
    ("IMU", "40_IMU.kicad_sch"),
    ("RADAR_IO_CAN", "50_RADAR_IO_CAN.kicad_sch"),
    ("ETHERNET", "60_ETHERNET.kicad_sch"),
    ("DEBUG_BOOT", "70_DEBUG_BOOT.kicad_sch"),
]

PLACEHOLDER_LIB = "Connector_Generic:Conn_01x08"

SYMBOL_LIBRARIES = {
    "SystemCarrier_Local": "${KIPRJMOD}/SystemCarrier_Local.kicad_sym",
    "Device": "${KICAD9_SYMBOL_DIR}/Device.kicad_sym",
    "Connector_Generic": "${KICAD9_SYMBOL_DIR}/Connector_Generic.kicad_sym",
    "Connector": "${KICAD9_SYMBOL_DIR}/Connector.kicad_sym",
    "RF_GPS": "${KICAD9_SYMBOL_DIR}/RF_GPS.kicad_sym",
    "Switch": "${KICAD9_SYMBOL_DIR}/Switch.kicad_sym",
    "MCU_ST_STM32H7": "${KICAD9_SYMBOL_DIR}/MCU_ST_STM32H7.kicad_sym",
    "Interface_Ethernet": "${KICAD9_SYMBOL_DIR}/Interface_Ethernet.kicad_sym",
}


def write_symbol_library_table(output_dir: Path) -> None:
    lines = [
        "(sym_lib_table",
        "  (version 7)",
    ]

    for name, uri in SYMBOL_LIBRARIES.items():
        lines.append(
            '  (lib (name "' + name + '") '
            '(type "KiCad") '
            '(uri "' + uri + '") '
            '(options "") '
            '(descr "RLS Head generated Carrier symbol library binding"))'
        )

    lines.append(")")
    (output_dir / "sym-lib-table").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )



def load_symbol_pin_contract(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("SYMBOL_PIN_CONTRACT_SYS_001.csv missing header")
        return list(reader)


def apply_symbol_pin_contract(
    sch,
    rows: list[dict[str, str]],
    references: set[str],
    hierarchy_nets: set[str],
) -> dict[str, int]:
    direct_prefixes = (
        "IMU_",
        "ETH_",
        "CAN_",
        "GNSS_",
        "RADAR_",
    )
    direct_exact = {
        "3V3",
        "GND",
    }

    connected = 0
    no_connect = 0

    for row in rows:
        reference = str(row.get("ref", "")).strip()
        if reference not in references:
            continue

        pin_number = str(row.get("pin_number", "")).strip()
        connection = str(row.get("connection", "")).strip()
        policy = str(row.get("policy", "")).strip()

        position = sch.get_component_pin_position(
            reference,
            pin_number,
        )
        if position is None:
            continue

        if policy == "NC_ALLOWED":
            sch.no_connects.add(
                position=(
                    position.x,
                    position.y,
                )
            )
            no_connect += 1
            continue

        if policy != "CONNECT":
            continue

        if connection in hierarchy_nets:
            # The authoritative hierarchical label is placed directly
            # on this component pin later in the generation pass.
            continue

        if (
            connection in direct_exact
            or connection.startswith(direct_prefixes)
        ):
            add_pin_label(
                sch,
                connection,
                reference,
                pin_number,
            )
            connected += 1

    return {
        "connected": connected,
        "no_connect": no_connect,
    }


def load_mcu_pinmap(pinmap_path: Path) -> list[dict[str, str]]:
    with pinmap_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("PINMAP_SYS_001.csv missing header")
        return list(reader)


def load_assigned_mcu_gpio(pinmap_path: Path) -> set[str]:
    with pinmap_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("PINMAP_SYS_001.csv missing header")

        return {
            str(row.get("mcu_pin", "")).strip()
            for row in reader
            if str(row.get("mcu_pin", "")).strip()
        }


def validate_mcu_pinmap_against_symbol(
    sch,
    pinmap_rows: list[dict[str, str]],
) -> None:
    component = sch.components.get("U1")
    if component is None:
        raise ValueError("missing component:U1")

    by_number = {
        str(pin.number).strip():
            str(pin.name).strip()
        for pin in component.pins
    }

    for row in pinmap_rows:
        physical = str(
            row.get("physical_pin", "")
        ).strip()
        expected_name = str(
            row.get("mcu_pin", "")
        ).strip()

        if not physical or not expected_name:
            continue

        actual_name = by_number.get(physical)
        if actual_name is None:
            raise ValueError(
                f"U1 physical pin missing:{physical}:{expected_name}"
            )

        normalized = actual_name.removesuffix("_C")
        if normalized != expected_name:
            raise ValueError(
                "U1 pinmap mismatch:"
                f"{physical}:{actual_name}!={expected_name}"
            )


def mark_unused_mcu_gpio_no_connect(
    sch,
    assigned_gpio: set[str],
) -> int:
    component = sch.components.get("U1")
    if component is None:
        return 0

    count = 0

    for pin in component.pins:
        pin_name = str(pin.name).strip()

        match = re.fullmatch(r"(P[A-K][0-9]+)(?:_C)?", pin_name)
        if match is None:
            continue

        base_name = match.group(1)
        if base_name in assigned_gpio:
            continue

        pin_position = sch.get_component_pin_position(
            "U1",
            str(pin.number),
        )
        if pin_position is None:
            continue

        sch.no_connects.add(
            position=(
                pin_position.x,
                pin_position.y,
            )
        )
        count += 1

    return count


def add_pin_label(
    sch,
    net_name: str,
    reference: str,
    pin_number: str,
) -> None:
    if sch.get_component_pin_position(
        reference,
        pin_number,
    ) is None:
        raise ValueError(
            f"missing pin:{reference}:{pin_number}"
        )

    sch.add_label(
        net_name,
        pin=(reference, pin_number),
    )


def add_labels_by_pin_name(
    sch,
    reference: str,
    mapping: dict[str, str],
) -> None:
    component = sch.components.get(reference)
    if component is None:
        raise ValueError(f"missing component:{reference}")

    for pin in component.pins:
        name = str(pin.name).strip()
        net = mapping.get(name)
        if net is None:
            continue
        add_pin_label(
            sch,
            net,
            reference,
            str(pin.number),
        )


def pos(x_grid: int, y_grid: int) -> tuple[float, float]:
    return (1.27 * x_grid, 1.27 * y_grid)


def add_local_symbol(
    sch,
    reference: str,
    mpn: str,
    value: str,
    position: tuple[float, float],
    placeholders: list[dict],
) -> None:
    try:
        sch.components.add(
            f"{LOCAL_SYMBOL_LIBRARY}:{mpn}",
            reference,
            value,
            position,
            MPN=mpn,
            Capture_Status="LOCAL_CONTRACT_SYMBOL",
        )
    except Exception:
        add_placeholder(
            sch,
            reference,
            value,
            position,
            placeholders,
        )


def add_placeholder(
    sch,
    reference: str,
    value: str,
    position: tuple[float, float],
    placeholders: list[dict],
) -> None:
    sch.components.add(
        lib_id=PLACEHOLDER_LIB,
        reference=reference,
        value=value,
        position=position,
        MPN=value,
        Capture_Status="SYMBOL_PENDING",
    )
    placeholders.append(
        {
            "reference": reference,
            "value": value,
            "sheet": getattr(sch, "name", ""),
        }
    )


def populate_power(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "POWER_INPUT — Rev A authoritative capture\n"
        "TPS259470A protection + fixed 3.3V TPS62132",
        position=pos(20, 10),
        size=1.27,
    )

    sch.components.add("Connector_Generic:Conn_01x02", "J1", "12V_IN", pos(18, 24))
    sch.components.add("Device:D_TVS", "D1", "SMAJ15CA", pos(30, 24))
    add_local_symbol(sch, "U6", "TPS259470ARPWR", "TPS259470ARPWR_SYS", pos(43, 24), placeholders)
    add_local_symbol(sch, "U5", "TPS62132RGTR", "TPS62132RGTR_3V3", pos(60, 24), placeholders)
    add_local_symbol(sch, "U7", "TPS259470ARPWR", "TPS259470ARPWR_RADAR", pos(43, 42), placeholders)

    sch.components.add("Device:L", "L1", "2.2uH", pos(72, 24))
    sch.components.add("Device:C", "C1", "10uF/25V", pos(55, 36))
    sch.components.add("Device:C", "C2", "22uF/6.3V", pos(76, 36))
    sch.components.add("Device:C", "C3", "3.3nF", pos(64, 36))
    sch.components.add("Device:C", "C4", "100nF/25V", pos(58, 40))
    sch.components.add("Device:R", "R1", "665R 1%", pos(39, 34))
    sch.components.add("Device:R", "R2", "1.05k 1%", pos(39, 52))
    sch.components.add("Device:R", "R5P", "100k 1% PG_PU", pos(68, 34))
    sch.components.add("Device:R", "R6F", "10k 1% FLT_PU", pos(48, 34))
    sch.components.add("Device:R", "R7F", "10k 1% FLT_PU", pos(48, 52))

    for ref, value, p in [
        ("R61", "470k 1%", pos(25, 30)), ("R62", "36.0k 1%", pos(29, 34)), ("R63", "41.2k 1%", pos(33, 38)),
        ("R71", "470k 1%", pos(25, 48)), ("R72", "16.9k 1%", pos(29, 52)), ("R73", "43.7k 1%", pos(33, 56)),
    ]:
        sch.components.add("Device:R", ref, value, p)

    sch.components.add("Device:C", "C6D", "3.3nF", pos(43, 36))
    sch.components.add("Device:C", "C7D", "3.3nF", pos(43, 54))
    sch.components.add("Connector_Generic:Conn_01x02", "J2", "RADAR_12V_OUT", pos(75, 50))

    add_pin_label(sch, "VIN_RAW", "J1", "1")
    add_pin_label(sch, "GND", "J1", "2")
    add_pin_label(sch, "VIN_RAW", "D1", "1")
    add_pin_label(sch, "GND", "D1", "2")

    for pin, net in {"4":"SYS_EFUSE_FLT","5":"VIN_RAW","6":"VIN_PROTECTED","8":"GND"}.items():
        add_pin_label(sch, net, "U6", pin)
    add_pin_label(sch, "VIN_RAW", "R61", "1")
    sch.add_wire_between_pins("R61", "2", "U6", "1")
    sch.add_wire_between_pins("U6", "1", "R62", "1")
    sch.add_wire_between_pins("R62", "2", "U6", "2")
    sch.add_wire_between_pins("U6", "2", "R63", "1")
    add_pin_label(sch, "GND", "R63", "2")
    sch.add_wire_between_pins("U6", "9", "R1", "1")
    add_pin_label(sch, "GND", "R1", "2")
    sch.add_wire_between_pins("U6", "7", "C6D", "1")
    add_pin_label(sch, "GND", "C6D", "2")
    add_pin_label(sch, "SYS_EFUSE_FLT", "R6F", "1")
    add_pin_label(sch, "3V3", "R6F", "2")
    for pin in ("3","10"):
        p=sch.get_component_pin_position("U6", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))

    for pin, net in {"4":"RADAR_EFUSE_FLT","5":"VIN_PROTECTED","6":"RADAR_12V","8":"GND"}.items():
        add_pin_label(sch, net, "U7", pin)
    add_pin_label(sch, "VIN_PROTECTED", "R71", "1")
    sch.add_wire_between_pins("R71", "2", "U7", "1")
    sch.add_wire_between_pins("U7", "1", "R72", "1")
    sch.add_wire_between_pins("R72", "2", "U7", "2")
    sch.add_wire_between_pins("U7", "2", "R73", "1")
    add_pin_label(sch, "GND", "R73", "2")
    sch.add_wire_between_pins("U7", "9", "R2", "1")
    add_pin_label(sch, "GND", "R2", "2")
    sch.add_wire_between_pins("U7", "7", "C7D", "1")
    add_pin_label(sch, "GND", "C7D", "2")
    add_pin_label(sch, "RADAR_EFUSE_FLT", "R7F", "1")
    add_pin_label(sch, "3V3", "R7F", "2")
    for pin in ("3","10"):
        p=sch.get_component_pin_position("U7", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))

    for pin in ("1","2","3"):
        add_pin_label(sch, "BUCK_SW", "U5", pin)
    add_pin_label(sch, "BUCK_SW", "L1", "1")
    add_pin_label(sch, "3V3", "L1", "2")
    add_pin_label(sch, "U5_PG", "U5", "4")
    add_pin_label(sch, "U5_PG", "R5P", "1")
    add_pin_label(sch, "3V3", "R5P", "2")
    for pin in ("5","6","15","16","EP"):
        if sch.get_component_pin_position("U5", pin) is not None:
            add_pin_label(sch, "GND", "U5", pin)
    for pin in ("7","8"):
        p=sch.get_component_pin_position("U5", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))
    sch.add_wire_between_pins("U5", "9", "C3", "1")
    add_pin_label(sch, "GND", "C3", "2")
    for pin in ("10","11","12","13"):
        add_pin_label(sch, "VIN_PROTECTED", "U5", pin)
    add_pin_label(sch, "3V3", "U5", "14")

    add_pin_label(sch, "VIN_PROTECTED", "C1", "1")
    add_pin_label(sch, "GND", "C1", "2")
    add_pin_label(sch, "3V3", "C2", "1")
    add_pin_label(sch, "GND", "C2", "2")
    add_pin_label(sch, "VIN_PROTECTED", "C4", "1")
    add_pin_label(sch, "GND", "C4", "2")
    add_pin_label(sch, "RADAR_12V", "J2", "1")
    add_pin_label(sch, "GND", "J2", "2")


def populate_mcu(
    sch,
    placeholders: list[dict],
    assigned_gpio: set[str],
    pinmap_rows: list[dict[str, str]],
) -> int:
    sch.add_text(
        "MCU_CORE — STM32H753IIT6\n"
        "P0 time capture pins remain fixed by PINMAP_SYS_001.csv",
        position=pos(18, 9),
        size=1.27,
    )

    try:
        sch.components.add(
            "MCU_ST_STM32H7:STM32H753IITx",
            "U1",
            "STM32H753IIT6",
            pos(52, 35),
            footprint="Package_QFP:LQFP-176_24x24mm_P0.5mm",
            MPN="STM32H753IIT6",
        )
    except Exception:
        add_placeholder(
            sch,
            "U1",
            "STM32H753IIT6",
            pos(52, 35),
            placeholders,
        )

    sch.components.add("Device:C", "C10", "2.2uF", pos(27, 25))
    sch.components.add("Device:C", "C11", "2.2uF", pos(27, 33))
    sch.components.add("Device:C", "C12", "4.7uF", pos(27, 41))
    sch.components.add("Device:C", "C13", "100nF", pos(83, 26))
    sch.components.add("Device:R", "R10", "10k 1%", pos(83, 38))
    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J10",
        "TC2030_SWD",
        pos(83, 52),
    )

    validate_mcu_pinmap_against_symbol(
        sch,
        pinmap_rows,
    )

    # Power-domain support components required by the Rev.A contract.
    sch.components.add(
        "Device:L_Ferrite",
        "FB1",
        "BLM18BD601SH1",
        pos(30, 18),
        MPN="BLM18BD601SH1",
    )
    sch.components.add(
        "Device:C",
        "C14",
        "1uF",
        pos(36, 22),
    )
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0101",
        "PWR_FLAG",
        pos(22, 18),
    )
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0102",
        "PWR_FLAG",
        pos(22, 52),
    )

    # Bind every assigned MCU signal directly to the authoritative net name.
    for row in pinmap_rows:
        physical = str(
            row.get("physical_pin", "")
        ).strip()
        net_name = str(
            row.get("net_name", "")
        ).strip()
        if physical and net_name:
            add_pin_label(
                sch,
                net_name,
                "U1",
                physical,
            )

    # Core and analog supply pins.
    add_labels_by_pin_name(
        sch,
        "U1",
        {
            "VDD": "3V3",
            "VBAT": "3V3",
            "VDD33_USB": "3V3",
            "VSS": "GND",
            "VSSA": "GND",
            "VDDA": "VDDA_FILTERED",
            "VREF+": "VDDA_FILTERED",
            "PDR_ON": "3V3",
        },
    )

    # VCAP pins each receive their own 2.2 uF low-ESR capacitor.
    sch.add_wire_between_pins(
        "U1",
        "81",
        "C10",
        "1",
    )
    add_pin_label(sch, "GND", "C10", "2")
    sch.add_wire_between_pins(
        "U1",
        "125",
        "C11",
        "1",
    )
    add_pin_label(sch, "GND", "C11", "2")

    # Digital bulk capacitor.
    add_pin_label(sch, "3V3", "C12", "1")
    add_pin_label(sch, "GND", "C12", "2")

    # VDDA filter and local decoupling.
    add_pin_label(sch, "3V3", "FB1", "1")
    add_pin_label(
        sch,
        "VDDA_FILTERED",
        "FB1",
        "2",
    )
    add_pin_label(
        sch,
        "VDDA_FILTERED",
        "C13",
        "1",
    )
    add_pin_label(sch, "GND", "C13", "2")
    add_pin_label(
        sch,
        "VDDA_FILTERED",
        "C14",
        "1",
    )
    add_pin_label(sch, "GND", "C14", "2")

    # BOOT0 default-low strap.
    sch.add_wire_between_pins(
        "U1",
        "166",
        "R10",
        "1",
    )
    add_pin_label(sch, "GND", "R10", "2")

    # SWD Tag-Connect pinout from CONNECTOR_PINOUT_SYS_001.
    for pin_number, net_name in {
        "1": "3V3",
        "2": "SWDIO",
        "3": "GND",
        "4": "SWCLK",
        "5": "GND",
        "6": "SWO",
    }.items():
        add_pin_label(
            sch,
            net_name,
            "J10",
            pin_number,
        )

    # Mark the local rails as explicitly driven for ERC.
    add_pin_label(
        sch,
        "3V3",
        "#FLG0101",
        "1",
    )
    add_pin_label(
        sch,
        "GND",
        "#FLG0102",
        "1",
    )

    return mark_unused_mcu_gpio_no_connect(
        sch,
        assigned_gpio,
    )



def populate_time_gnss(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "TIME_GNSS — NEO-M9N timing and RF entry\n"
        "P0 GNSS_PPS -> STM32 PA0/TIM2_CH1",
        position=pos(18, 9),
        size=1.27,
    )

    try:
        sch.components.add(
            "RF_GPS:NEO-M9N",
            "U8",
            "NEO-M9N-00B",
            pos(50, 32),
            footprint="SystemCarrier_Local:NEO-M9N_LCC24_12.2x16mm",
            MPN="NEO-M9N-00B",
        )
    except Exception:
        add_placeholder(sch, "U8", "NEO-M9N-00B", pos(50, 32), placeholders)

    sch.components.add(
        "Device:D_TVS", "D8", "ESD0P2RF-02LS", pos(72, 28),
        footprint="SystemCarrier_Local:ESD0P2RF-02LS_PG-TSSLP-2-1",
        MPN="ESD0P2RF-02LS",
    )
    sch.components.add("Connector_Generic:Conn_01x02", "J8", "GNSS_UFL", pos(86, 28))
    sch.components.add("Device:C", "C80", "100nF", pos(36, 42))
    sch.components.add("Device:C", "C81", "10uF", pos(42, 42))
    sch.components.add("Device:L", "L80", "27nH DNP_OPTION", pos(72, 42))
    sch.components.add("Device:R", "R80", "10R 0.25W DNP_OPTION", pos(64, 48))
    sch.components.add("Device:C", "C82", "100nF DNP_OPTION", pos(78, 48))
    sch.components.add("Device:R", "R81", "100k 1% VUSB_PD", pos(57, 48))
    sch.components.add("Device:R", "R82", "0R V_BCKP", pos(57, 53))

    # Main supply decoupling.
    add_pin_label(sch, "3V3", "C80", "1")
    add_pin_label(sch, "GND", "C80", "2")
    add_pin_label(sch, "3V3", "C81", "1")
    add_pin_label(sch, "GND", "C81", "2")

    # Backup-domain and unused USB supply requirements.
    sch.add_wire_between_pins("U8", "22", "R82", "1")
    add_pin_label(sch, "3V3", "R82", "2")
    sch.add_wire_between_pins("U8", "7", "R81", "1")
    add_pin_label(sch, "GND", "R81", "2")

    # Internal straps intentionally left open by contract.
    for pin in ("2", "8"):
        p = sch.get_component_pin_position("U8", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))

    # RF path: RF_IN / U.FL signal on GNSS_RF, with shunt ESD.
    add_pin_label(sch, "GNSS_RF", "U8", "11")
    add_pin_label(sch, "GNSS_RF", "J8", "1")
    add_pin_label(sch, "GND", "J8", "2")
    add_pin_label(sch, "GNSS_RF", "D8", "1")
    add_pin_label(sch, "GND", "D8", "2")

    # Optional active-antenna bias-T:
    # VCC_RF -> 10R -> filtered node -> 27nH -> GNSS_RF,
    # with 100nF from filtered node to GND.
    add_pin_label(sch, "GNSS_VCC_RF", "U8", "9")
    add_pin_label(sch, "GNSS_VCC_RF", "R80", "1")
    add_pin_label(sch, "GNSS_BIAS_FILTER", "R80", "2")
    add_pin_label(sch, "GNSS_BIAS_FILTER", "L80", "1")
    add_pin_label(sch, "GNSS_RF", "L80", "2")
    add_pin_label(sch, "GNSS_BIAS_FILTER", "C82", "1")
    add_pin_label(sch, "GND", "C82", "2")

    sch.add_text(
        "R82 ties V_BCKP to 3V3 for EVT. R81 pulls unused V_USB to GND.\n"
        "L80/R80/C82 implement the optional active-antenna VCC_RF bias-T.",
        position=pos(18, 62),
        size=1.0,
    )


def populate_imu(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "IMU — ICM-42688-P SPI2 + hardware DRDY\n"
        "P0 IMU_DRDY -> STM32 PB11/TIM2_CH4",
        position=pos(18, 9),
        size=1.27,
    )

    add_local_symbol(
        sch,
        "U2",
        "ICM-42688-P",
        "ICM-42688-P",
        pos(52, 31),
        placeholders,
    )

    sch.components.add("Device:C", "C20", "100nF", pos(38, 42))
    sch.components.add("Device:C", "C21", "2.2uF", pos(45, 42))
    sch.components.add("Device:C", "C22", "10nF", pos(52, 42))

    # VDDIO and mandatory ground/unused-function handling from the
    # authoritative ICM-42688-P pin contract.
    add_pin_label(sch, "3V3", "U2", "5")
    add_pin_label(sch, "GND", "U2", "7")
    add_pin_label(sch, "GND", "U2", "9")

    # Local VDD/VDDIO decoupling.
    add_pin_label(sch, "3V3", "C20", "1")
    add_pin_label(sch, "GND", "C20", "2")
    add_pin_label(sch, "3V3", "C21", "1")
    add_pin_label(sch, "GND", "C21", "2")
    add_pin_label(sch, "3V3", "C22", "1")
    add_pin_label(sch, "GND", "C22", "2")

    sch.add_text(
        "C20/C21 are VDD decoupling; C22 is the dedicated VDDIO 10nF bypass.\n"
        "Pin7 RESV and pin9 FSYNC are tied to GND per the Rev.A pin contract.",
        position=pos(18, 61),
        size=1.0,
    )


def populate_radar_io_can(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "RADAR_IO_CAN — external AWR2944-class EVM interface\n"
        "CAN-FD control/metadata + P0 RADAR_REF timestamp + protected 12V",
        position=pos(18, 9),
        size=1.27,
    )

    add_local_symbol(
        sch, "U4", "TCAN3404DRBRQ1", "TCAN3404DRBRQ1",
        pos(50, 30), placeholders
    )
    add_local_symbol(
        sch, "D4", "ESD2CANFD24DBZRQ1", "ESD2CANFD24-Q1",
        pos(68, 30), placeholders
    )

    sch.components.add("Connector_Generic:Conn_01x06", "J4", "RADAR_IO", pos(86, 32))
    sch.components.add("Connector_Generic:Conn_01x02", "J5", "RADAR_PWR", pos(86, 50))
    sch.components.add("Device:R", "R40", "120R 1% DNP_DEFAULT", pos(70, 45))
    sch.components.add("Device:C", "C40", "100nF", pos(42, 42))
    sch.components.add("Device:R", "R41", "10k 1% STB_PD", pos(52, 46))
    sch.components.add("Device:R", "R42", "10k 1% SHDN_PD", pos(59, 46))

    # Transceiver local power and exposed-pad ground.
    add_pin_label(sch, "3V3", "C40", "1")
    add_pin_label(sch, "GND", "C40", "2")
    if sch.get_component_pin_position("U4", "EP") is not None:
        add_pin_label(sch, "GND", "U4", "EP")

    # Deterministic normal mode defaults.
    sch.add_wire_between_pins("U4", "8", "R41", "1")
    add_pin_label(sch, "GND", "R41", "2")
    sch.add_wire_between_pins("U4", "5", "R42", "1")
    add_pin_label(sch, "GND", "R42", "2")

    # CAN bus and ESD.
    add_pin_label(sch, "RADAR_CANH", "D4", "1")
    add_pin_label(sch, "RADAR_CANL", "D4", "2")
    add_pin_label(sch, "GND", "D4", "3")

    # Radar I/O connector according to CONNECTOR_PINOUT_SYS_001.csv.
    add_pin_label(sch, "RADAR_CANL", "J4", "1")
    add_pin_label(sch, "GND", "J4", "2")
    add_pin_label(sch, "RADAR_CANH", "J4", "3")
    add_pin_label(sch, "RADAR_REF", "J4", "4")
    add_pin_label(sch, "GND", "J4", "5")
    p = sch.get_component_pin_position("J4", "6")
    if p is not None:
        sch.no_connects.add(position=(p.x, p.y))

    # Optional endpoint termination across CANH/CANL.
    add_pin_label(sch, "RADAR_CANH", "R40", "1")
    add_pin_label(sch, "RADAR_CANL", "R40", "2")

    # Protected radar power connector.
    add_pin_label(sch, "RADAR_12V", "J5", "1")
    add_pin_label(sch, "GND", "J5", "2")

    sch.add_text(
        "R40 is DNP by default and populated only when the carrier is the CAN endpoint.\n"
        "R41/R42 force normal mode defaults. J4 pin6 remains NC by Rev.A contract.",
        position=pos(18, 62),
        size=1.0,
    )


def populate_ethernet(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "ETHERNET — LAN8742A RMII instrumentation link\n"
        "External 50 MHz clock + integrated 10/100BASE-T MagJack",
        position=pos(18, 9),
        size=1.27,
    )

    try:
        sch.components.add(
            "Interface_Ethernet:LAN8742A",
            "U3",
            "LAN8742Ai-CZ-TR",
            pos(48, 31),
            MPN="LAN8742Ai-CZ-TR",
        )
    except Exception:
        add_placeholder(
            sch,
            "U3",
            "LAN8742Ai-CZ-TR",
            pos(48, 31),
            placeholders,
        )

    add_local_symbol(
        sch,
        "Y2",
        "ECS-2520S33-500-FN-TR",
        "ECS-2520S33-500-FN-TR",
        pos(28, 22),
        placeholders,
    )
    add_local_symbol(
        sch,
        "D3",
        "TPD4E05U06DQAR",
        "TPD4E05U06DQAR",
        pos(72, 31),
        placeholders,
    )
    sch.components.add(
        "Connector:RJ45_Bel_SI-60062-F",
        "J6",
        "SI-60182-F",
        pos(88, 31),
        footprint="Connector_RJ:RJ45_Bel_SI-60062-F",
        MPN="SI-60182-F",
        Compatibility_Basis="Bel_SI-60182-F_vs_SI-60062-F_verified",
    )

    sch.components.add("Device:R", "R60", "12.1k 1%", pos(42, 45))
    for ref, y in [("R61", 42), ("R62", 46), ("R63", 50), ("R64", 54)]:
        sch.components.add("Device:R", ref, "49.9R 1%", pos(68, y))

    sch.components.add("Device:C", "C60", "1uF", pos(50, 45))
    sch.components.add("Device:C", "C61", "470pF C0G", pos(56, 45))
    sch.components.add("Device:C", "C62", "100nF", pos(36, 45))
    sch.components.add("Device:C", "C63", "22nF C0G", pos(82, 54))
    sch.components.add("Device:R", "R65", "10k 1% NRST_PD", pos(58, 51))

    # LAN8742 power and mandatory local bias/support network.
    for pin in ("1", "9", "19"):
        add_pin_label(sch, "3V3", "U3", pin)
    if sch.get_component_pin_position("U3", "25") is not None:
        add_pin_label(sch, "GND", "U3", "25")

    sch.add_wire_between_pins("U3", "24", "R60", "1")
    add_pin_label(sch, "GND", "R60", "2")

    sch.add_wire_between_pins("U3", "6", "C60", "1")
    add_pin_label(sch, "GND", "C60", "2")

    # Local 3V3 decoupling / analog filter caps.
    add_pin_label(sch, "3V3", "C62", "1")
    add_pin_label(sch, "GND", "C62", "2")
    add_pin_label(sch, "3V3", "C61", "1")
    add_pin_label(sch, "GND", "C61", "2")

    # Internal strap/default pins and unused outputs.
    for pin in ("2", "3", "4", "10", "14"):
        p = sch.get_component_pin_position("U3", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))

    # PHY controlled reset pulldown.
    add_pin_label(sch, "ETH_NRST", "R65", "1")
    add_pin_label(sch, "GND", "R65", "2")

    # 50 MHz oscillator.
    add_pin_label(sch, "GND", "Y2", "2")
    add_pin_label(sch, "ETH_50M", "Y2", "3")
    add_pin_label(sch, "3V3", "Y2", "4")
    p = sch.get_component_pin_position("Y2", "1")
    if p is not None:
        sch.no_connects.add(position=(p.x, p.y))

    # MDI nets at PHY and ESD array.
    mdi = {
        "20": "ETH_TXN",
        "21": "ETH_TXP",
        "22": "ETH_RXN",
        "23": "ETH_RXP",
    }
    for pin, net in mdi.items():
        add_pin_label(sch, net, "U3", pin)

    for pin, net in {
        "1": "ETH_TXP",
        "2": "ETH_TXN",
        "4": "ETH_RXP",
        "5": "ETH_RXN",
        "3": "GND",
        "8": "GND",
    }.items():
        add_pin_label(sch, net, "D3", pin)

    for pin in ("6", "7", "9", "10"):
        p = sch.get_component_pin_position("D3", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))

    # Four 49.9-ohm MDI terminations to analog 3.3V rail.
    for ref, net in {
        "R61": "ETH_TXP",
        "R62": "ETH_TXN",
        "R63": "ETH_RXP",
        "R64": "ETH_RXN",
    }.items():
        add_pin_label(sch, net, ref, "1")
        add_pin_label(sch, "3V3", ref, "2")

    # MagJack PHY-side pairs.
    for pin, net in {
        "1": "ETH_TXP",
        "3": "ETH_TXN",
        "4": "ETH_RXP",
        "6": "ETH_RXN",
    }.items():
        add_pin_label(sch, net, "J6", pin)

    # TX/RX center taps tied together and AC-shunted to ground.
    add_pin_label(sch, "ETH_CT", "J6", "2")
    add_pin_label(sch, "ETH_CT", "J6", "5")
    add_pin_label(sch, "ETH_CT", "C63", "1")
    add_pin_label(sch, "GND", "C63", "2")

    sch.add_text(
        "R60 = PHY RBIAS. R61-R64 = 49.9R MDI terminations to 3V3.\n"
        "C60 = VDDCR. C63 = 22nF center-tap AC shunt.\n"
        "MagJack LED/shield service pins remain unresolved until the exact SI-60182-F drawing is bound.",
        position=pos(18, 64),
        size=1.0,
    )


def populate_debug_boot(sch, placeholders: list[dict]) -> None:
    del placeholders

    sch.add_text(
        "DEBUG_BOOT — SWD, reset and boot service access\n"
        "No vehicle actuation/control interfaces",
        position=pos(18, 9),
        size=1.27,
    )

    sch.components.add(
        "Switch:SW_Push",
        "SW1",
        "NRST",
        pos(52, 30),
    )
    sch.components.add(
        "Device:R",
        "R70",
        "0R DNP_BOOT_OVERRIDE",
        pos(52, 42),
    )

    for name, p in [
        ("3V3", pos(34, 18)),
        ("GND", pos(34, 54)),
        ("SWDIO", pos(34, 26)),
        ("SWCLK", pos(34, 31)),
        ("SWO", pos(34, 36)),
        ("NRST", pos(66, 30)),
        ("BOOT0", pos(66, 42)),
    ]:
        sch.add_label(name, position=p)

    sch.add_text(
        "Primary Tag-Connect SWD connector remains captured with MCU_CORE.\n"
        "SW1 pulls NRST low; R70 is a DNP service override only.",
        position=pos(18, 61),
        size=1.0,
    )

def populate_text_sheet(sch, title: str, notes: list[str]) -> None:
    sch.add_text(
        title + "\n" + "\n".join(notes),
        position=pos(18, 12),
        size=1.27,
    )


HIERARCHY_PIN_TYPES = {
    "input",
    "output",
    "bidirectional",
    "passive",
}


def load_hierarchy_interface(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
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
                "HIERARCHY_INTERFACE_SYS_001.csv missing required columns"
            )
        rows = list(reader)

    for row in rows:
        pin_type = str(
            row.get("pin_type", "")
        ).strip()
        if pin_type not in HIERARCHY_PIN_TYPES:
            raise ValueError(
                f"invalid hierarchy pin type:{pin_type}"
            )

    return rows


def hierarchy_rows_for_sheet(
    rows: list[dict[str, str]],
    sheet_name: str,
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if str(
            row.get("sheet", "")
        ).strip()
        == sheet_name
    ]


def sheet_pin_edge(
    pin_type: str,
) -> str:
    return {
        "input": "left",
        "output": "right",
        "bidirectional": "top",
        "passive": "bottom",
    }[pin_type]


def sheet_pin_root_position(
    sheet_position: tuple[float, float],
    sheet_size: tuple[float, float],
    edge: str,
    offset: float,
) -> tuple[float, float]:
    x, y = sheet_position
    width, height = sheet_size

    if edge == "left":
        return (x, y + height - offset)
    if edge == "right":
        return (x + width, y + offset)
    if edge == "top":
        return (x + offset, y)
    if edge == "bottom":
        return (x + offset, y + height)

    raise ValueError(
        f"unsupported sheet pin edge:{edge}"
    )


def normalize_serialized_hierarchy_shapes(
    schematic_path: Path,
    rows: list[dict[str, str]],
) -> None:
    """Correct hierarchical-label shapes after kicad-sch-api serialization.

    kicad-sch-api 0.x currently serializes generated hierarchical labels
    as input regardless of the requested electrical type.  The contract
    remains authoritative, so patch only the shape token immediately
    following each known hierarchical label.  Real kicad-cli ERC then
    validates the resulting native KiCad schematic.
    """
    text = schematic_path.read_text(encoding="utf-8")

    for row in rows:
        net_name = str(row["net_name"]).strip()
        pin_type = str(row["pin_type"]).strip()
        pattern = (
            r'(\(hierarchical_label\s+"'
            + re.escape(net_name)
            + r'"\s*\n\s*\(shape\s+)'
            + r'(input|output|bidirectional|tri_state|passive)'
            + r'(\))'
        )
        text, count = re.subn(
            pattern,
            lambda match: (
                match.group(1)
                + pin_type
                + match.group(3)
            ),
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(
                "unable to normalize hierarchical label:"
                f"{net_name}:{pin_type}:{schematic_path.name}"
            )

    schematic_path.write_text(text, encoding="utf-8")


def add_child_hierarchy_labels(
    sch,
    rows: list[dict[str, str]],
) -> None:
    for row in rows:
        net_name = str(
            row["net_name"]
        ).strip()
        pin_type = str(
            row["pin_type"]
        ).strip()
        reference = str(
            row["anchor_ref"]
        ).strip()
        pin_number = str(
            row["anchor_pin"]
        ).strip()

        position = (
            sch.get_component_pin_position(
                reference,
                pin_number,
            )
        )
        if position is None:
            raise ValueError(
                "hierarchy anchor missing:"
                f"{reference}:{pin_number}:{net_name}"
            )

        shape = {
            "input": HierarchicalLabelShape.INPUT,
            "output": HierarchicalLabelShape.OUTPUT,
            "bidirectional":
                HierarchicalLabelShape.BIDIRECTIONAL,
            "passive":
                HierarchicalLabelShape.PASSIVE,
        }[pin_type]

        # kicad-sch-api hierarchy validation keys off the
        # hierarchical label electrical type. Prefer the explicit
        # label_type API; retain shape as a compatibility fallback.
        try:
            sch.add_hierarchical_label(
                text=net_name,
                label_type=pin_type,
                position=(
                    position.x,
                    position.y,
                ),
            )
        except TypeError:
            sch.add_hierarchical_label(
                text=net_name,
                position=(
                    position.x,
                    position.y,
                ),
                shape=shape,
            )


def build(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).resolve().parents[1]
    local_symbol_path = output_dir / f"{LOCAL_SYMBOL_LIBRARY}.kicad_sym"
    local_symbol_manifest = generate_local_symbols(
        pin_contract=(
            repo_root
            / "hardware"
            / "system_carrier"
            / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
        ),
        footprint_plan=(
            repo_root
            / "hardware"
            / "system_carrier"
            / "FOOTPRINT_PLAN_SYS_001.csv"
        ),
        aux_pin_contract=(
            repo_root
            / "hardware"
            / "system_carrier"
            / "AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv"
        ),
        output=local_symbol_path,
    )

    local_fp_source = (
        repo_root
        / "hardware"
        / "system_carrier"
        / "footprints"
        / "SystemCarrier_Local.pretty"
    )
    local_fp_output = (
        output_dir
        / "SystemCarrier_Local.pretty"
    )
    shutil.copytree(
        local_fp_source,
        local_fp_output,
        dirs_exist_ok=True,
    )
    (output_dir / "fp-lib-table").write_text(
        "(fp_lib_table\n"
        "  (lib (name \"SystemCarrier_Local\") "
        "(type \"KiCad\") "
        "(uri \"${KIPRJMOD}/SystemCarrier_Local.pretty\") "
        "(options \"\") "
        "(descr \"RLS Head System Carrier local footprints\"))\n"
        ")\n",
        encoding="utf-8",
    )

    write_symbol_library_table(output_dir)

    symbol_cache = ksa.library.get_symbol_cache()
    symbol_cache.add_library_path(
        str(local_symbol_path)
    )

    pinmap_path = (
        repo_root
        / "hardware"
        / "system_carrier"
        / "PINMAP_SYS_001.csv"
    )
    pinmap_rows = load_mcu_pinmap(
        pinmap_path
    )
    assigned_mcu_gpio = load_assigned_mcu_gpio(
        pinmap_path
    )
    symbol_pin_contract_rows = load_symbol_pin_contract(
        repo_root
        / "hardware"
        / "system_carrier"
        / "SYMBOL_PIN_CONTRACT_SYS_001.csv"
    )

    hierarchy_interface_path = (
        repo_root
        / "hardware"
        / "system_carrier"
        / "HIERARCHY_INTERFACE_SYS_001.csv"
    )
    hierarchy_rows = load_hierarchy_interface(
        hierarchy_interface_path
    )

    main = ksa.create_schematic(PROJECT_NAME)
    parent_uuid = main.uuid
    placeholders: list[dict] = []
    mcu_unused_gpio_no_connect_count = 0

    sheet_uuids: dict[str, str] = {}
    sheet_geometry: dict[
        str,
        tuple[
            tuple[float, float],
            tuple[float, float],
        ],
    ] = {}

    for index, (name, filename) in enumerate(SHEETS):
        col = index % 2
        row = index // 2
        sheet_position = (
            30.48 + 101.6 * col,
            25.4 + 50.8 * row,
        )
        sheet_size = (88.9, 38.1)

        sheet_uuid = main.sheets.add_sheet(
            name=name,
            filename=filename,
            position=sheet_position,
            size=sheet_size,
            project_name=PROJECT_NAME,
            page_number=str(index + 2),
        )
        sheet_uuids[name] = str(sheet_uuid)
        sheet_geometry[name] = (
            sheet_position,
            sheet_size,
        )

        rows = hierarchy_rows_for_sheet(
            hierarchy_rows,
            name,
        )
        by_type_count = {
            pin_type: 0
            for pin_type in HIERARCHY_PIN_TYPES
        }

        for item in rows:
            pin_type = str(
                item["pin_type"]
            ).strip()
            edge = sheet_pin_edge(
                pin_type
            )
            by_type_count[pin_type] += 1
            offset = (
                2.54
                * by_type_count[pin_type]
            )

            main.sheets.add_sheet_pin(
                sheet_uuid,
                str(
                    item["net_name"]
                ).strip(),
                pin_type,
                edge,
                offset,
            )

            root_position = (
                sheet_pin_root_position(
                    sheet_position,
                    sheet_size,
                    edge,
                    offset,
                )
            )
            stub = 5.08
            if edge == "left":
                label_position = (
                    root_position[0] - stub,
                    root_position[1],
                )
            elif edge == "right":
                label_position = (
                    root_position[0] + stub,
                    root_position[1],
                )
            elif edge == "top":
                label_position = (
                    root_position[0],
                    root_position[1] - stub,
                )
            else:
                label_position = (
                    root_position[0],
                    root_position[1] + stub,
                )
            main.wires.add(
                start=root_position,
                end=label_position,
            )
            main.add_label(
                str(
                    item["net_name"]
                ).strip(),
                position=label_position,
            )

    main.add_text(
        "EVT System Carrier\n"
        "External radar front-end: TI AWR2944PEVM\n"
        "Carrier contains no 76–81 GHz RF routing",
        position=pos(18, 8),
        size=1.27,
    )
    main.save(str(output_dir / f"{PROJECT_NAME}.kicad_sch"))

    for name, filename in SHEETS:
        child = ksa.create_schematic(PROJECT_NAME)
        child.set_hierarchy_context(parent_uuid, sheet_uuids[name])

        if name == "POWER_INPUT":
            populate_power(child, placeholders)
        elif name == "MCU_CORE":
            mcu_unused_gpio_no_connect_count = (
                populate_mcu(
                    child,
                    placeholders,
                    assigned_mcu_gpio,
                    pinmap_rows,
                )
            )
        elif name == "TIME_GNSS":
            populate_time_gnss(
                child,
                placeholders,
            )
        elif name == "IMU":
            populate_imu(
                child,
                placeholders,
            )
        elif name == "RADAR_IO_CAN":
            populate_radar_io_can(
                child,
                placeholders,
            )
        elif name == "ETHERNET":
            populate_ethernet(
                child,
                placeholders,
            )
        elif name == "DEBUG_BOOT":
            populate_debug_boot(
                child,
                placeholders,
            )

        sheet_hierarchy_rows = hierarchy_rows_for_sheet(
            hierarchy_rows,
            name,
        )
        hierarchy_nets = {
            str(row["net_name"]).strip()
            for row in sheet_hierarchy_rows
        }

        contract_refs_by_sheet = {
            "TIME_GNSS": {"U8"},
            "IMU": {"U2"},
            "RADAR_IO_CAN": {"U4"},
            "ETHERNET": {"U3"},
        }
        if name in contract_refs_by_sheet:
            apply_symbol_pin_contract(
                child,
                symbol_pin_contract_rows,
                contract_refs_by_sheet[name],
                hierarchy_nets,
            )

        add_child_hierarchy_labels(
            child,
            sheet_hierarchy_rows,
        )

        child_path = output_dir / filename
        child.save(str(child_path))
        normalize_serialized_hierarchy_shapes(
            child_path,
            hierarchy_rows_for_sheet(
                hierarchy_rows,
                name,
            ),
        )

    (output_dir / f"{PROJECT_NAME}.kicad_pro").write_text(
        json.dumps(
            {
                "meta": {
                    "filename": f"{PROJECT_NAME}.kicad_pro",
                    "version": 1,
                },
                "text_variables": {},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = {
        "schema": STATUS_SCHEMA,
        "status": "CAD_SCAFFOLD_READY",
        "project": PROJECT_NAME,
        "root_schematic": f"{PROJECT_NAME}.kicad_sch",
        "sheet_count": len(SHEETS) + 1,
        "child_sheets": [filename for _, filename in SHEETS],
        "sheet_uuids": sheet_uuids,
        "hierarchy_interface_contract":
            "HIERARCHY_INTERFACE_SYS_001.csv",
        "hierarchy_interface_count":
            len(hierarchy_rows),
        "local_symbol_library": local_symbol_path.name,
        "local_symbol_manifest": local_symbol_manifest,
        "local_footprint_library": "SystemCarrier_Local.pretty",
        "fp_lib_table": "fp-lib-table",
        "sym_lib_table": "sym-lib-table",
        "symbol_library_bindings": dict(SYMBOL_LIBRARIES),
        "symbol_placeholders": placeholders,
        "mcu_assigned_gpio_count": len(
            assigned_mcu_gpio
        ),
        "mcu_unused_gpio_no_connect_count":
            mcu_unused_gpio_no_connect_count,
        "notes": [
            "This is an authoritative generated CAD scaffold, not Review A.",
            "POWER_INPUT and MCU_CORE contain initial capture content.",
            "Local U2/U4/U5/U6/U7/Y2/D3/D4 symbols are generated from authoritative pin contracts.",
            "Remaining placeholder symbols must be replaced before CARRIER_REVIEW_A.",
            "Real KiCad ERC is generated in CI and may contain expected capture-stage violations.",
        ],
    }

    (output_dir / "cad_scaffold_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the authoritative EVT System Carrier KiCad scaffold"
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    result = build(Path(args.output_dir))
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
