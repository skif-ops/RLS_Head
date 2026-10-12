from __future__ import annotations

import argparse
import json
from pathlib import Path

import kicad_sch_api as ksa


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
            "sheet": sch.name,
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
        "D_IN",
        "SMAJ15CA",
        pos(30, 24),
    )

    add_placeholder(
        sch, "U6", "TPS259470ARPWR_SYS", pos(43, 24), placeholders
    )
    add_placeholder(
        sch, "U5", "TPS62132RGTR_3V3", pos(60, 24), placeholders
    )
    add_placeholder(
        sch, "U7", "TPS259470ARPWR_RADAR", pos(43, 42), placeholders
    )

    sch.components.add("Device:L", "L1", "2.2uH", pos(72, 24))
    sch.components.add("Device:C", "C_U5_IN", "10uF/25V", pos(55, 36))
    sch.components.add("Device:C", "C_U5_OUT", "22uF/6.3V", pos(76, 36))
    sch.components.add("Device:C", "C_U5_SS", "3.3nF", pos(64, 36))
    sch.components.add("Device:R", "R_U6_ILIM", "665R 1%", pos(39, 34))
    sch.components.add("Device:R", "R_U7_ILIM", "1.05k 1%", pos(39, 52))
    sch.components.add(
        "Connector_Generic:Conn_01x02",
        "J_RADAR_PWR",
        "RADAR_12V_OUT",
        pos(75, 50),
    )

    for name, p in [
        ("12V_IN", pos(22, 18)),
        ("VIN_RAW", pos(31, 18)),
        ("VIN_PROTECTED", pos(46, 18)),
        ("3V3", pos(76, 18)),
        ("RADAR_12V", pos(68, 47)),
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

    sch.components.add("Device:C", "C_VCAP1", "2.2uF", pos(27, 25))
    sch.components.add("Device:C", "C_VCAP2", "2.2uF", pos(27, 33))
    sch.components.add("Device:C", "C_VDD_BULK", "4.7uF", pos(27, 41))
    sch.components.add("Device:C", "C_NRST", "100nF", pos(83, 26))
    sch.components.add("Device:R", "R_BOOT0", "10k 1%", pos(83, 38))
    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J_SWD",
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


def populate_text_sheet(sch, title: str, notes: list[str]) -> None:
    sch.add_text(
        title + "\n" + "\n".join(notes),
        position=pos(18, 12),
        size=1.27,
    )


def build(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

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
            populate_text_sheet(
                child,
                "TIME_GNSS",
                [
                    "U8 NEO-M9N-00B — symbol capture pending",
                    "GNSS_PPS -> STM32 PA0/TIM2_CH1",
                    "GNSS antenna: U.FL + ESD0P2RF-02LS",
                ],
            )
        elif name == "IMU":
            populate_text_sheet(
                child,
                "IMU",
                [
                    "U2 ICM-42688-P — symbol capture pending",
                    "SPI2 + hardware IMU_DRDY",
                ],
            )
        elif name == "RADAR_IO_CAN":
            populate_text_sheet(
                child,
                "RADAR_IO_CAN",
                [
                    "U4 TCAN3404DRBRQ1 — symbol capture pending",
                    "J_RADAR_IO CAN-FD + P0 RADAR_REF",
                    "J_RADAR_PWR protected RADAR_12V",
                ],
            )
        elif name == "ETHERNET":
            populate_text_sheet(
                child,
                "ETHERNET",
                [
                    "U3 LAN8742Ai-CZ-TR — symbol capture pending",
                    "50 MHz RMII clock, RBIAS 12.1k, MagJack",
                ],
            )
        elif name == "DEBUG_BOOT":
            populate_text_sheet(
                child,
                "DEBUG_BOOT",
                [
                    "SWDIO/SWCLK/SWO, target VREF, NRST, BOOT0",
                    "No vehicle actuation/control interfaces",
                ],
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
        "symbol_placeholders": placeholders,
        "notes": [
            "This is an authoritative generated CAD scaffold, not Review A.",
            "POWER_INPUT and MCU_CORE contain initial capture content.",
            "Placeholder symbols must be replaced before CARRIER_REVIEW_A.",
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
