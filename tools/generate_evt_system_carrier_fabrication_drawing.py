from __future__ import annotations

import hashlib
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "hardware/system_carrier/altium/release/pilot_r1/fab"
    / "Fabrication_Drawing_PILOT_R1.pdf"
)
PCB = ROOT / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc"

NAVY = colors.HexColor("#17365d")
BLUE = colors.HexColor("#1f4e78")
LIGHT_BLUE = colors.HexColor("#eaf2f8")
LIGHT_GRAY = colors.HexColor("#f3f4f6")
MID_GRAY = colors.HexColor("#64748b")
RED = colors.HexColor("#b91c1c")
GREEN = colors.HexColor("#166534")
AMBER = colors.HexColor("#92400e")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_fonts() -> None:
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
    ]
    if all(path.exists() for path in candidates):
        pdfmetrics.registerFont(TTFont("DrawingSans", str(candidates[0])))
        pdfmetrics.registerFont(TTFont("DrawingSans-Bold", str(candidates[1])))


def font(bold: bool = False) -> str:
    preferred = "DrawingSans-Bold" if bold else "DrawingSans"
    return preferred if preferred in pdfmetrics.getRegisteredFontNames() else (
        "Helvetica-Bold" if bold else "Helvetica"
    )


def title_block(c: canvas.Canvas, width: float, sheet: int) -> None:
    x = width - 111 * mm
    y = 10 * mm
    w = 99 * mm
    h = 31 * mm
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.35 * mm)
    c.rect(x, y, w, h)
    c.line(x, y + 13 * mm, x + w, y + 13 * mm)
    c.line(x + 69 * mm, y, x + 69 * mm, y + 13 * mm)
    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(x + 3 * mm, y + 23 * mm, "EVT_SYS_CARRIER REV.A")
    c.setFont(font(), 7.5)
    c.drawString(x + 3 * mm, y + 18 * mm, "PILOT R1 FABRICATION DRAWING")
    c.drawString(x + 3 * mm, y + 14.5 * mm, "FABRICATOR REVIEW / CAM PREFLIGHT")
    c.setFillColor(colors.black)
    c.drawString(x + 3 * mm, y + 8 * mm, "Scale: 1:1")
    c.drawString(x + 72 * mm, y + 8 * mm, f"Sheet {sheet}/2")
    c.setFillColor(RED)
    c.setFont(font(True), 7)
    c.drawString(x + 3 * mm, y + 3 * mm, "PRODUCTION AUTHORITY: NOT_AUTHORIZED")
    c.setFillColor(colors.black)


def arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    c.line(x1, y1, x2, y2)
    if abs(x2 - x1) >= abs(y2 - y1):
        c.line(x1, y1, x1 + 2.5 * mm, y1 + 1.2 * mm)
        c.line(x1, y1, x1 + 2.5 * mm, y1 - 1.2 * mm)
        c.line(x2, y2, x2 - 2.5 * mm, y2 + 1.2 * mm)
        c.line(x2, y2, x2 - 2.5 * mm, y2 - 1.2 * mm)
    else:
        c.line(x1, y1, x1 + 1.2 * mm, y1 + 2.5 * mm)
        c.line(x1, y1, x1 - 1.2 * mm, y1 + 2.5 * mm)
        c.line(x2, y2, x2 + 1.2 * mm, y2 - 2.5 * mm)
        c.line(x2, y2, x2 - 1.2 * mm, y2 - 2.5 * mm)


def draw_header(c: canvas.Canvas, title: str, subtitle: str) -> None:
    width, height = landscape(A3)
    c.setFillColor(NAVY)
    c.setFont(font(True), 15)
    c.drawString(18 * mm, height - 18 * mm, title)
    c.setFillColor(colors.black)
    c.setFont(font(), 8)
    c.drawString(18 * mm, height - 24 * mm, subtitle)
    c.setStrokeColor(BLUE)
    c.setLineWidth(0.4 * mm)
    c.line(18 * mm, height - 28 * mm, width - 18 * mm, height - 28 * mm)


def draw_table(
    c: canvas.Canvas,
    data: list[list[str]],
    x: float,
    y_top: float,
    widths: list[float],
    font_size: float = 7,
    row_heights: list[float] | float | None = None,
) -> float:
    table = Table(
        data,
        colWidths=widths,
        rowHeights=row_heights,
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), font(True)),
                ("FONTNAME", (0, 1), (-1, -1), font()),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("GRID", (0, 0), (-1, -1), 0.35, MID_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ]
        )
    )
    table_width, table_height = table.wrapOn(c, 0, 0)
    table.drawOn(c, x, y_top - table_height)
    return table_height


