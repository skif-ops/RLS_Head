from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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
    ("HOST_UART", "60_HOST_UART.kicad_sch"),
    ("DEBUG_BOOT", "70_DEBUG_BOOT.kicad_sch"),
]

# Move symbols and their pin-derived labels together when sizing child pages.
SHEET_ORIGIN_MM = (0.0, 0.0)
SHEET_GRID_SCALE = (1.0, 1.0)
CURRENT_SHEET_NAME = ""

CHILD_PAGE_LAYOUT = {
    "POWER_INPUT": ("A4", (80.01, 49.53), (1.0, 1.0)),
    "MCU_CORE": ("A3", (30.48, 40.64), (1.0, 1.0)),
    "TIME_GNSS": ("A5", (10.0, 8.0), (1.35, 1.25)),
    "IMU": ("A5", (10.0, 8.0), (1.6, 1.3)),
    "RADAR_IO_CAN": ("A5", (10.0, 8.0), (1.25, 1.25)),
    "HOST_UART": ("A5", (10.0, 8.0), (1.4, 1.25)),
    "DEBUG_BOOT": ("A5", (10.0, 8.0), (1.7, 1.35)),
}

PLACEHOLDER_LIB = "Connector_Generic:Conn_01x08"

SYMBOL_LIBRARIES = {
    "SystemCarrier_Local": "${KIPRJMOD}/SystemCarrier_Local.kicad_sym",
    "Device": "${KICAD9_SYMBOL_DIR}/Device.kicad_sym",
    "Connector_Generic": "${KICAD9_SYMBOL_DIR}/Connector_Generic.kicad_sym",
    "Connector": "${KICAD9_SYMBOL_DIR}/Connector.kicad_sym",
    "Switch": "${KICAD9_SYMBOL_DIR}/Switch.kicad_sym",
    "power": "${KICAD9_SYMBOL_DIR}/power.kicad_sym",
    "MCU_ST_STM32H7": "${KICAD9_SYMBOL_DIR}/MCU_ST_STM32H7.kicad_sym",
}

# Contract names for Altium native patterns use KiCad stock geometry as an
# import bridge. Native pad geometry still requires the separate Altium audit.
ALTIUM_IMPORT_BRIDGES = {
    "Molex_43650-0200_RA_THT_2P": (
        "Connector_Molex",
        "Molex_Micro-Fit_3.0_43650-0200_1x02_P3.00mm_Horizontal",
    ),
    "Molex_43045-0600_RA_THT_6P": (
        "Connector_Molex",
        "Molex_Micro-Fit_3.0_43045-0600_2x03_P3.00mm_Horizontal",
    ),
    "Hirose_UFL_R_SMT_K": (
        "Connector_Coaxial",
        "U.FL_Hirose_U.FL-R-SMT-1_Vertical",
    ),
    "TagConnect_TC2030_NL": (
        "Connector",
        "Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
    ),
    "Coilcraft_XFL4020_4x4": (
        "Inductor_SMD",
        "L_Coilcraft_XxL4020",
    ),
    "ESwitch_TL3301_GullWing_6x6": (
        "Button_Switch_SMD",
        "SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG",
    ),
}


def find_stock_footprints() -> Path:
    candidates = [
        os.environ.get("KICAD_FOOTPRINT_DIR", ""),
        os.environ.get("KICAD9_FOOTPRINT_DIR", ""),
        os.environ.get("KICAD10_FOOTPRINT_DIR", ""),
        "/usr/share/kicad/footprints",
        str(
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "KiCad/10.0/share/kicad/footprints"
        ),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "Capacitor_SMD.pretty").is_dir():
            return Path(candidate)
    raise FileNotFoundError("KiCad stock footprint libraries not found")


