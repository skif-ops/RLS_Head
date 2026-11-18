from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PAGE_WIDTH = 6740.0
PAGE_HEIGHT = 3800.0
TITLE_HEIGHT = 190.0
GRID_BOTTOM = 1270.0
CELL_WIDTH = 840.0
CELL_HEIGHT = 590.0
MATRIX_BOTTOM = 30.0
MATRIX_TOP = 1220.0


def encoded_net_name(net: str) -> str:
    return "NL" + "".join(character if character.isalnum() else "0" for character in net)


def load_binding(binding_csv: Path) -> tuple[dict[str, set[str]], dict[str, int]]:
    token_to_nets: dict[str, set[str]] = defaultdict(set)
    net_pad_count: dict[str, int] = defaultdict(int)
    with binding_csv.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            net = (row.get("Net") or "").strip()
            if not net:
                continue
            token_to_nets[encoded_net_name(net)].add(net)
            net_pad_count[net] += 1
    return token_to_nets, dict(net_pad_count)


def extract_cross_sheet_nets(
    source_pdf: Path,
    binding_csv: Path,
) -> tuple[dict[str, list[int]], dict[str, int], list[str]]:
    reader = PdfReader(str(source_pdf))
    if len(reader.pages) < 32:
        raise ValueError(f"Expected at least 32 schematic pages, found {len(reader.pages)}")
    token_to_nets, net_pad_count = load_binding(binding_csv)
    net_to_sheets: dict[str, set[int]] = defaultdict(set)
    unresolved: set[str] = set()
    for sheet_number, page in enumerate(reader.pages[1:32], start=1):
        text = page.extract_text() or ""
        for token in set(re.findall(r"NL[A-Za-z0-9_]+", text)):
            candidates = token_to_nets.get(token, set())
            if len(candidates) == 1:
                net_to_sheets[next(iter(candidates))].add(sheet_number)
            else:
                unresolved.add(token)
    cross_sheet = {
        net: sorted(sheets)
        for net, sheets in net_to_sheets.items()
        if len(sheets) >= 2
    }
    return cross_sheet, net_pad_count, sorted(unresolved)


def write_connectivity_csv(path: Path, net_to_sheets: dict[str, list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["Net", "Sheets"])
        for net in sorted(net_to_sheets, key=net_sort_key):
            writer.writerow([net, ";".join(f"{sheet:02d}" for sheet in net_to_sheets[net])])


def net_sort_key(net: str) -> tuple[int, str]:
    upper = net.upper()
    if upper == "GND":
        group = 0
    elif any(token in upper for token in ("24V", "12V", "5V", "3V3", "1V")):
        group = 1
    elif any(token in upper for token in ("UART", "CAN", "USB", "GNSS", "IMU", "SWD")):
        group = 2
    elif upper.startswith("TI_"):
        group = 3
    else:
        group = 4
    return group, upper


def net_color(net: str) -> tuple[float, float, float]:
    group = net_sort_key(net)[0]
    return {
        0: (0.18, 0.18, 0.18),
        1: (0.76, 0.05, 0.05),
        2: (0.04, 0.24, 0.76),
        3: (0.48, 0.05, 0.55),
        4: (0.38, 0.38, 0.38),
    }[group]


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\arial.ttf")
    bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("R9Regular", str(regular)))
        pdfmetrics.registerFont(TTFont("R9Bold", str(bold)))
        return "R9Regular", "R9Bold"
    return "Helvetica", "Helvetica-Bold"


def cell_origin(index: int) -> tuple[float, float]:
    col = index % 8
    row = index // 8
    return col * CELL_WIDTH, GRID_BOTTOM + (3 - row) * CELL_HEIGHT


def draw_patch_array(
    c: canvas.Canvas,
    x: float,
    y: float,
    channel: str,
    pin: str,
    color: tuple[float, float, float],
    regular_font: str,
    bold_font: str,
) -> None:
    c.setFillColorRGB(*color)
    c.setStrokeColorRGB(*color)
    c.setFont(bold_font, 13)
    c.drawString(x, y + 5, channel)
    c.setFont(regular_font, 9)
    c.drawString(x + 34, y + 6, pin)
    c.setLineWidth(2)
    c.line(x + 118, y + 9, x + 155, y + 9)
    for i in range(8):
        px = x + 158 + i * 24
        c.rect(px, y - 3, 17, 25, stroke=1, fill=1)