def draw_paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    size: float = 8,
    leading: float = 11,
    color: colors.Color = colors.black,
) -> float:
    style = ParagraphStyle(
        "drawing",
        fontName=font(),
        fontSize=size,
        leading=leading,
        textColor=color,
        spaceAfter=0,
    )
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, 200 * mm)
    paragraph.drawOn(c, x, y_top - height)
    return height


def page_one(c: canvas.Canvas) -> None:
    width, height = landscape(A3)
    draw_header(
        c,
        "EVT_SYS_CARRIER REV.A  |  BOARD OUTLINE AND PILOT FABRICATION BASIS",
        "Dimensions in millimetres. Mechanical datum and output status are bound to the final native Altium PcbDoc.",
    )

    ox = 83 * mm
    oy = 71 * mm
    board_w = 90 * mm
    board_h = 70 * mm
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.55 * mm)
    c.roundRect(ox, oy, board_w, board_h, 3 * mm)

    for hx, hy, name in [(5, 5, "H1"), (85, 5, "H2"), (5, 65, "H3"), (85, 65, "H4")]:
        x = ox + hx * mm
        y = oy + hy * mm
        c.setLineWidth(0.22 * mm)
        c.circle(x, y, 1.6 * mm)
        c.line(x - 3 * mm, y, x + 3 * mm, y)
        c.line(x, y - 3 * mm, x, y + 3 * mm)
        c.setFont(font(), 7)
        c.drawString(x + 3 * mm, y + 2 * mm, f"{name}  NPTH 3.20")

    dim_y = oy - 16 * mm
    dim_x = ox - 18 * mm
    c.setLineWidth(0.2 * mm)
    c.line(ox, oy, ox, dim_y - 2 * mm)
    c.line(ox + board_w, oy, ox + board_w, dim_y - 2 * mm)
    arrow(c, ox, dim_y, ox + board_w, dim_y)
    c.setFont(font(True), 9)
    c.drawCentredString(ox + board_w / 2, dim_y + 2.5 * mm, "90.00")
    c.line(ox, oy, dim_x - 2 * mm, oy)
    c.line(ox, oy + board_h, dim_x - 2 * mm, oy + board_h)
    arrow(c, dim_x, oy, dim_x, oy + board_h)
    c.saveState()
    c.translate(dim_x - 3 * mm, oy + board_h / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, "70.00")
    c.restoreState()

    c.setFont(font(), 7)
    c.drawString(ox, oy + board_h + 7 * mm, "OUTLINE: R3.00 CORNERS, ROUTED PROFILE")
    c.drawString(
        ox,
        oy - 27 * mm,
        "MOUNTING DATUM: H1 CENTRE AT X=5.00, Y=5.00 FROM LOWER-LEFT BOARD EXTENTS",
    )

    x = 224 * mm
    y = height - 40 * mm
    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(x, y, "PILOT FABRICATION NOTES")
    c.setFillColor(colors.black)
    notes = [
        "1. Finished board outline: 90.00 x 70.00 mm with R3.00 corners.",
        "2. Project mechanical target: 1.60 mm. Working Rezonit baseline: published 1.50 mm TG150 four-layer construction; order data prevails.",
        "3. Four copper layers, 35 um base copper on every layer, FR-4 TG150 IPC-4101/99 working material.",
        "4. L1 components/signals; L2 solid GND; L3 power and slow signals; L4 secondary signals.",
        "5. Pilot finish request: ENIG, 0.075-0.125 um Au over 3-6 um Ni; green solder mask; white legend.",
        "6. External interfaces are two 3.3 V UART channels and a connectorized external GNSS module. Ethernet is not fitted on this revision.",
        "7. No controlled-impedance route class is released for this carrier revision. Any order-specific impedance request requires CAM solver review and a controlled PCB ECO.",
        "8. Gerber X2 includes the routed board profile. Legacy RS-274X GKO is retained as a CAM fallback; NC drill files remain the drill authority.",
        "9. Use the NC drill reports for plated, non-plated and Top-to-L2 tool definitions. Finished hole sizes are specified on sheet 2.",
        "10. Electrical test is required. Submit single-board data; fabricator panelisation is permitted after CAM review.",
        "11. IPC-2581 Revision B and Gerber X2 are both supplied. Resolve any CAM disagreement against the native PcbDoc and this drawing.",
        "12. This pilot drawing supports quotation and CAM preflight. It does not grant production authority.",
    ]
    for note in notes:
        used = draw_paragraph(c, note, x, y - 6 * mm, 176 * mm, 7.4, 10)
        y -= used + 2.1 * mm

    summary = [
        ["Item", "Current evidence", "Pilot R1 state"],
        ["Gerber X2", "4 copper, mask, paste, legend and profile", "PASS"],
        ["IPC-2581", "Revision B; 83 components; current native export", "PASS"],
        ["Native DRC", "0 warnings, 0 violations, 0 unrouted", "PASS"],
        ["Connections", "483 pads, 1776 tracks, 241 vias, 60 fills", "PASS"],
        ["STEP", "Board solid and hole geometry; component 3D out of scope", "PASS SCOPE"],
    ]
    draw_table(
        c,
        summary,
        224 * mm,
        94 * mm,
        [39 * mm, 111 * mm, 26 * mm],
        font_size=6.7,
        row_heights=7.5 * mm,
    )
    title_block(c, width, 1)
    c.showPage()