def stage_import_footprints(
    output_dir: Path,
    assignments: dict[str, str],
) -> dict:
    stock_root = find_stock_footprints()
    records: list[dict[str, str | bool]] = []
    for identifier in sorted(set(assignments.values())):
        library, name = identifier.split(":", 1)
        if library == "SystemCarrier_Local":
            continue
        bridge = library == "SystemCarrier_Altium"
        source_library, source_name = (
            ALTIUM_IMPORT_BRIDGES[name]
            if bridge
            else (library, name)
        )
        source = stock_root / f"{source_library}.pretty" / f"{source_name}.kicad_mod"
        if not source.is_file():
            raise FileNotFoundError(f"Missing KiCad footprint: {source}")
        content = source.read_bytes()
        if bridge:
            original = f'(footprint "{source_name}"'.encode()
            alias = f'(footprint "{name}"'.encode()
            if not content.startswith(original):
                raise ValueError(f"Unexpected KiCad footprint header: {source}")
            content = alias + content[len(original):]
        target = output_dir / f"{library}.pretty" / f"{name}.kicad_mod"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append(
            {
                "footprint_id": identifier,
                "source_library": source_library,
                "source_name": source_name,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "staged_sha256": hashlib.sha256(content).hexdigest(),
                "altium_import_bridge": bridge,
            }
        )
    manifest = {
        "schema": "SYSTEM-CARRIER-FOOTPRINT-IMPORT-STAGING-001",
        "status": "STAGED_FOR_IMPORT",
        "stock_footprint_root": str(stock_root),
        "records": records,
        "native_geometry_audit_required": True,
    }
    (output_dir / "footprint_import_staging.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


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


def load_footprint_assignments(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        if rows.fieldnames is None or not {"ref", "footprint_id"}.issubset(
            rows.fieldnames
        ):
            raise ValueError("FOOTPRINT_ASSIGNMENT_SYS_002.csv missing columns")
        assignments: dict[str, str] = {}
        for row in rows:
            reference = str(row["ref"] or "").strip()
            footprint = str(row["footprint_id"] or "").strip()
            if not reference or not footprint or ":" not in footprint:
                raise ValueError(f"Invalid footprint assignment: {reference}")
            if reference in assignments:
                raise ValueError(f"Duplicate footprint assignment: {reference}")
            assignments[reference] = footprint
    return assignments


def apply_symbol_pin_contract(
    sch,
    rows: list[dict[str, str]],
    references: set[str],
    hierarchy_nets: set[str],
) -> dict[str, int]:
    direct_prefixes = (
        "IMU_",
        "HOST_UART",
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


def load_bom_mpn(bom_path: Path) -> dict[str, str]:
    with bom_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        if rows.fieldnames is None:
            raise ValueError("BOM_SYS_CARRIER_LAYOUT_004.csv missing header")
        result: dict[str, str] = {}
        for row in rows:
            reference = str(row.get("ref", "")).strip()
            mpn = str(row.get("value_or_mpn", "")).strip()
            if not reference or not mpn or reference in result:
                raise ValueError(f"Invalid BOM reference or MPN: {reference}")
            result[reference] = mpn
    return result


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


def add_power_flag(
    sch,
    reference: str,
    net_name: str,
    position: tuple[float, float],
) -> None:
    sch.components.add(
        "power:PWR_FLAG",
        reference,
        "PWR_FLAG",
        position,
    )
    add_pin_label(
        sch,
        net_name,
        reference,
        "1",
    )


def add_pin_label(
    sch,
    net_name: str,
    reference: str,
    pin_number: str,
) -> None:
    pin = sch.get_component_pin_position(
        reference,
        pin_number,
    )
    if pin is None:
        raise ValueError(
            f"missing pin:{reference}:{pin_number}"
        )

    # Vertical power parts need label stubs clear of their values.
    if reference in {
        "R61", "R62", "R63", "R71", "R72", "R73", "R1", "R2",
        "R5P", "R6F", "R7F", "R90", "C1", "C2", "C3", "C4",
        "C90", "C91", "C92", "C93", "L1", "L9",
    }:
        component = sch.components.get(reference)
        direction = -1.0 if pin.y < component.position.y else 1.0
        end = (pin.x, pin.y + direction * 5.08)
        sch.wires.add(start=(pin.x, pin.y), end=end)
        sch.add_label(net_name, position=end)
        return

    if reference == "J1":
        end = (pin.x - 7.62, pin.y)
        sch.wires.add(start=(pin.x, pin.y), end=end)
        sch.labels.add(net_name, end, justify_h="right")
        sch._sync_labels_to_data()
        return

    # These power labels need room outside their symbol bodies.
    if reference in {"D1", "U5", "U6", "U7", "U9"}:
        component = sch.components.get(reference)
        dx = pin.x - component.position.x
        dy = pin.y - component.position.y
        if abs(dx) >= abs(dy):
            end = (pin.x + (10.16 if dx >= 0 else -10.16), pin.y)
            justify_h = "left" if dx >= 0 else "right"
        else:
            end = (pin.x, pin.y + (10.16 if dy >= 0 else -10.16))
            justify_h = "left"
        sch.wires.add(start=(pin.x, pin.y), end=end)
        sch.labels.add(net_name, end, justify_h=justify_h)
        sch._sync_labels_to_data()
        return

    if CURRENT_SHEET_NAME == "MCU_CORE":
        add_oriented_label_at_pin(sch, net_name, reference, pin_number)
    elif CURRENT_SHEET_NAME == "POWER_INPUT":
        sch.add_label(net_name, pin=(reference, pin_number))
    else:
        add_pin_label_stub(sch, net_name, reference, pin_number, stub=5.08)


def add_oriented_label_at_pin(
    sch, net_name: str, reference: str, pin_number: str
) -> None:
    component = sch.components.get(reference)
    pin = sch.get_component_pin_position(reference, pin_number)
    if component is None or pin is None:
        raise ValueError(f"missing pin:{reference}:{pin_number}")
    definition = next(
        (item for item in component.pins if str(item.number) == pin_number),
        None,
    )
    if definition is None:
        raise ValueError(f"missing pin definition:{reference}:{pin_number}")
    horizontal = (definition.rotation + component.rotation) % 180 == 0
    direction = (
        1.0 if pin.x >= component.position.x else -1.0
    ) if horizontal else (
        1.0 if pin.y >= component.position.y else -1.0
    )
    sch.labels.add(
        net_name,
        (pin.x, pin.y),
        rotation=0 if horizontal else 90,
        justify_h=(
            "left" if direction > 0 else "right"
        ) if horizontal else (
            "right" if direction > 0 else "left"
        ),
    )
    sch._sync_labels_to_data()


def add_pin_label_stub(
    sch,
    net_name: str,
    reference: str,
    pin_number: str,
    *,
    stub: float = 5.08,
    size: float = 1.27,
) -> None:
    pin = sch.get_component_pin_position(
        reference,
        pin_number,
    )
    if pin is None:
        raise ValueError(
            f"missing pin:{reference}:{pin_number}"
        )

    component = sch.components.get(reference)
    if component is None:
        raise ValueError(
            f"missing component:{reference}"
        )

    pin_definition = next(
        (item for item in component.pins if str(item.number) == pin_number),
        None,
    )
    if pin_definition is None:
        raise ValueError(f"missing pin definition:{reference}:{pin_number}")

    horizontal = (pin_definition.rotation + component.rotation) % 180 == 0
    if horizontal:
        direction = 1.0 if pin.x >= component.position.x else -1.0
        end = (
            pin.x + direction * stub,
            pin.y,
        )
        rotation = 0
        justify_h = "left" if direction > 0 else "right"
    else:
        direction = 1.0 if pin.y >= component.position.y else -1.0
        end = (
            pin.x,
            pin.y + direction * stub,
        )
        rotation = 90
        justify_h = "left" if direction < 0 else "right"

    sch.wires.add(
        start=(pin.x, pin.y),
        end=end,
    )
    sch.labels.add(
        net_name,
        end,
        rotation=rotation,
        justify_h=justify_h,
        size=size,
    )
    sch._sync_labels_to_data()


def add_labels_by_pin_name(
    sch,
    reference: str,
    mapping: dict[str, str],
    *,
    skip_pin_numbers: set[str] | None = None,
) -> None:
    component = sch.components.get(reference)
    if component is None:
        raise ValueError(f"missing component:{reference}")

    skip = skip_pin_numbers or set()

    for pin in component.pins:
        pin_number = str(pin.number).strip()
        if pin_number in skip:
            continue

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
    return (
        1.27 * x_grid * SHEET_GRID_SCALE[0] + SHEET_ORIGIN_MM[0],
        1.27 * y_grid * SHEET_GRID_SCALE[1] + SHEET_ORIGIN_MM[1],
    )


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


def add_stock_pin_stub_label(
    sch,
    net_name: str,
    reference: str,
    pin_number: str,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
) -> None:
    pin = sch.get_component_pin_position(
        reference,
        pin_number,
    )
    if pin is None:
        raise ValueError(
            f"missing pin:{reference}:{pin_number}"
        )
    end = (
        pin.x + dx,
        pin.y + dy,
    )
    sch.wires.add(
        start=(pin.x, pin.y),
        end=end,
    )
    sch.add_label(
        net_name,
        position=end,
    )


def add_tps25947_dvdt_labels(
    sch,
    reference: str,
    capacitor_reference: str,
    net_name: str,
) -> None:
    component = sch.components.get(reference)
    if component is None:
        raise ValueError(f"missing component:{reference}")

    add_pin_label(sch, net_name, reference, "7")

    cap_pin = sch.get_component_pin_position(
        capacitor_reference,
        "1",
    )
    if cap_pin is None:
        raise ValueError(
            f"missing pin:{capacitor_reference}:1"
        )
    sch.add_label(
        net_name,
        position=(cap_pin.x, cap_pin.y),
    )


def add_tps25947_ground_label(
    sch,
    reference: str,
) -> None:
    component = sch.components.get(reference)
    if component is None:
        raise ValueError(f"missing component:{reference}")

    ground_pin = sch.get_component_pin_position(reference, "8")
    if ground_pin is None:
        raise ValueError(f"missing pin:{reference}:8")
    pin = (ground_pin.x, ground_pin.y)
    end = (
        pin[0] + 1.27,
        pin[1],
    )
    sch.wires.add(
        start=pin,
        end=end,
    )
    sch.add_label(
        "GND",
        position=end,
    )


def populate_power(sch, placeholders: list[dict]) -> None:
    def power_pos(x_grid: int, y_grid: int) -> tuple[float, float]:
        return (32.0 + (x_grid - 18) * 3.9, 34.0 + (y_grid - 18) * 2.65)

    sch.add_text(
        "POWER_INPUT — Rev A authoritative capture\n"
        "TPS259470A protection + fixed 3.3V and external GNSS 5V rails",
        position=(70.0, 20.0),
        size=1.5,
    )

    sch.components.add("Connector_Generic:Conn_01x02", "J1", "12V_IN", power_pos(22, 24))
    sch.components.add("Device:D_TVS", "D1", "SMAJ15CA", power_pos(26, 18))
    add_local_symbol(sch, "U6", "TPS259470ARPWR", "SYS_EFUSE", power_pos(39, 24), placeholders)
    add_local_symbol(sch, "U5", "TPS62132RGTR", "3V3_BUCK", power_pos(64, 17), placeholders)
    add_local_symbol(sch, "U9", "TPS62133RGTR", "5V_GNSS_BUCK", power_pos(64, 46), placeholders)
    add_local_symbol(sch, "U7", "TPS259470ARPWR", "RADAR_EFUSE", power_pos(39, 42), placeholders)

    sch.components.add("Device:L", "L1", "2.2uH", power_pos(78, 17))
    sch.components.add("Device:L", "L9", "2.2uH", power_pos(78, 46))
    sch.components.add("Device:C", "C1", "10uF/25V", power_pos(55, 36))
    sch.components.add("Device:C", "C2", "22uF/6.3V", power_pos(76, 36))
    sch.components.add("Device:C", "C3", "3.3nF", power_pos(64, 36))
    sch.components.add("Device:C", "C4", "100nF/25V", power_pos(58, 40))
    sch.components.add("Device:R", "R1", "665R 1%", power_pos(39, 34))
    sch.components.add("Device:R", "R2", "1.05k 1%", power_pos(39, 52))
    sch.components.add("Device:R", "R5P", "100k 1% PG_PU", power_pos(68, 34))
    sch.components.add("Device:C", "C90", "10uF/25V", power_pos(52, 60))
    sch.components.add("Device:C", "C91", "22uF/10V", power_pos(76, 60))
    sch.components.add("Device:C", "C92", "3.3nF", power_pos(64, 60))
    sch.components.add("Device:C", "C93", "100nF/25V", power_pos(58, 60))
    sch.components.add("Device:R", "R90", "100k 1% PG_PU", power_pos(68, 58))
    sch.components.add("Device:R", "R6F", "10k 1% FLT_PU", power_pos(48, 34))
    sch.components.add("Device:R", "R7F", "10k 1% FLT_PU", power_pos(48, 52))

    for ref, value, p in [
        ("R61", "470k 1%", power_pos(25, 26)), ("R62", "36.0k 1%", power_pos(29, 30)), ("R63", "41.2k 1%", power_pos(33, 34)),
        ("R71", "470k 1%", power_pos(25, 48)), ("R72", "16.9k 1%", power_pos(29, 52)), ("R73", "43.7k 1%", power_pos(33, 56)),
    ]:
        sch.components.add("Device:R", ref, value, p)

    sch.components.add("Device:C", "C6D", "3.3nF", power_pos(43, 36))
    sch.components.add("Device:C", "C7D", "3.3nF", power_pos(43, 54))
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0201",
        "PWR_FLAG",
        power_pos(20, 28),
    )
    add_pin_label(sch, "VIN_RAW", "#FLG0201", "1")
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0202",
        "PWR_FLAG",
        (30.0, 170.0),
    )
    add_pin_label(sch, "GND", "#FLG0202", "1")

    add_pin_label(sch, "VIN_RAW", "J1", "1")
    # J1.2 receives the authoritative hierarchical GND label later.
    add_pin_label(sch, "VIN_RAW", "D1", "1")
    add_pin_label(sch, "GND", "D1", "2")

    for pin, net in {"5":"VIN_RAW","6":"VIN_PROTECTED"}.items():
        add_pin_label(sch, net, "U6", pin)
    add_tps25947_ground_label(sch, "U6")
    add_pin_label(sch, "VIN_RAW", "R61", "1")
    for ref, pin in (("R61", "2"), ("U6", "1"), ("R62", "1")):
        add_pin_label(sch, "U6_UVLO_LOCAL", ref, pin)
    for ref, pin in (("R62", "2"), ("U6", "2"), ("R63", "1")):
        add_pin_label(sch, "U6_OVLO_LOCAL", ref, pin)
    add_pin_label(sch, "GND", "R63", "2")
    add_pin_label(sch, "U6_ILIM_LOCAL", "U6", "9")
    add_pin_label(sch, "U6_ILIM_LOCAL", "R1", "1")
    add_pin_label(sch, "GND", "R1", "2")
    add_tps25947_dvdt_labels(
        sch, "U6", "C6D", "U6_DVDT"
    )
    add_stock_pin_stub_label(
        sch, "GND", "C6D", "2", dx=1.27
    )
    add_pin_label(sch, "SYS_EFUSE_FLT", "R6F", "1")
    add_pin_label(sch, "3V3", "R6F", "2")
    for pin in ("3","10"):
        p=sch.get_component_pin_position("U6", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))

    add_pin_label(sch, "VIN_PROTECTED", "U7", "5")
    add_tps25947_ground_label(sch, "U7")
    add_pin_label(sch, "VIN_PROTECTED", "R71", "1")
    for ref, pin in (("R71", "2"), ("U7", "1"), ("R72", "1")):
        add_pin_label(sch, "U7_UVLO_LOCAL", ref, pin)
    for ref, pin in (("R72", "2"), ("U7", "2"), ("R73", "1")):
        add_pin_label(sch, "U7_OVLO_LOCAL", ref, pin)
    add_pin_label(sch, "GND", "R73", "2")
    add_pin_label(sch, "U7_ILIM_LOCAL", "U7", "9")
    add_pin_label(sch, "U7_ILIM_LOCAL", "R2", "1")
    add_pin_label(sch, "GND", "R2", "2")
    add_tps25947_dvdt_labels(
        sch, "U7", "C7D", "U7_DVDT"
    )
    add_stock_pin_stub_label(
        sch, "GND", "C7D", "2", dx=1.27
    )
    add_pin_label(sch, "RADAR_EFUSE_FLT", "R7F", "1")
    add_pin_label(sch, "3V3", "R7F", "2")
    for pin in ("3","10"):
        p=sch.get_component_pin_position("U7", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))

    for pin in ("1","2","3"):
        add_pin_label(sch, "BUCK_SW", "U5", pin)
    add_pin_label(sch, "BUCK_SW", "L1", "1")
    # L1.2 receives the authoritative hierarchical 3V3 label later.
    add_pin_label(sch, "U5_PG", "U5", "4")
    add_pin_label(sch, "U5_PG", "R5P", "1")
    add_pin_label(sch, "3V3", "R5P", "2")
    for pin in ("5","6","15","16","17"):
        if sch.get_component_pin_position("U5", pin) is not None:
            add_pin_label(sch, "GND", "U5", pin)
    for pin in ("7","8"):
        p=sch.get_component_pin_position("U5", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x,p.y))
    add_pin_label(sch, "U5_SS_LOCAL", "U5", "9")
    add_pin_label(sch, "U5_SS_LOCAL", "C3", "1")
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

    for pin in ("1", "2", "3"):
        add_pin_label(sch, "BUCK5_SW", "U9", pin)
    add_pin_label(sch, "BUCK5_SW", "L9", "1")
    add_pin_label(sch, "U9_PG", "U9", "4")
    add_pin_label(sch, "U9_PG", "R90", "1")
    add_pin_label(sch, "5V_GNSS", "R90", "2")
    for pin in ("5", "6", "15", "16", "17"):
        if sch.get_component_pin_position("U9", pin) is not None:
            add_pin_label(sch, "GND", "U9", pin)
    for pin in ("7", "8"):
        p = sch.get_component_pin_position("U9", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))
    add_pin_label(sch, "U9_SS_LOCAL", "U9", "9")
    add_pin_label(sch, "U9_SS_LOCAL", "C92", "1")
    add_pin_label(sch, "GND", "C92", "2")
    for pin in ("10", "11", "12", "13"):
        add_pin_label(sch, "VIN_PROTECTED", "U9", pin)
    add_pin_label(sch, "5V_GNSS", "U9", "14")
    add_pin_label(sch, "VIN_PROTECTED", "C90", "1")
    add_pin_label(sch, "GND", "C90", "2")
    add_pin_label(sch, "5V_GNSS", "C91", "1")
    add_pin_label(sch, "GND", "C91", "2")
    add_pin_label(sch, "VIN_PROTECTED", "C93", "1")
    add_pin_label(sch, "GND", "C93", "2")


