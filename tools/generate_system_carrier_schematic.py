from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import kicad_sch_api as ksa

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
        "POWER_INPUT — Rev A capture scaffold\n"
        "Locked values come from SCHEMATIC_COMPONENTS_SYS_001.csv",
        position=pos(20, 10),
        size=1.27,
    )

    sch.components.add(
        "Connector_Generic:Conn_01x02",
        "J1",
        "12V_IN",
        pos(18, 24),
    )
    sch.components.add(
        "Device:D_TVS",
        "D1",
        "SMAJ15CA",
        pos(30, 24),
    )

    add_local_symbol(
        sch, "U6", "TPS259470ARPWR", "TPS259470ARPWR_SYS",
        pos(43, 24), placeholders
    )
    add_local_symbol(
        sch, "U5", "TPS62132RGTR", "TPS62132RGTR_3V3",
        pos(60, 24), placeholders
    )
    add_local_symbol(
        sch, "U7", "TPS259470ARPWR", "TPS259470ARPWR_RADAR",
        pos(43, 42), placeholders
    )

    sch.components.add("Device:L", "L1", "2.2uH", pos(72, 24))
    sch.components.add("Device:C", "C1", "10uF/25V", pos(55, 36))
    sch.components.add("Device:C", "C2", "22uF/6.3V", pos(76, 36))
    sch.components.add("Device:C", "C3", "3.3nF", pos(64, 36))
    sch.components.add("Device:R", "R1", "665R 1%", pos(39, 34))
    sch.components.add("Device:R", "R2", "1.05k 1%", pos(39, 52))
    sch.components.add("Device:R", "R6F", "10k 1% FLT_PU", pos(48, 34))
    sch.components.add("Device:R", "R7F", "10k 1% FLT_PU", pos(48, 52))
    sch.components.add(
        "Connector_Generic:Conn_01x02",
        "J2",
        "RADAR_12V_OUT",
        pos(75, 50),
    )

    for name, p in [
        ("12V_IN", pos(22, 18)),
        ("VIN_RAW", pos(31, 18)),
        ("VIN_PROTECTED", pos(46, 18)),
        ("3V3", pos(76, 18)),
        ("RADAR_12V", pos(68, 47)),
        ("SYS_EFUSE_FLT", pos(50, 30)),
        ("RADAR_EFUSE_FLT", pos(50, 48)),
        ("GND", pos(53, 58)),
    ]:
        sch.add_label(name, position=p)


def populate_mcu(sch, placeholders: list[dict]) -> None:
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

    for name, p in [
        ("3V3", pos(26, 18)),
        ("GND", pos(26, 52)),
        ("GNSS_PPS", pos(74, 18)),
        ("RADAR_REF", pos(74, 22)),
        ("IMU_DRDY", pos(74, 26)),
        ("SWDIO", pos(77, 49)),
        ("SWCLK", pos(77, 53)),
    ]:
        sch.add_label(name, position=p)




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
        add_placeholder(
            sch,
            "U8",
            "NEO-M9N-00B",
            pos(50, 32),
            placeholders,
        )
    sch.components.add(
        "Device:D_TVS",
        "D8",
        "ESD0P2RF-02LS",
        pos(72, 28),
        footprint="SystemCarrier_Local:ESD0P2RF-02LS_PG-TSSLP-2-1",
        MPN="ESD0P2RF-02LS",
    )

    sch.components.add(
        "Connector_Generic:Conn_01x02",
        "J8",
        "GNSS_UFL",
        pos(86, 28),
    )
    sch.components.add(
        "Device:C",
        "C80",
        "100nF",
        pos(36, 42),
    )
    sch.components.add(
        "Device:C",
        "C81",
        "10uF",
        pos(42, 42),
    )
    sch.components.add(
        "Device:L",
        "L80",
        "27nH DNP_OPTION",
        pos(72, 42),
    )
    sch.components.add(
        "Device:R",
        "R80",
        "10R 0.25W DNP_OPTION",
        pos(64, 48),
    )
    sch.components.add(
        "Device:C",
        "C82",
        "100nF DNP_OPTION",
        pos(78, 48),
    )
    sch.components.add(
        "Device:R",
        "R81",
        "100k 1% VUSB_PD",
        pos(57, 48),
    )

    for name, p in [
        ("3V3", pos(34, 18)),
        ("GND", pos(34, 55)),
        ("GNSS_TX_EXT", pos(34, 28)),
        ("GNSS_RX_EXT", pos(34, 34)),
        ("GNSS_PPS", pos(62, 20)),
        ("GNSS_RF", pos(78, 28)),
    ]:
        sch.add_label(name, position=p)

    sch.add_text(
        "L80/R80/C82 are optional active-antenna bias population.\n"
        "R81 pulls unused V_USB to GND. D8 must sit immediately behind the antenna connector.",
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

    sch.components.add(
        "Device:C",
        "C20",
        "100nF",
        pos(38, 42),
    )
    sch.components.add(
        "Device:C",
        "C21",
        "2.2uF",
        pos(45, 42),
    )
    sch.components.add(
        "Device:C",
        "C22",
        "10nF",
        pos(52, 42),
    )

    for name, p in [
        ("3V3", pos(34, 18)),
        ("GND", pos(34, 54)),
        ("IMU_NSS", pos(34, 26)),
        ("IMU_SCK", pos(34, 31)),
        ("IMU_MISO", pos(34, 36)),
        ("IMU_MOSI", pos(34, 41)),
        ("IMU_DRDY", pos(70, 28)),
    ]:
        sch.add_label(name, position=p)

    sch.add_text(
        "C20/C21 are local VDD decoupling. C22 is the dedicated VDDIO 10nF bypass.\n"
        "Unused RESV/FSYNC pins are resolved by the final pin contract, not by an arbitrary pull resistor.",
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
        sch,
        "U4",
        "TCAN3404DRBRQ1",
        "TCAN3404DRBRQ1",
        pos(50, 30),
        placeholders,
    )
    add_local_symbol(
        sch,
        "D4",
        "ESD2CANFD24DBZRQ1",
        "ESD2CANFD24-Q1",
        pos(68, 30),
        placeholders,
    )

    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J4",
        "RADAR_IO",
        pos(86, 32),
    )
    sch.components.add(
        "Connector_Generic:Conn_01x02",
        "J5",
        "RADAR_PWR",
        pos(86, 50),
    )
    sch.components.add(
        "Device:R",
        "R40",
        "120R 1% DNP_DEFAULT",
        pos(70, 45),
    )
    sch.components.add(
        "Device:C",
        "C40",
        "100nF",
        pos(42, 42),
    )
    sch.components.add(
        "Device:R",
        "R41",
        "10k 1% STB_PD",
        pos(52, 46),
    )
    sch.components.add(
        "Device:R",
        "R42",
        "10k 1% SHDN_PD",
        pos(59, 46),
    )

    for name, p in [
        ("3V3", pos(37, 18)),
        ("GND", pos(37, 54)),
        ("CAN_TX", pos(37, 27)),
        ("CAN_RX", pos(37, 34)),
        ("RADAR_CANH", pos(76, 25)),
        ("RADAR_CANL", pos(76, 34)),
        ("RADAR_REF", pos(76, 40)),
        ("RADAR_12V", pos(76, 50)),
    ]:
        sch.add_label(name, position=p)

    sch.add_text(
        "R40 is populated only when carrier is the CAN bus endpoint.\n"
        "R41 pulls STB low and R42 pulls SHDN low for deterministic normal mode. RADAR_REF requires adjacent ground return.",
        position=pos(18, 62),
        size=1.0,
    )