def page_two(c: canvas.Canvas, pcb_hash: str) -> None:
    width, height = landscape(A3)
    draw_header(
        c,
        "EVT_SYS_CARRIER REV.A  |  STACKUP, SIGNAL-INTEGRITY, DFM AND DRILL SUMMARY",
        "Pilot R1 uses the published Rezonit 4-layer, 35 um TG150 construction as a working baseline; order-specific values remain deferred.",
    )

    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(18 * mm, height - 37 * mm, "PUBLISHED REZONIT WORKING STACK")
    c.setFillColor(colors.black)
    stack = [
        ["Seq", "Item", "Layer / material", "Thickness", "Copper", "Dk at 1 MHz", "Status"],
        ["1", "Copper", "L1 Top", "0.035 mm", "35 um", "", "WORKING"],
        ["2", "Prepreg", "FR-4 TG150 2116", "0.115 mm", "", "4.2", "WORKING"],
        ["3", "Copper", "L2 solid GND", "0.035 mm", "35 um", "", "WORKING"],
        ["4", "Core", "FR-4 TG150 IPC-4101/99", "1.130 mm", "", "4.6", "WORKING"],
        ["5", "Copper", "L3 power / slow signal", "0.035 mm", "35 um", "", "WORKING"],
        ["6", "Prepreg", "FR-4 TG150 2116", "0.115 mm", "", "4.2", "WORKING"],
        ["7", "Copper", "L4 Bottom", "0.035 mm", "35 um", "", "WORKING"],
    ]
    draw_table(
        c,
        stack,
        18 * mm,
        height - 41 * mm,
        [11 * mm, 23 * mm, 56 * mm, 24 * mm, 21 * mm, 24 * mm, 27 * mm],
        row_heights=7 * mm,
    )
    c.setFont(font(), 6.5)
    c.drawString(
        18 * mm,
        height - 100 * mm,
        "Published actual board thickness: 1.50 mm, excluding plating, finish and solder mask. Project mechanical target remains 1.60 mm.",
    )

    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(18 * mm, height - 110 * mm, "SIGNAL-INTEGRITY DISPOSITION")
    c.setFillColor(colors.black)
    impedance = [
        ["Interface", "Physical layer", "Current revision", "Fabricator action", "Disposition"],
        ["HOST_UART_A/B", "3.3 V single-ended", "Two connectorized UART channels", "Check ordinary clearance and return path", "NO Z0 CONTROL"],
        ["GNSS", "UART/PPS to external module", "No onboard GNSS RF route", "Check connector pinout and ESD placement", "NO RF Z0 CLASS"],
        ["Ethernet", "Not fitted", "Removed from canonical requirement", "Do not add MDI artwork or impedance notes", "NOT APPLICABLE"],
    ]
    draw_table(
        c,
        impedance,
        18 * mm,
        height - 114 * mm,
        [34 * mm, 48 * mm, 58 * mm, 67 * mm, 34 * mm],
        font_size=6.6,
        row_heights=8 * mm,
    )
    draw_paragraph(
        c,
        "The published Rezonit construction is a working material baseline, not an order-bound impedance solution. The supplied artwork remains the validated EVT baseline. Any stack or routing change requires a controlled PCB ECO and repeated DRC and connection audit.",
        18 * mm,
        height - 149 * mm,
        241 * mm,
        6.7,
        9,
        AMBER,
    )

    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(18 * mm, height - 158 * mm, "NC DRILL TOOL SUMMARY")
    c.setFillColor(colors.black)
    drills = [
        ["Tool", "Finished hole", "Type", "Count"],
        ["T1", "0.18 mm", "PTH Top-L2", "1"],
        ["T2", "0.20 mm", "PTH through", "133"],
        ["T2", "0.20 mm", "PTH Top-L2", "2"],
        ["T3", "0.25 mm", "PTH", "4"],
        ["T4", "0.30 mm", "PTH", "103"],
        ["T5", "0.40 mm", "PTH", "2"],
        ["T6", "0.991 mm", "PTH", "3"],
        ["T7", "1.02 mm", "PTH", "16"],
        ["T8", "3.00 mm", "PTH", "3"],
        ["T9", "3.00 mm", "NPTH", "1"],
        ["T10", "3.20 mm", "NPTH", "4"],
        ["", "TOTAL", "", "272"],
    ]
    draw_table(
        c,
        drills,
        18 * mm,
        height - 162 * mm,
        [18 * mm, 30 * mm, 24 * mm, 20 * mm],
        font_size=6.5,
        row_heights=5.5 * mm,
    )

    c.setFillColor(NAVY)
    c.setFont(font(True), 10)
    c.drawString(122 * mm, height - 158 * mm, "PUBLISHED DFM BASELINE VS CURRENT DESIGN")
    c.setFillColor(colors.black)
    dfm = [
        ["Parameter", "Current design / output", "Rezonit published", "Pilot disposition"],
        ["Trace width", "0.15 mm minimum rule", "0.20 basic; 0.15 advanced", "ADVANCED"],
        ["Copper spacing", "0.20 mm minimum rule", "0.20 basic; 0.15 advanced", "PASS BASIC"],
        ["Drill", "0.18 mm Top-L2; 0.20 mm through minimum", "Order capability to be confirmed", "CAM REVIEW"],
        ["Via annular ring", "Validate against current drill and pad tables", "0.15 basic; 0.10 advanced", "CAM REVIEW"],
        ["NPTH", "3.20 mm mounting holes", "0.50 mm published minimum", "PASS"],
        ["Solder mask", "Green; 0.025 mm expansion request", "0.10 mm bridge; 0.025 expansion", "CAM CHECK"],
    ]
    draw_table(
        c,
        dfm,
        122 * mm,
        height - 162 * mm,
        [37 * mm, 67 * mm, 64 * mm, 34 * mm],
        font_size=6.25,
        row_heights=8 * mm,
    )

    c.setFillColor(NAVY)
    c.setFont(font(True), 9)
    c.drawString(122 * mm, 72 * mm, "SOURCE BINDING")
    c.setFillColor(colors.black)
    sources = [
        f"Native PcbDoc SHA-256: {pcb_hash}",
        "Native DRC: PASS, 0 warnings, 0 violations, 0 unrouted nets.",
        "Connection integrity: PASS; all pads and routed copper remain inside the 90 x 70 mm outline.",
        "Rezonit stack source: rezonit.ru/.../tipovye-sborki-i-konstruktsii-pechatnykh-plat/",
        "Rezonit finish/mask source: rezonit.ru published production capabilities table.",
        "Order-specific stack, finished copper and field-solver geometry take precedence when available.",
    ]
    y = 66 * mm
    for item in sources:
        used = draw_paragraph(c, item, 122 * mm, y, 202 * mm, 6.4, 8)
        y -= used + 1.3 * mm

    c.setFillColor(RED)
    c.setFont(font(True), 7.2)
    c.drawString(122 * mm, 18 * mm, "PRODUCTION AUTHORITY REMAINS NOT_AUTHORIZED")
    c.setFillColor(colors.black)
    title_block(c, width, 2)
    c.showPage()


def main() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pcb_hash = sha256(PCB)
    drawing = canvas.Canvas(
        str(OUTPUT),
        pagesize=landscape(A3),
        pageCompression=1,
        invariant=1,
    )
    drawing.setTitle("EVT_SYS_CARRIER Pilot R1 Fabrication Drawing")
    drawing.setAuthor("skif-ops/RLS_Head")
    drawing.setSubject("Pilot fabrication basis for fabricator review and CAM preflight")
    page_one(drawing)
    page_two(drawing, pcb_hash)
    drawing.save()


if __name__ == "__main__":
    main()