def populate_mcu(
    sch,
    placeholders: list[dict],
    assigned_gpio: set[str],
    pinmap_rows: list[dict[str, str]],
    hierarchy_nets: set[str],
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
            pos(180, 87),
            footprint="Package_QFP:LQFP-176_24x24mm_P0.5mm",
            MPN="STM32H753IIT6",
        )
    except Exception:
        add_placeholder(
            sch,
            "U1",
            "STM32H753IIT6",
            pos(180, 87),
            placeholders,
        )

    sch.components.add("Device:C", "C10", "2.2uF", pos(25, 75))
    sch.components.add("Device:C", "C11", "2.2uF", pos(25, 90))
    sch.components.add("Device:C", "C12", "4.7uF", pos(25, 105))
    sch.components.add("Device:C", "C13", "100nF", pos(80, 50))
    sch.components.add("Device:R", "R10", "10k 1%", pos(80, 80))
    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J10",
        "TC2030_SWD",
        pos(80, 100),
    )
    add_local_symbol(
        sch,
        "Y1",
        "ECS-2520S33-250-FN-TR",
        "25MHz_OSC",
        pos(30, 25),
        placeholders,
    )
    sch.components.add(
        "Device:C",
        "C15",
        "100nF",
        pos(45, 55),
    )

    # One 100nF capacitor per STM32 VDD pin, plus USB supply and NRST filter.
    vdd_pins = (
        "15", "23", "36", "49", "62", "72", "82",
        "91", "103", "127", "136", "149", "159", "172",
    )
    for index, pin_number in enumerate(vdd_pins):
        ref = f"C{100 + index}"
        x = 100 if index < 7 else 120
        y = 20 + 8 * (index % 7)
        sch.components.add(
            "Device:C",
            ref,
            "100nF VDD",
            pos(x, y),
            Decouples_U1_Pin=pin_number,
        )
        add_pin_label(sch, "3V3", ref, "1")
        add_pin_label(sch, "GND", ref, "2")

    sch.components.add(
        "Device:C",
        "C114",
        "100nF VDD33_USB",
        pos(100, 85),
        Decouples_U1_Pin="114",
    )
    add_pin_label(sch, "3V3", "C114", "1")
    add_pin_label(sch, "GND", "C114", "2")

    sch.components.add(
        "Device:C",
        "C115",
        "100nF NRST",
        pos(120, 85),
        Filters_U1_Pin="31",
    )
    add_pin_label(sch, "NRST", "C115", "1")
    add_pin_label(sch, "GND", "C115", "2")
    tp1 = sch.components.add(
        "Connector:TestPoint",
        "TP1",
        "HOST_UART1_TX",
        pos(100, 105),
        footprint="TestPoint:TestPoint_Pad_D1.0mm",
    )
    tp2 = sch.components.add(
        "Connector:TestPoint",
        "TP2",
        "HOST_UART1_RX",
        pos(120, 105),
        footprint="TestPoint:TestPoint_Pad_D1.0mm",
    )
    tp1.in_bom = False
    tp2.in_bom = False

    validate_mcu_pinmap_against_symbol(
        sch,
        pinmap_rows,
    )

    # Power-domain support components required by the Rev.A contract.
    sch.components.add(
        "Device:L_Ferrite",
        "FB1",
        "BLM18BD601SH1",
        pos(65, 35),
        MPN="BLM18BD601SH1",
    )
    sch.components.add(
        "Device:C",
        "C14",
        "1uF",
        pos(65, 65),
    )
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0101",
        "PWR_FLAG",
        pos(45, 110),
    )
    sch.components.add(
        "power:PWR_FLAG",
        "#FLG0103",
        "PWR_FLAG",
        pos(75, 110),
    )

    # Bind every assigned MCU signal directly to the authoritative net name.
    for row in pinmap_rows:
        physical = str(
            row.get("physical_pin", "")
        ).strip()
        net_name = str(
            row.get("net_name", "")
        ).strip()
        if (
            physical
            and net_name
            and net_name not in hierarchy_nets
            and net_name != "MCU_HSE_25M"
        ):
            add_pin_label(
                sch,
                net_name,
                "U1",
                physical,
            )

    # Dedicated 25 MHz STM32 HSE oscillator.
    # ECS-2520S pin1 may be NC for active operation.
    p = sch.get_component_pin_position("Y1", "1")
    if p is not None:
        sch.no_connects.add(position=(p.x, p.y))
    add_pin_label(sch, "GND", "Y1", "2")
    add_pin_label(sch, "MCU_HSE_25M", "Y1", "3")
    add_pin_label(sch, "MCU_HSE_25M", "U1", "29")
    add_pin_label(sch, "HOST_UART1_TX", "TP1", "1")
    add_pin_label(sch, "HOST_UART1_RX", "TP2", "1")
    add_pin_label(sch, "3V3", "Y1", "4")
    add_pin_label(sch, "3V3", "C15", "1")
    add_pin_label(sch, "GND", "C15", "2")

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
        skip_pin_numbers={"23", "14"},
    )

    # VCAP pins each receive their own 2.2 uF low-ESR capacitor.
    add_pin_label(sch, "VCAP1_LOCAL", "U1", "81")
    add_pin_label(sch, "VCAP1_LOCAL", "C10", "1")
    add_pin_label(sch, "GND", "C10", "2")
    add_pin_label(sch, "VCAP2_LOCAL", "U1", "125")
    add_pin_label(sch, "VCAP2_LOCAL", "C11", "1")
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
    add_pin_label(sch, "BOOT0", "R10", "1")
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
        "VDDA_FILTERED",
        "#FLG0103",
        "1",
    )

    return mark_unused_mcu_gpio_no_connect(
        sch,
        assigned_gpio,
    )



