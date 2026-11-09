from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


C_M_S = 299_792_458.0
TARGET_FREQUENCY_HZ = 78.5e9
CHECK_FREQUENCIES_HZ = (76.0e9, 78.5e9, 81.0e9)
TARGET_NETS = {
    204: "TI_RX1",
    205: "TI_RX2",
    206: "TI_RX3",
    207: "TI_RX4",
    220: "TI_TX1",
    221: "TI_TX2",
    222: "TI_TX3",
    223: "TI_TX4",
}
OLD_TRACK_INDEX_RANGE = range(5199, 5247)
OLD_FILL_INDEX_RANGE = range(0, 16)
PATCH_WIDTHS_MM = (1.35, 1.05, 0.82, 0.65, 0.65, 0.82, 1.05, 1.35)
PATCH_LENGTH_MM = 1.08
PITCH_LAMBDA_0 = 0.40
FEED_WIDTH_MIL = 8.4016
SERIES_WIDTH_MIL = 4.0000
MASK_EXPANSION_MIL = 3.937
PATCH_OVERLAP_MIL = 0.9843
TRUNK_OFFSET_MM = -0.95
CORNER_CHAMFER_MM = 0.05
RO3003_RELATIVE_PERMITTIVITY = 3.0
RO3003_HEIGHT_MM = 0.127
SERIES_WIDTH_MM = SERIES_WIDTH_MIL * 0.0254
PHASE_TARGET_INNER_TO_OUTER_DEG = (0.0, -25.51088403, -67.98073466, -140.98684564)
PHASE_INCREMENT_DEG = tuple(
    abs(second - first)
    for first, second in zip(PHASE_TARGET_INNER_TO_OUTER_DEG, PHASE_TARGET_INNER_TO_OUTER_DEG[1:])
)
NEW_TRACK_INDEX_START = 8000
NEW_FILL_INDEX_START = 16
RF_NON_TOP_VIA_SPANS = {
    789: ("MID6", "BOTTOM"),
    793: ("MID6", "BOTTOM"),
    840: ("MID8", "BOTTOM"),
    914: ("MID6", "BOTTOM"),
    1011: ("MID6", "MID7"),
    1013: ("MID6", "MID7"),
    1044: ("MID7", "BOTTOM"),
    1334: ("MID3", "MID5"),
}
RF_REDUNDANT_VIA_INDICES = {918, 1041, 1042}
RF_ESCAPE_VIA_INDEX_START = 9000
RF_CONNECTOR_TRACK_INDEX_START = 9010
BOARD_CENTER_MM = (50.0, 50.0)
BOARD_RADIUS_MM = 39.5
BOARD_EDGE_MARGIN_MM = 0.25


@dataclass(frozen=True)
class Fill:
    net: int
    x1_mil: float
    x2_mil: float
    y1_mil: float
    y2_mil: float

    @property
    def x_center_mil(self) -> float:
        return (self.x1_mil + self.x2_mil) / 2.0

    @property
    def y_center_mil(self) -> float:
        return (self.y1_mil + self.y2_mil) / 2.0


def mil_to_mm(value: float) -> float:
    return value * 0.0254


def mm_to_mil(value: float) -> float:
    return value / 0.0254


def field(line: str, name: str) -> str | None:
    match = re.search(rf"\|{re.escape(name)}=([^|\r\n]+)", line)
    return match.group(1) if match else None


def numeric_mil(line: str, name: str) -> float:
    value = field(line, name)
    if value is None or not value.endswith("mil"):
        raise ValueError(f"missing {name}=...mil in record: {line[:120]}")
    return float(value[:-3])