def populate_ethernet(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "ETHERNET — LAN8742A RMII instrumentation link\n"
        "Dedicated 50 MHz reference clock shared with STM32 RMII",
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

    sch.components.add(
        "Device:R",
        "R60",
        "12.1k 1%",
        pos(42, 45),
    )
    for ref, y in [
        ("R61", 42),
        ("R62", 46),
        ("R63", 50),
        ("R64", 54),
    ]:
        sch.components.add(
            "Device:R",
            ref,
            "49.9R 1%",
            pos(68, y),
        )

    sch.components.add(
        "Device:C",
        "C60",
        "1uF",
        pos(50, 45),
    )
    sch.components.add(
        "Device:C",
        "C61",
        "470pF C0G",
        pos(56, 45),
    )
    sch.components.add(
        "Device:C",
        "C62",
        "100nF",
        pos(36, 45),
    )
    sch.components.add(
        "Device:R",
        "R65",
        "10k 1% NRST_PD",
        pos(58, 51),
    )

    for name, p in [
        ("3V3", pos(34, 17)),
        ("GND", pos(34, 58)),
        ("ETH_50M", pos(34, 22)),
        ("ETH_MDIO", pos(34, 28)),
        ("ETH_MDC", pos(34, 33)),
        ("ETH_CRS_DV", pos(34, 38)),
        ("ETH_RXD0", pos(34, 43)),
        ("ETH_RXD1", pos(34, 48)),
        ("ETH_TX_EN", pos(61, 24)),
        ("ETH_TXD0", pos(61, 29)),
        ("ETH_TXD1", pos(61, 34)),
        ("ETH_NRST", pos(61, 39)),
        ("ETH_MDI", pos(78, 31)),
    ]:
        sch.add_label(name, position=p)

    sch.add_text(
        "R60 = PHY RBIAS. R61-R64 = 49.9R MDI termination.\n"
        "C60 = VDDCR, C61 = analog filter, C62 = local bypass.\n"
        "R65 holds nRST low until STM32 PE4 releases it after the required startup delay.",
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

    symbol_cache = ksa.library.get_symbol_cache()
    symbol_cache.add_library_path(
        str(local_symbol_path)
    )

    main = ksa.create_schematic(PROJECT_NAME)
    parent_uuid = main.uuid
    placeholders: list[dict] = []

    sheet_uuids: dict[str, str] = {}
    for index, (name, filename) in enumerate(SHEETS):
        col = index % 2
        row = index // 2
        sheet_uuid = main.sheets.add_sheet(
            name=name,
            filename=filename,
            position=(30.48 + 101.6 * col, 25.4 + 50.8 * row),
            size=(88.9, 38.1),
            project_name=PROJECT_NAME,
            page_number=str(index + 2),
        )
        sheet_uuids[name] = str(sheet_uuid)

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
            populate_mcu(child, placeholders)
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

        child.save(str(output_dir / filename))

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
        "local_symbol_library": local_symbol_path.name,
        "local_symbol_manifest": local_symbol_manifest,
        "local_footprint_library": "SystemCarrier_Local.pretty",
        "fp_lib_table": "fp-lib-table",
        "symbol_placeholders": placeholders,
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