def populate_time_gnss(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "TIME_GNSS — external simpleRTK3B Pro / mosaic-X5 interface\n"
        "Optional untrusted GNSS aiding: 5V, USART3 and 3.3V PPS",
        position=(82.0, 18.0),
        size=1.5,
    )

    add_local_symbol(
        sch,
        "D8",
        "TPD4E05U06DQAR",
        "UART_PPS_ESD",
        pos(45, 34),
        placeholders,
    )
    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J8",
        "EXT_GNSS_PIXHAWK",
        pos(96, 44),
        MPN="SM06B-GHS-TB(LF)(SN)",
    )

    for pin, net in {
        "1": "GNSS_RX_EXT",
        "2": "GNSS_TX_EXT",
        "4": "GNSS_PPS",
    }.items():
        add_pin_label_stub(sch, net, "D8", pin)
    add_pin_label_stub(sch, "GND", "D8", "3")
    add_pin_label_stub(sch, "GND", "D8", "8")
    for pin in ("5", "6", "7", "9", "10"):
        p = sch.get_component_pin_position("D8", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))

    event_pin = sch.get_component_pin_position("J8", "5")
    if event_pin is not None:
        sch.no_connects.add(position=(event_pin.x, event_pin.y))

    sch.add_text(
        "J8 Pixhawk adapter: 1 5V, 2 receiver RX,\n"
        "3 receiver TX, 4 PPS, 5 event NC, 6 GND.\n"
        "D8 protects UART/PPS. The receiver may be absent\n"
        "or quarantined without stopping carrier operation.",
        position=(55.0, 95.0),
        size=1.1,
    )