def draw_rf_tile(
    c: canvas.Canvas,
    x: float,
    y: float,
    regular_font: str,
    bold_font: str,
) -> None:
    c.setStrokeColorRGB(0.12, 0.12, 0.12)
    c.setFillColorRGB(0.12, 0.12, 0.12)
    c.setFont(bold_font, 20)
    c.drawString(x + 18, y + CELL_HEIGHT - 32, "ВЧ ТРАКТ И ПЕЧАТНЫЕ АНТЕННЫ")
    c.setFont(regular_font, 11)
    c.drawString(
        x + 18,
        y + CELL_HEIGHT - 52,
        "AWR2944P, FMCW 76...81 ГГц, 4 TX + 4 когерентных RX, по 8 элементов в каждом канале",
    )

    block_x = x + 20
    block_y = y + 115
    c.setFillColorRGB(0.94, 0.94, 0.84)
    c.setStrokeColorRGB(0.15, 0.15, 0.15)
    c.setLineWidth(2)
    c.roundRect(block_x, block_y, 180, 330, 8, stroke=1, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont(bold_font, 17)
    c.drawCentredString(block_x + 90, block_y + 277, "RAD_U29")
    c.drawCentredString(block_x + 90, block_y + 251, "AWR2944P")
    c.setFont(regular_font, 11)
    c.drawCentredString(block_x + 90, block_y + 205, "FMCW синтезатор")
    c.drawCentredString(block_x + 90, block_y + 184, "4 передающих канала")
    c.drawCentredString(block_x + 90, block_y + 163, "4 фазокогерентных RX")
    c.drawCentredString(block_x + 90, block_y + 118, "дальность: beat-частота")
    c.drawCentredString(block_x + 90, block_y + 97, "скорость: Доплер")
    c.drawCentredString(block_x + 90, block_y + 76, "углы: разность фаз RX")

    red = (0.78, 0.08, 0.08)
    blue = (0.05, 0.25, 0.78)
    rows = [
        ("TX1", "TI_TX1 / B3", red),
        ("TX2", "TI_TX2 / B5", red),
        ("TX3", "TI_TX3 / B7", red),
        ("TX4", "TI_TX4 / B9", red),
        ("RX1", "TI_RX1 / M2", blue),
        ("RX2", "TI_RX2 / K2", blue),
        ("RX3", "TI_RX3 / H2", blue),
        ("RX4", "TI_RX4 / F2", blue),
    ]
    row_x = x + 220
    for i, (channel, pin, color) in enumerate(rows):
        row_y = y + 474 - i * 50
        c.setStrokeColorRGB(*color)
        c.setLineWidth(1.4)
        c.line(block_x + 180, row_y + 9, row_x - 10, row_y + 9)
        draw_patch_array(c, row_x, row_y, channel, pin, color, regular_font, bold_font)

    c.setFillColorRGB(0.16, 0.16, 0.16)
    c.setFont(regular_font, 9)
    c.drawString(
        x + 20,
        y + 78,
        "Линии контролируемого импеданса, согласование, развязка и геометрия питания антенн заданы медью PCB.",
    )
    c.drawString(
        x + 20,
        y + 60,
        "Фазовое измерение угла использует взаимно-когерентные RX1...RX4; антенны являются частью круглой платы D79.",
    )
    c.setFont(bold_font, 10)
    c.drawString(x + 20, y + 37, "Электрические связи каналов показаны явно; каждый прямоугольник обозначает печатный элемент.")


def draw_connectivity_matrix(
    c: canvas.Canvas,
    net_to_sheets: dict[str, list[int]],
    net_pad_count: dict[str, int],
    regular_font: str,
    bold_font: str,
) -> None:
    left = 25.0
    right = PAGE_WIDTH - 25.0
    header_y = MATRIX_TOP - 32.0
    first_row_y = MATRIX_TOP - 95.0
    row_bottom = MATRIX_BOTTOM + 58.0
    sheet_start_x = 940.0
    sheet_end_x = right - 25.0
    sheet_step = (sheet_end_x - sheet_start_x) / 30.0
    ordered_nets = sorted(net_to_sheets, key=net_sort_key)
    row_height = (first_row_y - row_bottom) / max(len(ordered_nets) - 1, 1)

    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1.5)
    c.rect(left, MATRIX_BOTTOM, right - left, MATRIX_TOP - MATRIX_BOTTOM, stroke=1, fill=0)
    c.setFillColorRGB(0.08, 0.08, 0.08)
    c.setFont(bold_font, 18)
    c.drawString(left + 12, header_y, "МЕЖЛИСТОВЫЕ ЭЛЕКТРИЧЕСКИЕ СОЕДИНЕНИЯ")
    c.setFont(regular_font, 9)
    c.drawString(
        left + 12,
        header_y - 22,
        "Строка соответствует точному имени сети Altium. Метка в столбце листа означает наличие электрической точки этой сети на данном листе.",
    )
    c.drawString(
        left + 12,
        header_y - 38,
        "Все локальные проводники, номера выводов и обозначения компонентов показаны выше. Полная привязка контакт-сеть сохранена в R9_pad_binding.csv.",
    )
    c.setFont(bold_font, 7)
    c.drawString(left + 12, first_row_y + 17, "ТОЧНОЕ ИМЯ СЕТИ")
    c.drawString(535, first_row_y + 17, "КОНТАКТОВ")
    c.drawString(640, first_row_y + 17, "ЛИСТЫ")
    for sheet in range(1, 32):
        x = sheet_start_x + (sheet - 1) * sheet_step
        c.setFillColorRGB(0.12, 0.12, 0.12)
        c.setFont(bold_font, 7)
        c.drawCentredString(x, first_row_y + 17, f"{sheet:02d}")
        c.setStrokeColorRGB(0.9, 0.9, 0.9)
        c.setLineWidth(0.25)
        c.line(x, row_bottom - 4, x, first_row_y + 10)

    for row_index, net in enumerate(ordered_nets):
        y = first_row_y - row_index * row_height
        color = net_color(net)
        sheets = net_to_sheets[net]
        c.setFillColorRGB(*color)
        c.setFont(regular_font, 5.2)
        c.drawString(left + 12, y - 1.8, net)
        c.drawRightString(595, y - 1.8, str(net_pad_count.get(net, 0)))
        c.drawString(635, y - 1.8, ", ".join(f"{sheet:02d}" for sheet in sheets))
        c.setStrokeColorRGB(*color)
        c.setLineWidth(0.45)
        c.line(885, y, sheet_end_x + 4, y)
        for sheet in sheets:
            x = sheet_start_x + (sheet - 1) * sheet_step
            c.setFillColorRGB(*color)
            c.rect(x - 2.0, y - 2.0, 4.0, 4.0, stroke=0, fill=1)

    c.setFillColorRGB(0.76, 0.05, 0.05)
    c.setFont(bold_font, 7)
    c.drawString(left + 12, MATRIX_BOTTOM + 17, "ПИТАНИЕ")
    c.setFillColorRGB(0.04, 0.24, 0.76)
    c.drawString(left + 95, MATRIX_BOTTOM + 17, "ИНТЕРФЕЙСЫ")
    c.setFillColorRGB(0.48, 0.05, 0.55)
    c.drawString(left + 205, MATRIX_BOTTOM + 17, "AWR2944P")
    c.setFillColorRGB(0.18, 0.18, 0.18)
    c.drawString(left + 285, MATRIX_BOTTOM + 17, "GND И ПРОЧИЕ ЦЕПИ")
    c.drawRightString(right - 12, MATRIX_BOTTOM + 17, f"МЕЖЛИСТОВЫХ СЕТЕЙ: {len(ordered_nets)}")


