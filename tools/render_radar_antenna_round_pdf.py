from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


TARGET_NETS = {
    204: "RX1",
    205: "RX2",
    206: "RX3",
    207: "RX4",
    220: "TX1",
    221: "TX2",
    222: "TX3",
    223: "TX4",
}

NET_COLORS = {
    204: colors.HexColor("#0B4F9C"),
    205: colors.HexColor("#1D70B7"),
    206: colors.HexColor("#3E8BDD"),
    207: colors.HexColor("#6BA8EA"),
    220: colors.HexColor("#9E1F1F"),
    221: colors.HexColor("#C93434"),
    222: colors.HexColor("#E05252"),
    223: colors.HexColor("#F07E7E"),
}


def field(line: str, name: str) -> str | None:
    match = re.search(rf"\|{re.escape(name)}=([^|\r\n]+)", line)
    return match.group(1) if match else None


def mil_to_mm(line: str, name: str) -> float:
    raw = field(line, name)
    if raw is None or not raw.endswith("mil"):
        raise ValueError(f"missing {name}=...mil")
    return float(raw[:-3]) * 0.0254


def load_geometry(pcb: Path) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    fills: list[tuple[int, str]] = []
    tracks: list[tuple[int, str]] = []
    for line in pcb.read_bytes().decode("cp1252").splitlines():
        net_raw = field(line, "NET")
        if net_raw is None or field(line, "LAYER") != "TOP":
            continue
        net = int(net_raw)
        if net not in TARGET_NETS:
            continue
        record = field(line, "RECORD")
        if record == "Fill":
            fills.append((net, line))
        elif record == "Track" and int(field(line, "INDEXFORSAVE") or 0) >= 8000:
            tracks.append((net, line))
    return fills, tracks


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/times.ttf")
    bold = Path("C:/Windows/Fonts/timesbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("TimesNewRoman", str(regular)))
        pdfmetrics.registerFont(TTFont("TimesNewRomanBold", str(bold)))
        return "TimesNewRoman", "TimesNewRomanBold"
    return "Times-Roman", "Times-Bold"


def draw_footer(c: canvas.Canvas, regular_font: str, page_number: int) -> None:
    width, _ = landscape(A4)
    c.setFont(regular_font, 9)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawCentredString(width / 2, 9 * mm, f"Антенный узел D79, ревизия 0.8.0 R9. Лист {page_number}")


def draw_title(c: canvas.Canvas, bold_font: str, regular_font: str, subtitle: str) -> None:
    width, height = landscape(A4)
    c.setFillColor(colors.black)
    c.setFont(bold_font, 18)
    c.drawString(18 * mm, height - 18 * mm, "Антенный узел круглой платы D79")
    c.setFont(regular_font, 11)
    c.drawString(18 * mm, height - 25 * mm, subtitle)


def draw_board_page(
    c: canvas.Canvas,
    manifest: dict,
    fills: list[tuple[int, str]],
    tracks: list[tuple[int, str]],
    regular_font: str,
    bold_font: str,
) -> None:
    width, height = landscape(A4)
    draw_title(
        c,
        bold_font,
        regular_font,
        "Вид сверху. Восемь элементов в каждом из четырёх RX и четырёх TX каналов",
    )

    scale = 1.50 * mm
    origin_x = 18 * mm
    origin_y = 18 * mm

    def point(x_mm: float, y_mm: float) -> tuple[float, float]:
        return origin_x + x_mm * scale, origin_y + y_mm * scale

    center_x, center_y = point(50.0, 50.0)
    radius = 39.5 * scale
    c.setFillColor(colors.HexColor("#EAF0EB"))
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.setLineWidth(0.45 * mm)
    c.circle(center_x, center_y, radius, fill=1, stroke=1)

    c.setStrokeColor(colors.HexColor("#A0A7A2"))
    c.setLineWidth(0.15 * mm)
    c.setDash(1.5 * mm, 1.2 * mm)
    c.line(center_x - radius, center_y, center_x + radius, center_y)
    c.line(center_x, center_y - radius, center_x, center_y + radius)
    c.setDash()

    c.setFillColor(colors.HexColor("#D9DEDA"))
    c.setStrokeColor(colors.HexColor("#9EA69F"))
    c.roundRect(*point(33.0, 17.0), 34.0 * scale, 27.0 * scale, 3 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#525A54"))
    c.setFont(regular_font, 9)
    c.drawCentredString(center_x, point(50.0, 30.0)[1], "Зона электроники на тыльной стороне")

    for net, line in tracks:
        c.setStrokeColor(NET_COLORS[net])
        c.setLineWidth(max(0.25 * mm, mil_to_mm(line, "WIDTH") * scale))
        c.line(*point(mil_to_mm(line, "X1"), mil_to_mm(line, "Y1")), *point(mil_to_mm(line, "X2"), mil_to_mm(line, "Y2")))

    for net, line in fills:
        x1, x2 = sorted((mil_to_mm(line, "X1"), mil_to_mm(line, "X2")))
        y1, y2 = sorted((mil_to_mm(line, "Y1"), mil_to_mm(line, "Y2")))
        px, py = point(x1, y1)
        c.setFillColor(NET_COLORS[net])
        c.setStrokeColor(colors.HexColor("#202020"))
        c.setLineWidth(0.08 * mm)
        c.rect(px, py, (x2 - x1) * scale, (y2 - y1) * scale, fill=1, stroke=1)

    c.setFont(bold_font, 8)
    c.setFillColor(colors.black)
    for section in manifest["sections"]:
        name = str(section["net_name"]).replace("TI_", "")
        x_mm = float(section["x_center_mm"])
        top_mm = float(section["patch_centers_y_mm"][-1]) + float(section["patch_length_mm"]) / 2.0
        x, y = point(x_mm, top_mm + 1.0)
        c.drawCentredString(x, y, name)

    rf_left, rf_bottom = point(34.0, 48.0)
    rf_right, rf_top = point(66.5, 66.0)
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.3 * mm)
    c.setDash(1.8 * mm, 1.2 * mm)
    c.rect(rf_left, rf_bottom, rf_right - rf_left, rf_top - rf_bottom, fill=0, stroke=1)
    c.setDash()

    info_x = 165 * mm
    info_y = height - 42 * mm
    c.setFillColor(colors.black)
    c.setFont(bold_font, 12)
    c.drawString(info_x, info_y, "Состав антенного раскрыва")
    c.setFont(regular_font, 10)
    lines = [
        "RX1...RX4: 4 канала по 8 элементов",
        "TX1...TX4: 4 канала по 8 элементов",
        "Всего излучателей: 64",
        "Диаметр платы: 79 мм",
        "Рабочая частота расчёта: 78,5 ГГц",
        "Шаг элементов: 1,5276 мм",
        "Расчётный сектор по углу места: не менее ±20°",
        "Нативный DRC Altium: 0 нарушений",
    ]
    for line in lines:
        info_y -= 6 * mm
        c.drawString(info_x, info_y, line)

    info_y -= 8 * mm
    c.setFont(bold_font, 10)
    c.drawString(info_x, info_y, "Ограничение")
    c.setFont(regular_font, 9)
    for line in (
        "Геометрия получена расчётом множителя решётки.",
        "Полно-волновое моделирование и измерения образца",
        "не выполнены. Допуск к производству не выдан.",
    ):
        info_y -= 5 * mm
        c.drawString(info_x, info_y, line)

    c.setFont(regular_font, 8.5)
    c.setFillColor(colors.HexColor("#404040"))
    c.drawString(18 * mm, 14 * mm, "Синий цвет: приёмные каналы RX. Красный цвет: передающие каналы TX.")
    draw_footer(c, regular_font, 1)
    c.showPage()


def draw_detail_page(
    c: canvas.Canvas,
    manifest: dict,
    fills: list[tuple[int, str]],
    tracks: list[tuple[int, str]],
    regular_font: str,
    bold_font: str,
) -> None:
    width, height = landscape(A4)
    draw_title(c, bold_font, regular_font, "Увеличенный вид верхней СВЧ-зоны круглой платы")

    view = (32.0, 45.0, 67.5, 66.5)
    x_min, y_min, x_max, y_max = view
    box_x, box_y = 18 * mm, 28 * mm
    box_w, box_h = 185 * mm, 135 * mm
    scale = min(box_w / (x_max - x_min), box_h / (y_max - y_min))

    def point(x_mm: float, y_mm: float) -> tuple[float, float]:
        return box_x + (x_mm - x_min) * scale, box_y + (y_mm - y_min) * scale

    c.setFillColor(colors.HexColor("#F6F8F6"))
    c.setStrokeColor(colors.HexColor("#777777"))
    c.rect(box_x, box_y, box_w, box_h, fill=1, stroke=1)

    for net, line in tracks:
        c.setStrokeColor(NET_COLORS[net])
        c.setLineWidth(max(0.28 * mm, mil_to_mm(line, "WIDTH") * scale))
        c.line(*point(mil_to_mm(line, "X1"), mil_to_mm(line, "Y1")), *point(mil_to_mm(line, "X2"), mil_to_mm(line, "Y2")))

    for net, line in fills:
        x1, x2 = sorted((mil_to_mm(line, "X1"), mil_to_mm(line, "X2")))
        y1, y2 = sorted((mil_to_mm(line, "Y1"), mil_to_mm(line, "Y2")))
        px, py = point(x1, y1)
        c.setFillColor(NET_COLORS[net])
        c.setStrokeColor(colors.HexColor("#202020"))
        c.setLineWidth(0.08 * mm)
        c.rect(px, py, (x2 - x1) * scale, (y2 - y1) * scale, fill=1, stroke=1)

    c.setFont(bold_font, 10)
    c.setFillColor(colors.black)
    for section in manifest["sections"]:
        name = str(section["net_name"]).replace("TI_", "")
        x_mm = float(section["x_center_mm"])
        top_mm = float(section["patch_centers_y_mm"][-1]) + float(section["patch_length_mm"]) / 2.0
        x, y = point(x_mm, top_mm + 0.45)
        c.drawCentredString(x, y, name)

    dim_x = 210 * mm
    dim_y = height - 42 * mm
    c.setFont(bold_font, 12)
    c.drawString(dim_x, dim_y, "Основные размеры")
    c.setFont(regular_font, 9)
    for line in (
        "Элементов на канал: 8",
        "Шаг центров: 1,5276 мм",
        "Длина излучателя: 1,08 мм",
        "Ширины: 1,35; 1,05; 0,82; 0,65 мм",
        "Питание: центральное симметричное",
        "Фазовые участки: 2,73; 2,85; 3,06 мм",
        "Материал СВЧ-слоя: RO3003, 0,127 мм",
    ):
        dim_y -= 7 * mm
        c.drawString(dim_x, dim_y, line)

    dim_y -= 8 * mm
    c.setFont(bold_font, 10)
    c.drawString(dim_x, dim_y, "Расчётная диаграмма")
    c.setFont(regular_font, 9)
    for line in (
        "76 ГГц: уровень на ±20° равен -2,85 дБ",
        "78,5 ГГц: уровень на ±20° равен -2,45 дБ",
        "81 ГГц: уровень на ±20° равен -2,08 дБ",
        "Прирост к версии с 2 элементами:",
        "2,07 дБ по расчёту множителя решётки",
    ):
        dim_y -= 6 * mm
        c.drawString(dim_x, dim_y, line)

    draw_footer(c, regular_font, 2)
    c.showPage()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a round-board antenna placement PDF")
    parser.add_argument("--pcb", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fills, tracks = load_geometry(args.pcb)
    if len(fills) != 64:
        raise ValueError(f"expected 64 radiator fills, found {len(fills)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    regular_font, bold_font = register_fonts()
    c = canvas.Canvas(str(args.output), pagesize=landscape(A4), pageCompression=1)
    c.setTitle("Антенный узел круглой платы D79, ревизия 0.8.0 R9")
    c.setAuthor("Проект EVT ГСН")
    c.setSubject("Расположение восьмиэлементных RX и TX каналов на круглой плате")
    draw_board_page(c, manifest, fills, tracks, regular_font, bold_font)
    draw_detail_page(c, manifest, fills, tracks, regular_font, bold_font)
    c.save()
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