def populate_imu(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "IMU — ICM-42688-P SPI2 + hardware DRDY\n"
        "P0 IMU_DRDY -> STM32 PB11/TIM2_CH4",
        position=(82.0, 18.0),
        size=1.5,
    )

    add_local_symbol(
        sch,
        "U2",
        "ICM-42688-P",
        "IMU",
        pos(52, 31),
        placeholders,
    )

    sch.components.add("Device:C", "C20", "100nF", pos(38, 42))
    sch.components.add("Device:C", "C21", "2.2uF", pos(45, 42))
    sch.components.add("Device:C", "C22", "10nF", pos(52, 42))

    # VDDIO and mandatory ground/unused-function handling from the
    # authoritative ICM-42688-P pin contract.
    add_pin_label_stub(sch, "3V3", "U2", "5")
    add_pin_label_stub(sch, "GND", "U2", "7")
    add_pin_label_stub(sch, "GND", "U2", "9")

    # Local VDD/VDDIO decoupling.
    add_pin_label_stub(sch, "3V3", "C20", "1")
    add_pin_label_stub(sch, "GND", "C20", "2")
    add_pin_label_stub(sch, "3V3", "C21", "1")
    add_pin_label_stub(sch, "GND", "C21", "2")
    add_pin_label_stub(sch, "3V3", "C22", "1")
    add_pin_label_stub(sch, "GND", "C22", "2")

    sch.add_text(
        "C20/C21: VDD decoupling. C22: 10nF VDDIO.\n"
        "Pin7 RESV and pin9 FSYNC connect to GND\n"
        "per the Rev.A pin contract.",
        position=(55.0, 95.0),
        size=1.1,
    )


