from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PAGE_WIDTH = 6740.0
PAGE_HEIGHT = 2600.0
TITLE_HEIGHT = 190.0
GRID_BOTTOM = 25.0
CELL_WIDTH = 840.0
CELL_HEIGHT = 590.0


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


def build_overlay(path: Path, regular_font: str, bold_font: str) -> None:
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
        "Все 31 лист схемы сведены на одно расширенное полотно. Система гражданского наблюдения и сопровождения БПЛА.",
    )
    c.setFont(regular_font, 13)
    c.drawString(
        25,
        PAGE_HEIGHT - 116,
        "Масштаб элементов исходных листов сохранён в векторном виде. Для чтения используйте увеличение PDF.",
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    regular_font, bold_font = register_fonts()
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
        overlay_path = Path(temporary.name)
    try:
        build_overlay(overlay_path, regular_font, bold_font)
        merge_source_pages(args.source, overlay_path, args.output)
    finally:
        overlay_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