def load_ascii(path: Path) -> tuple[list[str], str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("unexpected UTF-8 BOM in Altium ASCII PcbDoc")
    newline = "\r\n" if b"\r\n" in raw[:4096] else "\n"
    return raw.decode("cp1252").splitlines(), newline


def collect_old_geometry(lines: list[str]) -> tuple[dict[int, list[Fill]], dict[int, tuple[float, float]], set[int]]:
    fills: dict[int, list[Fill]] = {net: [] for net in TARGET_NETS}
    handoffs: dict[int, tuple[float, float]] = {}
    removal_lines: set[int] = set()

    for line_number, line in enumerate(lines):
        net_value = field(line, "NET")
        index_value = field(line, "INDEXFORSAVE")
        record = field(line, "RECORD")
        if net_value is None or index_value is None or record is None:
            continue
        net = int(net_value)
        if net not in TARGET_NETS:
            continue
        index = int(index_value)
        if record == "Track" and index in OLD_TRACK_INDEX_RANGE:
            removal_lines.add(line_number)
            handoffs.setdefault(net, (numeric_mil(line, "X1"), numeric_mil(line, "Y1")))
        elif record == "Fill" and index in OLD_FILL_INDEX_RANGE:
            removal_lines.add(line_number)
            fills[net].append(
                Fill(
                    net=net,
                    x1_mil=numeric_mil(line, "X1"),
                    x2_mil=numeric_mil(line, "X2"),
                    y1_mil=numeric_mil(line, "Y1"),
                    y2_mil=numeric_mil(line, "Y2"),
                )
            )

    if len(removal_lines) != 64:
        raise ValueError(f"expected 64 old antenna records, found {len(removal_lines)}")
    if set(handoffs) != set(TARGET_NETS):
        raise ValueError("not all antenna feed handoffs were found")
    for net, items in fills.items():
        if len(items) != 2:
            raise ValueError(f"{TARGET_NETS[net]}: expected two old fills, found {len(items)}")
        items.sort(key=lambda item: item.y_center_mil)
    return fills, handoffs, removal_lines


def track_record(net: int, width_mil: float, x1: float, y1: float, x2: float, y2: float, index: int) -> str:
    return (
        "|RECORD=Track|LAYER=TOP|LOCKED=FALSE|SELECTION=FALSE|USERROUTED=TRUE"
        "|UNIONINDEX=0|POLYGONOUTLINE=FALSE|SOLDERMASKEXPANSIONMODE=Manual"
        f"|PASTEMASKEXPANSIONMODE=None|NET={net}|WIDTH={width_mil:.4f}mil"
        f"|X1={x1:.4f}mil|Y1={y1:.4f}mil|X2={x2:.4f}mil|Y2={y2:.4f}mil"
        f"|SOLDERMASKEXPANSION_MANUAL={MASK_EXPANSION_MIL:.3f}mil|INDEXFORSAVE={index}"
    )


def fill_record(net: int, x_center_mil: float, y_center_mil: float, width_mm: float, index: int) -> str:
    half_width_mil = mm_to_mil(width_mm) / 2.0
    half_length_mil = mm_to_mil(PATCH_LENGTH_MM) / 2.0
    return (
        f"|RECORD=Fill|NET={net}|LAYER=TOP|SELECTION=FALSE|LOCKED=FALSE"
        "|POLYGONOUTLINE=FALSE|USERROUTED=TRUE|UNIONINDEX=0"
        "|SOLDERMASKEXPANSIONMODE=Manual"
        f"|SOLDERMASKEXPANSION_MANUAL={MASK_EXPANSION_MIL:.3f}mil"
        "|PASTEMASKEXPANSIONMODE=None"
        f"|X1={x_center_mil - half_width_mil:.4f}mil"
        f"|X2={x_center_mil + half_width_mil:.4f}mil"
        f"|Y1={y_center_mil - half_length_mil:.4f}mil"
        f"|Y2={y_center_mil + half_length_mil:.4f}mil"
        f"|ROTATION=0.0|INDEXFORSAVE={index}"
    )


def microstrip_effective_permittivity(relative_permittivity: float, width_mm: float, height_mm: float) -> float:
    ratio = width_mm / height_mm
    correction = 0.04 * (1.0 - ratio) ** 2 if ratio < 1.0 else 0.0
    return (
        (relative_permittivity + 1.0) / 2.0
        + (relative_permittivity - 1.0) / 2.0 * (1.0 / math.sqrt(1.0 + 12.0 / ratio) + correction)
    )


def phase_section_lengths_mm() -> tuple[float, ...]:
    effective_permittivity = microstrip_effective_permittivity(
        RO3003_RELATIVE_PERMITTIVITY, SERIES_WIDTH_MM, RO3003_HEIGHT_MM
    )
    guided_wavelength_mm = C_M_S / TARGET_FREQUENCY_HZ * 1000.0 / math.sqrt(effective_permittivity)
    return tuple(guided_wavelength_mm * (1.0 + value / 360.0) for value in PHASE_INCREMENT_DEG)


def delay_cell_points(
    x_center_mil: float, y_start_mil: float, y_end_mil: float, target_length_mm: float
) -> tuple[tuple[float, float], ...]:
    target_length_mil = mm_to_mil(target_length_mm)
    height_mil = abs(y_end_mil - y_start_mil)
    chamfer_mil = mm_to_mil(CORNER_CHAMFER_MM)
    chamfer_correction_mil = 4.0 * (2.0 - math.sqrt(2.0)) * chamfer_mil
    lateral_mil = (target_length_mil - height_mil + chamfer_correction_mil) / 4.0
    if lateral_mil <= chamfer_mil:
        raise ValueError("phase section is too short for the selected chamfer")
    direction = 1.0 if y_end_mil > y_start_mil else -1.0
    middle_mil = height_mil / 2.0
    local_points = (
        (0.0, 0.0),
        (-lateral_mil + chamfer_mil, 0.0),
        (-lateral_mil, chamfer_mil),
        (-lateral_mil, middle_mil - chamfer_mil),
        (-lateral_mil + chamfer_mil, middle_mil),
        (lateral_mil - chamfer_mil, middle_mil),
        (lateral_mil, middle_mil + chamfer_mil),
        (lateral_mil, height_mil - chamfer_mil),
        (lateral_mil - chamfer_mil, height_mil),
        (0.0, height_mil),
    )
    return tuple((x_center_mil + x, y_start_mil + direction * y) for x, y in local_points)


def build_new_geometry(
    old_fills: dict[int, list[Fill]], handoffs: dict[int, tuple[float, float]], array_shift_y_mm: float
) -> tuple[list[str], list[dict[str, object]]]:
    pitch_mm = PITCH_LAMBDA_0 * C_M_S / TARGET_FREQUENCY_HZ * 1000.0
    pitch_mil = mm_to_mil(pitch_mm)
    patch_length_mil = mm_to_mil(PATCH_LENGTH_MM)
    gap_mil = pitch_mil - patch_length_mil
    phase_lengths_mm = phase_section_lengths_mm()
    track_index = NEW_TRACK_INDEX_START
    fill_index = NEW_FILL_INDEX_START
    records: list[str] = []
    sections: list[dict[str, object]] = []

    for net in TARGET_NETS:
        old = old_fills[net]
        x_center = sum(item.x_center_mil for item in old) / len(old)
        first_center = old[0].y_center_mil + mm_to_mil(array_shift_y_mm)
        centers = tuple(first_center + index * pitch_mil for index in range(8))
        y_phase_center = sum(centers) / len(centers)
        handoff_x, handoff_y = handoffs[net]
        trunk_x = x_center + mm_to_mil(TRUNK_OFFSET_MM)
        split_y = (centers[3] + centers[4]) / 2.0
        lower_inner_top = centers[3] + patch_length_mil / 2.0
        upper_inner_bottom = centers[4] - patch_length_mil / 2.0
        records.append(
            track_record(
                net,
                FEED_WIDTH_MIL,
                handoff_x,
                handoff_y,
                trunk_x,
                handoff_y,
                track_index,
            )
        )
        track_index += 1
        records.append(
            track_record(net, FEED_WIDTH_MIL, trunk_x, handoff_y, trunk_x, split_y, track_index)
        )
        track_index += 1
        records.append(track_record(net, FEED_WIDTH_MIL, trunk_x, split_y, x_center, split_y, track_index))
        track_index += 1
        records.append(
            track_record(
                net,
                SERIES_WIDTH_MIL,
                x_center,
                split_y,
                x_center,
                lower_inner_top - PATCH_OVERLAP_MIL,
                track_index,
            )
        )
        track_index += 1
        records.append(
            track_record(
                net,
                SERIES_WIDTH_MIL,
                x_center,
                split_y,
                x_center,
                upper_inner_bottom + PATCH_OVERLAP_MIL,
                track_index,
            )
        )
        track_index += 1

        lower_pairs = ((3, 2), (2, 1), (1, 0))
        upper_pairs = ((4, 5), (5, 6), (6, 7))
        for phase_length_mm, pairs in zip(phase_lengths_mm, zip(lower_pairs, upper_pairs)):
            for inner_index, outer_index in pairs:
                if outer_index < inner_index:
                    start_y = centers[inner_index] - patch_length_mil / 2.0 + PATCH_OVERLAP_MIL
                    end_y = centers[outer_index] + patch_length_mil / 2.0 - PATCH_OVERLAP_MIL
                else:
                    start_y = centers[inner_index] + patch_length_mil / 2.0 - PATCH_OVERLAP_MIL
                    end_y = centers[outer_index] - patch_length_mil / 2.0 + PATCH_OVERLAP_MIL
                points = delay_cell_points(x_center, start_y, end_y, phase_length_mm)
                for start, end in zip(points, points[1:]):
                    records.append(
                        track_record(
                            net,
                            SERIES_WIDTH_MIL,
                            start[0],
                            start[1],
                            end[0],
                            end[1],
                            track_index,
                        )
                    )
                    track_index += 1

        for y_center, width_mm in zip(centers, PATCH_WIDTHS_MM):
            records.append(fill_record(net, x_center, y_center, width_mm, fill_index))
            fill_index += 1

        element_phase_deg = (
            PHASE_TARGET_INNER_TO_OUTER_DEG[3],
            PHASE_TARGET_INNER_TO_OUTER_DEG[2],
            PHASE_TARGET_INNER_TO_OUTER_DEG[1],
            PHASE_TARGET_INNER_TO_OUTER_DEG[0],
            PHASE_TARGET_INNER_TO_OUTER_DEG[0],
            PHASE_TARGET_INNER_TO_OUTER_DEG[1],
            PHASE_TARGET_INNER_TO_OUTER_DEG[2],
            PHASE_TARGET_INNER_TO_OUTER_DEG[3],
        )
        sections.append(
            {
                "net_id": net,
                "net_name": TARGET_NETS[net],
                "x_center_mm": round(mil_to_mm(x_center), 6),
                "phase_center_y_mm": round(mil_to_mm(y_phase_center), 6),
                "patch_centers_y_mm": [round(mil_to_mm(value), 6) for value in centers],
                "patch_widths_mm": list(PATCH_WIDTHS_MM),
                "patch_length_mm": PATCH_LENGTH_MM,
                "target_element_phase_deg_bottom_to_top": list(element_phase_deg),
                "phase_section_lengths_mm_inner_to_outer": [round(value, 6) for value in phase_lengths_mm],
                "feed_handoff_mm": [round(mil_to_mm(handoff_x), 6), round(mil_to_mm(handoff_y), 6)],
                "feed_topology": "center-fed symmetric two-branch series array",
            }
        )

    if len(records) != 536:
        raise ValueError(f"expected 536 new antenna records, generated {len(records)}")
    return records, sections


def insert_geometry(lines: list[str], removal_lines: set[int], new_records: list[str]) -> list[str]:
    insertion_line = min(removal_lines)
    output: list[str] = []
    for line_number, line in enumerate(lines):
        if line_number == insertion_line:
            output.extend(new_records)
        if line_number not in removal_lines:
            output.append(line)
    return output


def relocate_rf_zone_crossing_routes(lines: list[str]) -> list[str]:
    route_indices = {5183, 5184, 5185, 5188, 5189, 5190}
    source_tracks: dict[int, str] = {}
    source_vias: dict[int, str] = {}
    insertion_line = None
    for line_number, line in enumerate(lines):
        record = field(line, "RECORD")
        index = int(field(line, "INDEXFORSAVE") or -1)
        if record == "Track" and index in route_indices:
            source_tracks[index] = line
            insertion_line = line_number if insertion_line is None else min(insertion_line, line_number)
        elif record == "Via" and index in {1041, 1042}:
            source_vias[index] = line

    if set(source_tracks) != route_indices or insertion_line is None:
        raise ValueError(f"RF-zone route records mismatch: found {sorted(source_tracks)}")
    if set(source_vias) != {1041, 1042}:
        raise ValueError(f"RF-zone route via records mismatch: found {sorted(source_vias)}")
    if int(field(source_tracks[5183], "NET") or -1) != 174:
        raise ValueError("track 5183 no longer belongs to TI_NetR59_1")
    if int(field(source_tracks[5188], "NET") or -1) != 6:
        raise ValueError("track 5188 no longer belongs to CAN_TX")

    def make_segment(
        prototype: str,
        start: tuple[float, float],
        end: tuple[float, float],
        index: int,
        layer: str,
    ) -> str:
        segment = prototype
        for name, value in (("X1", start[0]), ("Y1", start[1]), ("X2", end[0]), ("Y2", end[1])):
            segment = replace_mil_field(segment, name, value)
        segment = re.sub(r"\|LAYER=[^|]+", f"|LAYER={layer}", segment, count=1)
        return re.sub(r"\|INDEXFORSAVE=\d+", f"|INDEXFORSAVE={index}", segment, count=1)

    def make_escape_via(prototype: str, x: float, y: float, index: int) -> str:
        via = replace_mil_field(replace_mil_field(prototype, "X", x), "Y", y)
        via = re.sub(r"\|STARTLAYER=[^|]+", "|STARTLAYER=TOP", via, count=1)
        via = re.sub(r"\|ENDLAYER=[^|]+", "|ENDLAYER=MID6", via, count=1)
        return re.sub(r"\|INDEXFORSAVE=\d+", f"|INDEXFORSAVE={index}", via, count=1)

    r59_start = (numeric_mil(source_tracks[5183], "X1"), numeric_mil(source_tracks[5183], "Y1"))
    r59_escape = (mm_to_mil(34.0), mm_to_mil(48.20))
    r59_corner = (r59_escape[0], numeric_mil(source_tracks[5185], "Y2"))
    r59_end = (numeric_mil(source_tracks[5185], "X2"), numeric_mil(source_tracks[5185], "Y2"))
    can_start = (numeric_mil(source_tracks[5188], "X1"), numeric_mil(source_tracks[5188], "Y1"))
    can_outer_top = (mm_to_mil(71.50), can_start[1])
    can_outer_low = (mm_to_mil(71.50), mm_to_mil(55.30))
    can_inner_low = (mm_to_mil(70.50), mm_to_mil(55.30))
    can_escape_via = (mm_to_mil(70.50), numeric_mil(source_tracks[5190], "Y2"))
    can_end = (numeric_mil(source_tracks[5190], "X2"), numeric_mil(source_tracks[5190], "Y2"))
    replacement: list[str] = [
        make_segment(source_tracks[5183], r59_start, r59_escape, 5183, "TOP"),
        make_segment(source_tracks[5184], r59_escape, r59_corner, 5184, "MID6"),
        make_segment(source_tracks[5185], r59_corner, r59_end, 5185, "MID6"),
        make_segment(source_tracks[5188], can_start, can_outer_top, 5188, "TOP"),
        make_segment(source_tracks[5189], can_outer_top, can_outer_low, 5189, "TOP"),
        make_segment(source_tracks[5189], can_outer_low, can_inner_low, RF_CONNECTOR_TRACK_INDEX_START, "TOP"),
        make_segment(source_tracks[5189], can_inner_low, can_escape_via, RF_CONNECTOR_TRACK_INDEX_START + 1, "TOP"),
        make_segment(source_tracks[5190], can_escape_via, can_end, 5190, "MID6"),
    ]
    replacement.extend(
        [
            make_escape_via(source_vias[1041], r59_escape[0], r59_escape[1], RF_ESCAPE_VIA_INDEX_START),
            make_escape_via(source_vias[1042], can_escape_via[0], can_escape_via[1], RF_ESCAPE_VIA_INDEX_START + 1),
        ]
    )

    output: list[str] = []
    inserted = False
    for line_number, line in enumerate(lines):
        if line_number == insertion_line:
            output.extend(replacement)
            inserted = True
        record = field(line, "RECORD")
        index = int(field(line, "INDEXFORSAVE") or -1)
        if record == "Track" and index in route_indices:
            continue
        if record == "Via" and index in RF_REDUNDANT_VIA_INDICES:
            continue
        output.append(line)
    if not inserted:
        raise ValueError("RF-zone route replacement was not inserted")
    return output


def replace_mil_field(line: str, name: str, value_mil: float) -> str:
    return re.sub(rf"\|{re.escape(name)}=[^|]+", f"|{name}={value_mil:.4f}mil", line, count=1)


def relocate_rf_conflicting_vias(lines: list[str]) -> list[str]:
    output = list(lines)
    transformed: set[int] = set()
    for line_number, line in enumerate(output):
        if field(line, "RECORD") != "Via":
            continue
        index = int(field(line, "INDEXFORSAVE") or -1)
        if index not in RF_NON_TOP_VIA_SPANS:
            continue
        start_layer, end_layer = RF_NON_TOP_VIA_SPANS[index]
        changed = re.sub(r"\|STARTLAYER=[^|]+", f"|STARTLAYER={start_layer}", line, count=1)
        changed = re.sub(r"\|ENDLAYER=[^|]+", f"|ENDLAYER={end_layer}", changed, count=1)
        output[line_number] = changed
        transformed.add(index)

    if transformed != set(RF_NON_TOP_VIA_SPANS):
        missing = sorted(set(RF_NON_TOP_VIA_SPANS) - transformed)
        raise ValueError(f"RF-conflicting via records not found: {missing}")
    return output


def close_preexisting_open_stubs(lines: list[str]) -> list[str]:
    output = list(lines)
    via_positions: dict[int, tuple[float, float]] = {}
    prototype_216 = None
    for line in output:
        record = field(line, "RECORD")
        index = int(field(line, "INDEXFORSAVE") or -1)
        if record == "Via" and index in {1324, 1364, 1365}:
            via_positions[index] = (numeric_mil(line, "X"), numeric_mil(line, "Y"))
        elif record == "Track" and index == 7734:
            prototype_216 = line

    if set(via_positions) != {1324, 1364, 1365} or prototype_216 is None:
        raise ValueError("service-stub repair primitives were not found")

    repaired_185 = False
    cleaned: list[str] = []
    for line in output:
        if field(line, "RECORD") != "Track":
            cleaned.append(line)
            continue
        index = int(field(line, "INDEXFORSAVE") or -1)
        if index == 5859:
            continue
        if index == 7493:
            x, y = via_positions[1324]
            line = replace_mil_field(replace_mil_field(line, "X1", x), "Y1", y)
            repaired_185 = True
        cleaned.append(line)
    if not repaired_185:
        raise ValueError("TI_PMIC_EN repair track 7493 was not found")

    start = via_positions[1365]
    end = via_positions[1364]
    connector = prototype_216
    for name, value in (("X1", start[0]), ("Y1", start[1]), ("X2", end[0]), ("Y2", end[1])):
        connector = replace_mil_field(connector, name, value)
    connector = re.sub(r"\|INDEXFORSAVE=\d+", "|INDEXFORSAVE=9012", connector, count=1)
    cleaned.append(connector)
    return cleaned


def add_rf_specific_rules(lines: list[str]) -> list[str]:
    rf_nets = " OR ".join(f"InNet('{name}')" for name in TARGET_NETS.values())
    rf_scope = f"OnLayer('Top Layer') AND (IsTrack OR IsArc) AND ({rf_nets})"
    output = list(lines)
    width_rule_line = None
    for line_number, line in enumerate(output):
        if (
            field(line, "RECORD") == "DXPRule"
            and field(line, "RULEKIND") == "Width"
            and field(line, "NAME") == "Width"
        ):
            output[line_number] = line.replace("|PRIORITY=1|", "|PRIORITY=2|", 1)
            width_rule_line = line_number
            break
    if width_rule_line is None:
        raise ValueError("default width rule not found")

    rf_width_rule = (
        "|RECORD=DXPRule|INDEXFORSAVE=40|SELECTION=FALSE|LAYER=TOP|LOCKED=FALSE"
        "|POLYGONOUTLINE=FALSE|USERROUTED=TRUE|UNIONINDEX=0|RULEKIND=Width"
        f"|NETSCOPE=AnyNet|LAYERKIND=SameLayer|SCOPE1EXPRESSION={rf_scope}"
        "|SCOPE2EXPRESSION=All|NAME=PROC194A_RF_WIDTH|ENABLED=TRUE|PRIORITY=1"
        "|COMMENT=Calculated 78.5 GHz antenna microstrip widths on RO3003"
        "|UNIQUEID=RFWIDTH8|DEFINEDBYLOGICALDOCUMENT=FALSE"
        f"|MAXLIMIT={FEED_WIDTH_MIL:.4f}mil|MINLIMIT={SERIES_WIDTH_MIL:.4f}mil"
        f"|PREFEREDWIDTH={SERIES_WIDTH_MIL:.4f}mil"
    )
    rf_clearance_rule = (
        "|RECORD=DXPRule|INDEXFORSAVE=41|SELECTION=FALSE|LAYER=TOP|LOCKED=FALSE"
        "|POLYGONOUTLINE=FALSE|USERROUTED=TRUE|UNIONINDEX=0|RULEKIND=Clearance"
        f"|NETSCOPE=DifferentNets|LAYERKIND=SameLayer|SCOPE1EXPRESSION={rf_scope}"
        f"|SCOPE2EXPRESSION={rf_scope}|NAME=PROC194A_RF_TO_RF_CLEARANCE"
        "|ENABLED=TRUE|PRIORITY=3|COMMENT=Controlled antenna-array inter-channel spacing"
        "|UNIQUEID=RFCLR045|DEFINEDBYLOGICALDOCUMENT=FALSE"
        "|GAP=4.5mil|GENERICCLEARANCE=4.5mil"
        "|IGNOREPADTOPADCLEARANCEINFOOTPRINT=FALSE|OBJECTCLEARANCES="
    )
    output[width_rule_line + 1:width_rule_line + 1] = [rf_width_rule, rf_clearance_rule]
    return output


def pattern_rows() -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    pitch_m = PITCH_LAMBDA_0 * C_M_S / TARGET_FREQUENCY_HZ
    positions_m = tuple((index - 3.5) * pitch_m for index in range(8))
    target_phase_deg = (
        PHASE_TARGET_INNER_TO_OUTER_DEG[3],
        PHASE_TARGET_INNER_TO_OUTER_DEG[2],
        PHASE_TARGET_INNER_TO_OUTER_DEG[1],
        PHASE_TARGET_INNER_TO_OUTER_DEG[0],
        PHASE_TARGET_INNER_TO_OUTER_DEG[0],
        PHASE_TARGET_INNER_TO_OUTER_DEG[1],
        PHASE_TARGET_INNER_TO_OUTER_DEG[2],
        PHASE_TARGET_INNER_TO_OUTER_DEG[3],
    )
    rows: list[dict[str, float]] = []
    summary: list[dict[str, float]] = []
    for frequency_hz in CHECK_FREQUENCIES_HZ:
        k = 2.0 * math.pi * frequency_hz / C_M_S
        phase_scale = frequency_hz / TARGET_FREQUENCY_HZ
        phases_rad = tuple(math.radians(value) * phase_scale for value in target_phase_deg)
        boresight_real = sum(math.cos(phase) for phase in phases_rad)
        boresight_imag = sum(math.sin(phase) for phase in phases_rad)
        boresight_power = boresight_real * boresight_real + boresight_imag * boresight_imag
        samples: list[tuple[float, float]] = []
        for step in range(-900, 901):
            angle_deg = step / 10.0
            angle_rad = math.radians(angle_deg)
            terms = tuple(
                phase + k * position * math.sin(angle_rad)
                for phase, position in zip(phases_rad, positions_m)
            )
            real = sum(math.cos(value) for value in terms)
            imag = sum(math.sin(value) for value in terms)
            array_power = (real * real + imag * imag) / boresight_power
            element_power = math.cos(angle_rad) ** 2
            power = max(array_power * element_power, 1e-15)
            db = 10.0 * math.log10(power)
            samples.append((angle_deg, db))
            rows.append(
                {
                    "frequency_ghz": frequency_hz / 1e9,
                    "elevation_deg": angle_deg,
                    "normalized_power_db": db,
                }
            )
        positive = [(angle, value) for angle, value in samples if angle >= 0.0]
        half_power_angle = next(angle for angle, value in positive if value <= -3.0)
        edge_db = next(value for angle, value in positive if abs(angle - 20.0) < 1e-9)
        summary.append(
            {
                "frequency_ghz": frequency_hz / 1e9,
                "half_power_angle_deg": half_power_angle,
                "full_3db_beamwidth_deg": 2.0 * half_power_angle,
                "power_at_plus_minus_20_deg_db": edge_db,
            }
        )
    return rows, summary


def array_factor_directivity_db(excitations: tuple[complex, ...]) -> float:
    coherent_sum = sum(excitations)
    input_power = sum(abs(value) ** 2 for value in excitations)
    return 10.0 * math.log10(abs(coherent_sum) ** 2 / input_power)


def validate_geometry(sections: list[dict[str, object]], pattern_summary: list[dict[str, float]]) -> dict[str, object]:
    errors: list[str] = []
    radius_limit = BOARD_RADIUS_MM - BOARD_EDGE_MARGIN_MM
    for section in sections:
        x_center = float(section["x_center_mm"])
        y_centers = [float(value) for value in section["patch_centers_y_mm"]]
        for y_center, width_mm in zip(y_centers, PATCH_WIDTHS_MM):
            for x in (x_center - width_mm / 2.0, x_center + width_mm / 2.0):
                for y in (y_center - PATCH_LENGTH_MM / 2.0, y_center + PATCH_LENGTH_MM / 2.0):
                    radius = math.hypot(x - BOARD_CENTER_MM[0], y - BOARD_CENTER_MM[1])
                    if radius > radius_limit:
                        errors.append(f"{section['net_name']} patch corner exceeds the board edge margin")
    for item in pattern_summary:
        if item["power_at_plus_minus_20_deg_db"] < -3.0:
            errors.append(f"{item['frequency_ghz']} GHz edge response is below -3 dB")

    old_factor_db = array_factor_directivity_db((0.90 + 0j, 1.35 + 0j))
    target_phases_rad = (
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[3]),
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[2]),
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[1]),
        0.0,
        0.0,
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[1]),
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[2]),
        math.radians(PHASE_TARGET_INNER_TO_OUTER_DEG[3]),
    )
    new_factor_db = array_factor_directivity_db(tuple(complex(math.cos(value), math.sin(value)) for value in target_phases_rad))
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "board_diameter_mm": BOARD_RADIUS_MM * 2.0,
        "minimum_board_edge_margin_mm": BOARD_EDGE_MARGIN_MM,
        "calculated_old_array_factor_directivity_db": old_factor_db,
        "calculated_new_array_factor_directivity_db": new_factor_db,
        "calculated_relative_gain_change_db": new_factor_db - old_factor_db,
        "calculation_limit": (
            "The result is an eight-element array-factor and first-order microstrip phase-length calculation. "
            "Patch coupling tapers and meander sections require full-wave tuning with the actual stackup. "
            "The calculation does not replace a full-wave model of feeds, mutual coupling, radome or losses."
        ),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("frequency_ghz", "elevation_deg", "normalized_power_db"))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the calculated wide-elevation antenna candidate for the D79 radar board")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pattern-csv", required=True, type=Path)
    parser.add_argument("--array-shift-y-mm", type=float, default=0.0)
    parser.add_argument("--preserve-rf-conflicting-vias", action="store_true")
    args = parser.parse_args()

    lines, newline = load_ascii(args.source)
    old_fills, handoffs, removal_lines = collect_old_geometry(lines)
    new_records, sections = build_new_geometry(old_fills, handoffs, args.array_shift_y_mm)
    output_lines = insert_geometry(lines, removal_lines, new_records)
    output_lines = relocate_rf_zone_crossing_routes(output_lines)
    if not args.preserve_rf_conflicting_vias:
        output_lines = relocate_rf_conflicting_vias(output_lines)
    output_lines = close_preexisting_open_stubs(output_lines)
    output_lines = add_rf_specific_rules(output_lines)
    output_lines[0] = re.sub(
        r"\|FILENAME=[^|]+",
        f"|FILENAME={args.output.name}",
        output_lines[0],
        count=1,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((newline.join(output_lines) + newline).encode("cp1252"))

    pattern, pattern_summary = pattern_rows()
    write_csv(args.pattern_csv, pattern)
    validation = validate_geometry(sections, pattern_summary)
    pitch_mm = PITCH_LAMBDA_0 * C_M_S / TARGET_FREQUENCY_HZ * 1000.0
    manifest = {
        "schema": "radar_wide_elevation_antenna_candidate_v1",
        "revision": "0.8.0",
        "purpose": "civilian airborne-drone observation and tracking",
        "source_ascii_pcbdoc": str(args.source.resolve()),
        "output_ascii_pcbdoc": str(args.output.resolve()),
        "source_sha256": sha256(args.source),
        "output_sha256": sha256(args.output),
        "target_frequency_ghz": TARGET_FREQUENCY_HZ / 1e9,
        "checked_frequencies_ghz": [value / 1e9 for value in CHECK_FREQUENCIES_HZ],
        "element_count_per_channel": 8,
        "channel_count": 8,
        "patch_pitch_mm": pitch_mm,
        "patch_pitch_lambda_0_at_target": PITCH_LAMBDA_0,
        "patch_length_mm": PATCH_LENGTH_MM,
        "patch_widths_mm": list(PATCH_WIDTHS_MM),
        "target_phase_inner_to_outer_deg": list(PHASE_TARGET_INNER_TO_OUTER_DEG),
        "phase_increment_deg": list(PHASE_INCREMENT_DEG),
        "phase_section_lengths_mm": list(phase_section_lengths_mm()),
        "array_shift_y_mm": args.array_shift_y_mm,
        "phase_center_contract": (
            "Preserve all RX/TX x coordinates and every relative RX/TX vertical offset. "
            "Move all eight-element apertures upward by the recorded common offset to establish the RF keepout."
        ),
        "sections": sections,
        "rf_zone_route_relocations": {
            "TI_NetR59_1": "The RF-zone section is transferred from Top to Mid6 through a Top-to-Mid6 escape via outside the aperture.",
            "CAN_TX": "The Top route detours around the right edge of the aperture and transfers to Mid6 outside the RF zone.",
        },
        "rf_non_top_via_spans": {
            str(index): {"start_layer": span[0], "end_layer": span[1]}
            for index, span in RF_NON_TOP_VIA_SPANS.items()
        },
        "array_factor_summary": pattern_summary,
        "geometry_validation": validation,
        "altium_native_import_status": "PENDING",
        "altium_drc_status": "PENDING",
        "full_wave_em_status": "REQUIRED_NOT_PERFORMED",
        "physical_measurement_status": "REQUIRED_NOT_PERFORMED",
        "production_authority": "NOT_AUTHORIZED",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": validation["status"], "manifest": str(args.manifest), "output": str(args.output)}))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