def populate_radar_io_can(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "RADAR_IO_CAN — external AWR2944-class EVM interface\n"
        "CAN-FD control/metadata + P0 RADAR_REF timestamp + protected 12V",
        position=(82.0, 18.0),
        size=1.5,
    )

    add_local_symbol(
        sch, "U4", "TCAN3404DRBRQ1", "CAN_FD",
        pos(50, 30), placeholders
    )
    add_local_symbol(
        sch, "D4", "ESD2CANFD24DBZRQ1", "CAN_ESD",
        pos(100, 30), placeholders
    )

    sch.components.add("Connector_Generic:Conn_01x06", "J4", "RADAR_IO", pos(116, 32))
    sch.components.add("Connector_Generic:Conn_01x02", "J5", "RADAR_PWR", pos(116, 50))
    sch.components.add("Device:R", "R40", "120R", pos(88, 53))
    sch.components.add("Device:C", "C40", "100nF", pos(42, 42))
    sch.components.add("Device:R", "R41", "10k", pos(52, 46))
    sch.components.add("Device:R", "R42", "10k", pos(59, 46))

    # Transceiver local power and exposed-pad ground.
    add_pin_label_stub(sch, "3V3", "C40", "1")
    add_pin_label_stub(sch, "GND", "C40", "2")
    if sch.get_component_pin_position("U4", "9") is not None:
        add_pin_label_stub(sch, "GND", "U4", "9")

    # Deterministic normal mode defaults.
    add_pin_label_stub(sch, "STB_PD", "U4", "8")
    add_pin_label_stub(sch, "STB_PD", "R41", "1")
    add_pin_label_stub(sch, "GND", "R41", "2")
    add_pin_label_stub(sch, "SHDN_PD", "U4", "5")
    add_pin_label_stub(sch, "SHDN_PD", "R42", "1")
    add_pin_label_stub(sch, "GND", "R42", "2")

    # CAN bus and ESD.
    add_pin_label_stub(sch, "RADAR_CANH", "D4", "1")
    add_pin_label_stub(sch, "RADAR_CANL", "D4", "2")
    add_pin_label_stub(sch, "GND", "D4", "3")

    # Radar I/O connector according to CONNECTOR_PINOUT_SYS_001.csv.
    add_pin_label_stub(sch, "RADAR_CANL", "J4", "1")
    add_pin_label_stub(sch, "GND", "J4", "2")
    add_pin_label_stub(sch, "RADAR_CANH", "J4", "3")
    add_pin_label_stub(sch, "GND", "J4", "5")
    p = sch.get_component_pin_position("J4", "6")
    if p is not None:
        sch.no_connects.add(position=(p.x, p.y))

    # Optional endpoint termination across CANH/CANL.
    add_pin_label_stub(sch, "RADAR_CANH", "R40", "1")
    add_pin_label_stub(sch, "RADAR_CANL", "R40", "2")

    # Protected radar power connector.
    add_pin_label_stub(sch, "GND", "J5", "2")

    sch.add_text(
        "R40 120R 1% is DNP by default.\n"
        "Populate only at the CAN endpoint.\n"
        "R41/R42 10k 1% select normal mode.\n"
        "J4 pin6 is NC by Rev.A contract.",
        position=(55.0, 96.0),
        size=1.1,
    )


def populate_host_uart(sch, placeholders: list[dict]) -> None:
    sch.add_text(
        "HOST_UART — two independent 3.3V UART interfaces\n"
        "USART2 on PD5/PD6 + USART1 on PA9/PA10; TX/RX/GND only",
        position=(82.0, 18.0),
        size=1.5,
    )

    add_local_symbol(
        sch,
        "D3",
        "TPD4E05U06DQAR",
        "DUAL_UART_ESD",
        pos(62, 39),
        placeholders,
    )
    sch.components.add(
        "Connector_Generic:Conn_01x06",
        "J6",
        "HOST_UART_2X",
        pos(96, 38),
        MPN="43045-0600",
    )

    sch.components.add("Device:R", "R600", "10k", pos(50, 31))
    sch.components.add("Device:R", "R605", "10k", pos(50, 57))
    for ref, x, y in [
        ("R601", 45, 25), ("R602", 45, 38),
        ("R603", 45, 51), ("R604", 45, 64),
    ]:
        sch.components.add("Device:R", ref, "33R", pos(x, y))

    for ref in ("R600", "R605", "R601", "R602", "R603", "R604"):
        sch.components.get(ref).rotation = 270

    series_nets = {
        "R601": ("HOST_UART1_TX", "HOST_UART1_TX_EXT"),
        "R602": ("HOST_UART1_RX", "HOST_UART1_RX_EXT"),
        "R603": ("HOST_UART2_TX", "HOST_UART2_TX_EXT"),
        "R604": ("HOST_UART2_RX", "HOST_UART2_RX_EXT"),
    }
    for ref, (mcu_net, connector_net) in series_nets.items():
        add_pin_label_stub(sch, connector_net, ref, "2")

    add_pin_label_stub(sch, "HOST_UART1_RX", "R600", "1")
    add_pin_label_stub(sch, "HOST_UART2_RX", "R605", "1")
    add_pin_label_stub(sch, "3V3", "R605", "2")

    add_pin_label_stub(sch, "GND", "D3", "3")
    add_pin_label_stub(sch, "GND", "D3", "8")

    channel_pins = {
        "HOST_UART1_TX_EXT": ("1", "2"),
        "HOST_UART1_RX_EXT": ("2", "3"),
        "HOST_UART2_TX_EXT": ("4", "5"),
        "HOST_UART2_RX_EXT": ("5", "6"),
    }
    for net_name, (esd_pin, connector_pin) in channel_pins.items():
        add_pin_label_stub(sch, net_name, "D3", esd_pin, stub=7.62, size=1.0)
        add_pin_label_stub(sch, net_name, "J6", connector_pin, stub=7.62, size=1.0)

    for pin in ("6", "7", "9", "10"):
        p = sch.get_component_pin_position("D3", pin)
        if p is not None:
            sch.no_connects.add(position=(p.x, p.y))

    add_pin_label_stub(sch, "GND", "J6", "4")

    sch.add_text(
        "J6: 1 GND, 2 U1 TX, 3 U1 RX,\n"
        "4 GND, 5 U2 TX, 6 U2 RX.\n"
        "R601-R604: 33R series. R600/R605: 10k RX pull-ups.\n"
        "D3 protects all four signal lines.\n"
        "No supply voltage is exported.",
        position=(45.0, 119.0),
        size=1.0,
    )