def build_overlay(
    path: Path,
    regular_font: str,
    bold_font: str,
    net_to_sheets: dict[str, list[int]],
    net_pad_count: dict[str, int],
) -> None:
    c = canvas.Canvas(str(path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    c.setTitle("RADAR D79 R9 full element schematic master")
    c.setSubject("31 native schematic sheets with RF tract and eight 8-element antenna arrays")
    c.setFillColorRGB(0.08, 0.08, 0.08)
    c.setFont(bold_font, 34)
    c.drawString(25, PAGE_HEIGHT - 55, "RADAR D79, 24 В. ПОЛНАЯ ЭЛЕМЕНТНАЯ СХЕМА. PCB v0.8.0 R9")
    c.setFont(regular_font, 17)
    c.drawString(
        25,
        PAGE_HEIGHT - 87,
        "Все 31 лист схемы сведены на одно расширенное полотно и связаны полным реестром межлистовых электрических сетей.",
    )
    c.setFont(regular_font, 13)
    c.drawString(
        25,
        PAGE_HEIGHT - 116,
        "Система гражданского наблюдения и сопровождения БПЛА. Исходные элементы и проводники сохранены в векторном виде.",
    )
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(2)
    c.line(25, PAGE_HEIGHT - 140, PAGE_WIDTH - 25, PAGE_HEIGHT - 140)

    for index in range(32):
        x, y = cell_origin(index)
        c.setStrokeColorRGB(0.45, 0.45, 0.45)
        c.setLineWidth(1)
        c.rect(x + 4, y + 4, CELL_WIDTH - 8, CELL_HEIGHT - 8, stroke=1, fill=0)
    rf_x, rf_y = cell_origin(0)
    draw_rf_tile(c, rf_x, rf_y, regular_font, bold_font)
    draw_connectivity_matrix(c, net_to_sheets, net_pad_count, regular_font, bold_font)
    c.showPage()
    c.save()


def merge_source_pages(source_pdf: Path, overlay_pdf: Path, output_pdf: Path) -> None:
    source = PdfReader(str(source_pdf))
    if len(source.pages) < 32:
        raise ValueError(f"Expected at least 32 schematic pages, found {len(source.pages)}")
    master = PdfReader(str(overlay_pdf)).pages[0]
    for tile_index in range(1, 32):
        source_page = source.pages[tile_index]
        source_w = float(source_page.mediabox.width)
        source_h = float(source_page.mediabox.height)
        available_w = CELL_WIDTH - 16
        available_h = CELL_HEIGHT - 16
        scale = min(available_w / source_w, available_h / source_h)
        x, y = cell_origin(tile_index)
        tx = x + (CELL_WIDTH - source_w * scale) / 2
        ty = y + (CELL_HEIGHT - source_h * scale) / 2
        master.merge_transformed_page(
            source_page,
            Transformation().scale(scale).translate(tx, ty),
            over=False,
        )

    writer = PdfWriter()
    writer.add_page(master)
    writer.add_metadata(
        {
            "/Title": "RADAR D79 24 V, full element schematic, R9",
            "/Subject": "One-sheet vector master with RF tract and antennas",
            "/Creator": "Altium source release master builder",
        }
    )
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as stream:
        writer.write(stream)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--connectivity-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    net_to_sheets, net_pad_count, unresolved = extract_cross_sheet_nets(
        args.source,
        args.binding,
    )
    if not net_to_sheets:
        raise ValueError("No cross-sheet electrical nets were extracted")
    if len(unresolved) > 5:
        raise ValueError(f"Too many unresolved Altium net tokens: {unresolved}")
    write_connectivity_csv(args.connectivity_csv, net_to_sheets)
    regular_font, bold_font = register_fonts()
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
        overlay_path = Path(temporary.name)
    try:
        build_overlay(
            overlay_path,
            regular_font,
            bold_font,
            net_to_sheets,
            net_pad_count,
        )
        merge_source_pages(args.source, overlay_path, args.output)
    finally:
        overlay_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