def populate_debug_boot(sch, placeholders: list[dict]) -> None:
    del placeholders

    sch.add_text(
        "DEBUG_BOOT — SWD, reset and boot service access\n"
        "No vehicle actuation/control interfaces",
        position=(82.0, 18.0),
        size=1.5,
    )

    sch.components.add(
        "Switch:SW_Push",
        "SW1",
        "NRST",
        pos(35, 30),
    )
    sch.components.add(
        "Device:R",
        "R70",
        "0R",
        pos(80, 48),
    )

    sch.add_text(
        "Primary Tag-Connect SWD remains on MCU_CORE.\n"
        "SW1 pulls NRST low. R70 is a DNP\n"
        "service override only.",
        position=(55.0, 95.0),
        size=1.1,
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

        position_pin_number = pin_number
        if CURRENT_SHEET_NAME == "HOST_UART" and reference in {
            "R600", "R601", "R602", "R603", "R604"
        }:
            # kicad-sch-api 0.5.6 returns the opposite graphical endpoint for
            # vertically rotated two-pin resistors.
            position_pin_number = "2" if pin_number == "1" else "1"

        position = (
            sch.get_component_pin_position(
                reference,
                position_pin_number,
            )
        )
        if position is None:
            raise ValueError(
                "hierarchy anchor missing:"
                f"{reference}:{pin_number}:{net_name}"
            )

        # Keep the child port on a short wire. KiCad treats a label placed
        # directly on a pin as connected, but Altium's KiCad importer can
        # leave that same imported port detached from its component pin.
        component = sch.components.get(reference)
        if component is None:
            raise ValueError(f"hierarchy component missing:{reference}")
        legacy_layout = CURRENT_SHEET_NAME in {"POWER_INPUT", "MCU_CORE"}
        if legacy_layout:
            dx = position.x - component.position.x
            dy = position.y - component.position.y
            stub = 25.4 if reference in {"U6", "U7"} else (
                12.7 if reference == "J1" else 1.27
            )
            if CURRENT_SHEET_NAME == "MCU_CORE":
                definition = next(
                    (pin for pin in component.pins if str(pin.number) == pin_number),
                    None,
                )
                if definition is None:
                    raise ValueError(
                        f"missing hierarchy pin:{reference}:{pin_number}"
                    )
                horizontal = (
                    definition.rotation + component.rotation
                ) % 180 == 0
                if horizontal:
                    stub = 25.4
            else:
                horizontal = abs(dx) >= abs(dy)
            if horizontal:
                label_position = (
                    position.x + (stub if dx >= 0 else -stub),
                    position.y,
                )
            else:
                label_position = (
                    position.x,
                    position.y + (stub if dy >= 0 else -stub),
                )
        else:
            pin_definition = next(
                (pin for pin in component.pins if str(pin.number) == pin_number),
                None,
            )
            if pin_definition is None:
                raise ValueError(f"missing hierarchy pin:{reference}:{pin_number}")
            horizontal = (pin_definition.rotation + component.rotation) % 180 == 0
            direction = (
                1.0 if position.x >= component.position.x else -1.0
            ) if horizontal else (
                1.0 if position.y >= component.position.y else -1.0
            )
            stub = (
                66.04
                if horizontal
                and direction < 0
                and reference in {
                    "U2", "J8", "U4", "R601", "R602", "R603", "R604"
                }
                else 20.32 if horizontal and reference in {"J4", "J5", "J6"}
                else 35.56 if horizontal
                else 20.32
            )
            if horizontal:
                label_position = (position.x + direction * stub, position.y)
            else:
                label_position = (position.x, position.y + direction * stub)
        sch.wires.add(
            start=(position.x, position.y),
            end=label_position,
        )

        # Keep the imported PCB net name bound to the hierarchy contract.
        # Ports alone can compile to generic NetU1_* names when Altium is
        # configured to avoid using port names as global net identifiers.
        if legacy_layout:
            net_label_position = (
                (position.x - 6.35, position.y)
                if reference == "J1" else (position.x, position.y)
            )
            if CURRENT_SHEET_NAME == "MCU_CORE":
                add_oriented_label_at_pin(
                    sch, net_name, reference, pin_number
                )
            else:
                sch.add_label(net_name, position=net_label_position)
        else:
            net_label_position = (
                (position.x + direction * 5.08, position.y)
                if horizontal else (position.x, position.y + direction * 5.08)
            )
            sch.labels.add(
                net_name,
                net_label_position,
                rotation=0 if horizontal else 90,
                justify_h=(
                    "left" if direction > 0 else "right"
                ) if horizontal else (
                    "right" if direction > 0 else "left"
                ),
            )
            sch._sync_labels_to_data()

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
                position=label_position,
            )
        except TypeError:
            sch.add_hierarchical_label(
                text=net_name,
                position=label_position,
                shape=shape,
            )


def build(output_dir: Path) -> dict:
    global SHEET_ORIGIN_MM, SHEET_GRID_SCALE, CURRENT_SHEET_NAME
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
    footprint_assignments = load_footprint_assignments(
        repo_root
        / "hardware"
        / "system_carrier"
        / "FOOTPRINT_ASSIGNMENT_SYS_002.csv"
    )
    bom_mpn = load_bom_mpn(
        repo_root
        / "hardware"
        / "system_carrier"
        / "BOM_SYS_CARRIER_LAYOUT_004.csv"
    )
    footprint_staging = stage_import_footprints(
        output_dir, footprint_assignments
    )
    footprint_libraries = {
        identifier.split(":", 1)[0]
        for identifier in footprint_assignments.values()
    }
    fp_table = ["(fp_lib_table"]
    for library in sorted(footprint_libraries):
        fp_table.append(
            f'  (lib (name "{library}") (type "KiCad") '
            f'(uri "${{KIPRJMOD}}/{library}.pretty") '
            '(options "") (descr "System Carrier import footprint"))'
        )
    fp_table.append(")")
    (output_dir / "fp-lib-table").write_text(
        "\n".join(fp_table) + "\n", encoding="utf-8"
    )
    assigned_footprint_refs: set[str] = set()

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
    main.set_paper_size("A2")
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
            45.72 + 294.64 * col,
            40.64 + 91.44 * row,
        )
        sheet_size = (190.5, 76.2)

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
            offset = 3.81 * by_type_count[pin_type]

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
            stub = 20.32 if edge in {"left", "right"} else 5.08
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
            net_name = str(item["net_name"]).strip()
            main.labels.add(
                net_name,
                label_position,
                rotation=0 if edge in {"left", "right"} else 90,
                justify_h=(
                    "right" if edge == "left" else "left"
                ) if edge in {"left", "right"} else (
                    "right" if edge == "top" else "left"
                ),
                size=1.5,
            )
            main._sync_labels_to_data()

            for sheet in main._data["sheets"]:
                if sheet["uuid"] == sheet_uuid:
                    sheet["pins"][-1]["size"] = 1.5
                    break

    main.add_text(
        "EVT System Carrier\n"
        "External radar front-end: TI AWR2944PEVM\n"
        "Carrier contains no 76–81 GHz RF routing",
        position=(45.72, 17.78),
        size=1.8,
    )
    main.save(str(output_dir / f"{PROJECT_NAME}.kicad_sch"))

    for name, filename in SHEETS:
        CURRENT_SHEET_NAME = name
        child = ksa.create_schematic(PROJECT_NAME)
        paper_size, SHEET_ORIGIN_MM, SHEET_GRID_SCALE = CHILD_PAGE_LAYOUT[name]
        child.set_paper_size(paper_size)
        child.set_hierarchy_context(parent_uuid, sheet_uuids[name])

        sheet_hierarchy_rows = hierarchy_rows_for_sheet(
            hierarchy_rows,
            name,
        )
        hierarchy_nets = {
            str(row["net_name"]).strip()
            for row in sheet_hierarchy_rows
        }

        if name == "POWER_INPUT":
            populate_power(child, placeholders)
        elif name == "MCU_CORE":
            mcu_unused_gpio_no_connect_count = (
                populate_mcu(
                    child,
                    placeholders,
                    assigned_mcu_gpio,
                    pinmap_rows,
                    hierarchy_nets,
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
        elif name == "HOST_UART":
            populate_host_uart(
                child,
                placeholders,
            )
        elif name == "DEBUG_BOOT":
            populate_debug_boot(
                child,
                placeholders,
            )

        contract_refs_by_sheet = {
            "IMU": {"U2"},
            "RADAR_IO_CAN": {"U4"},
            "HOST_UART": {"D3"},
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

        for component in child.components:
            reference = component.reference
            for property_name in tuple(component.properties):
                if property_name in {
                    "Reference", "Value", "Footprint",
                    "Datasheet", "Description",
                } or property_name.startswith("__"):
                    continue
                component.add_property(
                    property_name,
                    component.get_property(property_name, ""),
                    hidden=True,
                )
            capture_status = component.get_property("Capture_Status")
            if capture_status:
                component.add_property(
                    "Capture_Status", capture_status, hidden=True
                )
            if component.get_property("hierarchy_path"):
                component.add_property(
                    "hierarchy_path",
                    component.get_property("hierarchy_path"),
                    hidden=True,
                )
            if reference.startswith("#FLG"):
                continue
            if reference not in footprint_assignments:
                raise ValueError(f"Missing footprint contract: {reference}")
            if reference in assigned_footprint_refs:
                raise ValueError(f"Duplicate schematic reference: {reference}")
            expected_mpn = bom_mpn.get(reference)
            if expected_mpn is None:
                raise ValueError(f"Missing BOM reference: {reference}")
            imported_mpn = component.get_property("MPN", "")
            if imported_mpn and imported_mpn != expected_mpn:
                raise ValueError(
                    f"BOM MPN mismatch: {reference}:"
                    f"{imported_mpn}!={expected_mpn}"
                )
            component.add_property("MPN", expected_mpn, hidden=True)
            component.footprint = footprint_assignments[reference]
            assigned_footprint_refs.add(reference)

        child_path = output_dir / filename
        child.save(str(child_path))
        normalize_serialized_hierarchy_shapes(
            child_path,
            hierarchy_rows_for_sheet(
                hierarchy_rows,
                name,
            ),
        )

    missing_footprint_refs = set(footprint_assignments) - assigned_footprint_refs
    if missing_footprint_refs:
        raise ValueError(
            "Footprint assignments absent from schematic: "
            + ", ".join(sorted(missing_footprint_refs))
        )
    missing_bom_refs = set(bom_mpn) - assigned_footprint_refs
    if missing_bom_refs:
        raise ValueError(
            "BOM references absent from schematic: "
            + ", ".join(sorted(missing_bom_refs))
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
        "footprint_assignment_count": len(assigned_footprint_refs),
        "staged_footprint_count": len(footprint_staging["records"]),
        "altium_import_bridge_count": sum(
            bool(record["altium_import_bridge"])
            for record in footprint_staging["records"]
        ),
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
            "Local U2/U4/U5/U6/U7/U9/Y1/D3/D4/D8 symbols are generated from authoritative pin contracts.",
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
