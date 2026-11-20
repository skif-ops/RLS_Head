from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml
from docx.shared import Cm, Pt, RGBColor


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

from docx_style_policy import audit_docx, transform_docx  # noqa: E402


FONT = "Times New Roman"
TABLE_HEADER = "D9E1F2"
TABLE_BORDER = "D9D9D9"


def set_run_font(run, size: int, bold: bool = False) -> None:
    run.font.name = FONT
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn("w:cs"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def format_paragraph(paragraph, *, table: bool = False, centered: bool = False) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1.0
    fmt.left_indent = Cm(0)
    fmt.right_indent = Cm(0)
    fmt.first_line_indent = Cm(0 if table else 1.25)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.JUSTIFY


def keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:keepNext")) is None:
        p_pr.append(OxmlElement("w:keepNext"))


def set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 80, start: int = 90, bottom: int = 80, end: int = 90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is not None:
        tbl_pr.remove(borders)
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}'
        f'><w:top w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/>'
        f'<w:left w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/>'
        f'<w:insideV w:val="single" w:sz="4" w:color="{TABLE_BORDER}"/></w:tblBorders>'
    )
    tbl_pr.append(borders)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, 12)


def configure_document() -> Document:
    doc = Document()
    doc.settings.odd_and_even_pages_header_footer = True
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), FONT)
    normal._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), FONT)
    normal._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(14)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[name]
        style.font.name = FONT
        style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), FONT)
        style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), FONT)
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(14)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.first_line_indent = Cm(1.25)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_pr = style._element.get_or_add_pPr()
        p_bdr = p_pr.find(qn("w:pBdr"))
        if p_bdr is not None:
            p_pr.remove(p_bdr)

    for header_part in (section.first_page_header, section.header, section.even_page_header):
        header = header_part.paragraphs[0]
        header.text = "R10.3.37 | Расчет импеданса и стека | EVT"
        format_paragraph(header, table=True, centered=True)
        for run in header.runs:
            set_run_font(run, 12)

    for footer_part in (section.first_page_footer, section.footer, section.even_page_footer):
        footer = footer_part.paragraphs[0]
        footer.text = "R10.3.37 | Лист "
        format_paragraph(footer, table=True, centered=True)
        for run in footer.runs:
            set_run_font(run, 12)
        add_page_field(footer)
    return doc


def add_text(doc: Document, text: str, *, bold_prefix: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    format_paragraph(paragraph)
    if bold_prefix and text.startswith(bold_prefix):
        first = paragraph.add_run(bold_prefix)
        set_run_font(first, 14, bold=True)
        rest = paragraph.add_run(text[len(bold_prefix):])
        set_run_font(rest, 14)
    else:
        run = paragraph.add_run(text)
        set_run_font(run, 14)


def add_heading(doc: Document, text: str, level: int = 1, *, page_break_before: bool = False) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    format_paragraph(paragraph)
    paragraph.paragraph_format.page_break_before = page_break_before
    run = paragraph.add_run(text)
    set_run_font(run, 14, bold=True)
    keep_with_next(paragraph)


def add_equation(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    format_paragraph(paragraph)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    math_para = OxmlElement("m:oMathPara")
    math = OxmlElement("m:oMath")
    math_run = OxmlElement("m:r")
    run_props = OxmlElement("m:rPr")
    style = OxmlElement("m:sty")
    style.set(qn("m:val"), "p")
    run_props.append(style)
    math_text = OxmlElement("m:t")
    math_text.set(qn("xml:space"), "preserve")
    math_text.text = text
    math_run.extend([run_props, math_text])
    math.append(math_run)
    math_para.append(math)
    paragraph._p.append(math_para)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    set_repeat_header(table.rows[0])
    prevent_row_split(table.rows[0])
    for index, text in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, TABLE_HEADER)
        set_cell_margins(cell)
        cell.text = text
        for paragraph in cell.paragraphs:
            format_paragraph(paragraph, table=True, centered=True)
            for run in paragraph.runs:
                set_run_font(run, 12, bold=True)
    for row_data in rows:
        cells = table.add_row().cells
        prevent_row_split(table.rows[-1])
        for index, text in enumerate(row_data):
            cell = cells[index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            cell.text = str(text)
            for paragraph in cell.paragraphs:
                format_paragraph(paragraph, table=True)
                for run in paragraph.runs:
                    set_run_font(run, 12)
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Cm(width)


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def build_document(data: dict, output_path: Path) -> dict:
    doc = configure_document()
    title = doc.add_paragraph(style="Title")
    format_paragraph(title)
    title_run = title.add_run("Предварительный расчет импеданса и производственного стека платы R10.3.37")
    set_run_font(title_run, 14, bold=True)
    keep_with_next(title)

    add_text(doc, "Версия 0.9.3.37. Ревизия R10.3.37_REZONIT_DOCUMENT_RECALC. Расчетный документ для подготовки EVT.")
    add_text(doc, "Production authority = NOT_AUTHORIZED", bold_prefix="Production authority = NOT_AUTHORIZED")
    add_text(
        doc,
        "Документ фиксирует предварительный расчет одиночных и дифференциальных линий, производственный стек с заказной толщиной 2,00 мм и чувствительность СВЧ-профиля к допускам. Стек составлен из опубликованных производственных толщин и правил Резонита. R10.3.37 сохранена в бинарном формате Altium, 559 полигонов перезалиты, полный DRC завершен с нулевым числом предупреждений, нарушений и неразведенных соединений. Окончательные ширины назначает изготовитель после расчета фактического прессованного стека, модели травления, шероховатости меди и контрольного купона.",
    )

    add_heading(doc, "1. Назначение")
    add_text(
        doc,
        "Расчет применяется для проверки круглой платы локатора R10.3.37 на базе AWR2944P. Он задает исходную геометрию, требования к заказу и перечень параметров, которые требуется подтвердить до выпуска Gerber, ODB++ и IPC-2581. Расчет не является электродинамической моделью антенной решетки и не подтверждает готовность платы к производству.",
    )

    add_heading(doc, "2. Исходные данные")
    add_heading(doc, "2.1. Материал СВЧ", 2)
    add_table(
        doc,
        ["Параметр", "Значение", "Применение"],
        [
            ["Материал", "RO3003G2", "D1 и D9"],
            ["Стандартная толщина", "0,005 дюйма, 0,127 мм", "Расстояние L1-L2 и L9-L10"],
            ["Расчетная Dk", "3,07 при 77 ГГц", "Предварительный расчет RF50"],
            ["Технологическая Dk", "3,00 ±0,04 при 10 ГГц", "Оценка разброса"],
            ["Df", "0,0011 при 10 ГГц", "Материальные потери"],
            ["Медь", "готовая внешняя 45 мкм, типовой ED-процесс Резонита", "СВЧ-слои"],
        ],
        [5.0, 5.0, 6.0],
    )
    add_heading(doc, "2.2. Производственные толщины FR-4", 2)
    add_text(
        doc,
        "Для симметричной сборки приняты RO3003G2 толщиной 0,127 мм, препреги 2116 толщиной 0,115 и 0,140 мм, препрег 7628 толщиной 0,193 мм и ядра FR-4 Tg150 толщиной 0,100 мм. Пакеты D4, D5 и D6 выбраны с учетом опубликованного Резонитом правила заполнения вокруг внутренних слоев меди 105 мкм. Значения Dk FR-4 взяты из опубликованной статистики Резонита и подлежат уточнению по фактической партии.",
    )

    add_heading(doc, "3. Производственный стек")
    stack_rows = []
    for row in data["stackup"]:
        kind = "Медь" if row["kind"] == "copper" else "Диэлектрик"
        material = (
            row["material"]
            .replace("standard 5 mil", "стандарт 5 mil")
            .replace("VLP base copper", "базовая медь VLP")
            .replace("prepreg", "препрег")
            .replace("core", "ядро")
            .replace("copper", "медь")
        )
        stack_rows.append([row["item"], kind, fmt(float(row["thickness_mm"]), 3), material])
    stack_rows.append(["Итого", "", fmt(data["nominal_stack_thickness_before_mask_finish_mm"], 3), "До маски и финиша"])
    add_table(doc, ["Элемент", "Тип", "Толщина, мм", "Материал"], stack_rows, [2.0, 3.0, 3.0, 8.0])
    add_text(
        doc,
        f"Номинальная сумма меди и диэлектриков равна {fmt(data['nominal_stack_thickness_before_mask_finish_mm'], 3)} мм до маски и финиша. В заказе указывается готовая толщина 2,00 мм. Изготовитель должен вернуть согласованный прессованный стек и подтвердить готовую толщину до запуска EVT. Более узкий допуск допускается только после письменного подтверждения изготовителя.",
    )

    add_heading(doc, "4. Методика расчета")
    add_heading(doc, "4.1. Одиночная микрополосковая линия", 2)
    add_text(
        doc,
        "Для начального выбора ширины применена замкнутая модель Hammerstad-Jensen с поправкой на конечную толщину меди. Обозначения: W представляет ширину проводника, h представляет расстояние до опорного слоя, t представляет толщину меди, а εeff представляет эффективную диэлектрическую проницаемость.",
    )
    add_equation(doc, "Z₀ = 60/√εeff · ln[f(u)/u + √(1 + (2/u)²)],    u = W/h")
    add_equation(doc, "f(u) = 6 + (2π - 6) · exp[-(30,666/u)^0,7528]")
    add_text(
        doc,
        "Поправка толщины меди вводится через эффективное отношение W/h. В XLSX приведены все промежуточные коэффициенты u, t/h, du1, dur, a(u), b(Dk), εeff и f(u), поэтому расчет можно проверить и повторить после изменения стека.",
    )

    add_heading(doc, "4.2. Внутренние одиночные линии и дифференциальные пары", 2, page_break_before=True)
    add_text(
        doc,
        "CLOCK50, USB90 и CAN120 проходят на внутренних слоях и образуют несимметричные встроенные линии между двумя соседними медными слоями. Приведенная замкнутая модель учитывает только ближайший опорный слой и применяется как проверочная оценка диапазона. Для USB и CAN FD параметр S представляет зазор между проводниками. Полученные размеры нельзя переносить в производственные правила без расчета несимметричного полоска в полевом решателе на фактическом прессованном стеке.",
    )
    add_equation(doc, "Zdiff = 2Z₀ · [1 - 0,48 · exp(-0,96S/h)]")

    add_heading(doc, "5. Результаты расчета профилей")
    profile_rows = []
    profile_names = {
        "RF50_FACTORY_ED45_L1_L2": "RF50, типовой процесс",
        "RF50_SPECIAL_RLD15_L1_L2": "RF50, специальный процесс",
        "CLOCK50_L3_L2": "CLOCK50",
        "USB90_L8_L9": "USB90, внутренний слой",
        "CAN120_L8_L9": "CAN120",
        "USB90_L10_L9": "USB90, нижний слой",
        "CAN120_L10_L9": "CAN120, нижний слой",
    }
    for row in data["profiles"]:
        profile_rows.append(
            [
                profile_names[row["profile"]],
                fmt(row["target_ohm"], 1),
                f'{row["layer"]}/{row["reference"].split("_")[0]}',
                fmt(row["height_mm"], 3),
                fmt(row["copper_mm"], 3),
                fmt(row["width_mm"], 5),
                "-" if row["gap_mm"] == "" else fmt(row["gap_mm"], 3),
                fmt(row["calculated_ohm"], 3),
            ]
        )
    add_table(
        doc,
        ["Профиль", "Требуемое значение, Ом", "Слой/опора", "h, мм", "t, мм", "W, мм", "S, мм", "Расчет, Ом"],
        profile_rows,
        [2.7, 1.6, 2.0, 1.3, 1.3, 1.6, 1.4, 1.7],
    )
    add_text(
        doc,
        "Для открытой линии RF50 по типовому процессу Резонита получена ширина 0,27217 мм при h = 0,127 мм, Dk = 3,16 и готовой меди 0,045 мм. Альтернативная ширина 0,30145 мм относится только к специальному процессу с готовой RLD-медью 0,015 мм и не применяется без письменного подтверждения изготовителя. Значения CLOCK50, USB90 и CAN120 приведены только как проверочная оценка для ближайшего опорного слоя. Окончательная геометрия определяется полевым расчетом изготовителя.",
    )

    add_heading(doc, "5.1. Фактический СВЧ рисунок R10.3.37", 2)
    add_text(
        doc,
        "Все восемь СВЧ цепей TI_RX1-TI_RX4 и TI_TX1-TI_TX4 расположены на верхнем слое. В текущем рисунке применены секции шириной 0,10160, 0,21336 и 0,21340 мм. Эти секции относятся к синтезу последовательной антенной решетки и не являются одной линией 50 Ом. Автоматическая замена их на ширину RF50 запрещена. Каждая секция должна быть сопоставлена с полной электродинамической моделью антенного узла.",
    )
    add_text(
        doc,
        "Проверка геометрии не обнаружила сигнальных переходных отверстий, проходящих через L2 ближе 0,30 мм к СВЧ дорожкам. Этот результат подтверждает отсутствие близких сквозных нарушителей опорного слоя, но не заменяет расчет поля и токов возврата.",
    )

    add_heading(doc, "6. Чувствительность профиля RF50")
    sensitivity_rows = []
    for row in data["rf_sensitivity"]:
        sensitivity_rows.append(
            [
                row["case"],
                fmt(row["width_mm"], 5),
                fmt(row["height_mm"], 5),
                fmt(row["er"], 3),
                fmt(row["calculated_ohm"], 3),
                fmt(row["deviation_pct"], 2) + " %",
            ]
        )
    add_table(
        doc,
        ["Случай", "W, мм", "h, мм", "Dk", "Z0, Ом", "Отклонение"],
        sensitivity_rows,
        [4.2, 2.2, 2.2, 1.8, 2.4, 2.4],
    )
    add_text(
        doc,
        "При изменении толщины D1 на ±10 % расчетное отклонение RF50 составляет от -6,38 до +5,97 %. При изменении ширины на ±0,015 мм отклонение составляет от -3,00 до +3,21 %. Переход от Dk 3,16 к 3,03 изменяет расчет примерно на +1,77 %. Поэтому изготовитель должен контролировать прессованную толщину, готовую толщину меди, травление и шероховатость, а не только номинальную марку материала.",
    )

    add_heading(doc, "7. Длина волны в линии и оценка потерь")
    add_equation(doc, "λg = c/(f√εeff),    lλ/4 = λg/4")
    wavelength_rows = [
        [fmt(row["frequency_ghz"], 1), fmt(row["lambda0_mm"], 5), fmt(row["lambda_g_mm"], 5), fmt(row["quarter_wave_mm"], 5)]
        for row in data["guided_wavelengths"]
    ]
    add_table(doc, ["Частота, ГГц", "λ0, мм", "λg, мм", "λg/4, мм"], wavelength_rows, [3.5, 4.0, 4.0, 4.0])
    add_text(
        doc,
        "Оценка потерь использует опубликованное Rogers значение 1,3 дБ/дюйм при 77 ГГц для тестовой линии на RO3003G2 толщиной 5 mil. Это линейная оценка длины, а не полный баланс фидера. Переходы корпуса, разветвления, шероховатость, излучение и несогласование учитываются отдельно.",
    )
    add_equation(doc, "Lest = 1,3 дБ/дюйм · lмм/25,4")
    loss_rows = [
        [fmt(row["length_mm"], 0), fmt(row["datasheet_loss_db_per_in_at_77ghz"], 1), fmt(row["estimated_loss_db"], 4)]
        for row in data["insertion_loss_length_estimate"]
    ]
    add_table(doc, ["Длина, мм", "Исходное значение, дБ/дюйм", "Оценка потерь, дБ"], loss_rows, [4.0, 6.0, 5.0])

    spacer = doc.add_paragraph()
    format_paragraph(spacer)
    add_heading(doc, "8. Проверка R10.3.37 в Altium")
    validation = data["native_validation"]
    add_table(
        doc,
        ["Проверка", "Результат"],
        [
            ["Бинарный PcbDoc", Path(validation["native_pcbdoc"]["path"]).name],
            ["SHA-256 PcbDoc", validation["native_pcbdoc"]["sha256"]],
            ["Перезаливка полигонов", "Выполнена и сохранена"],
            ["Предупреждения DRC", str(validation["warnings"])],
            ["Нарушения правил DRC", str(validation["rule_violations"])],
            ["Неразведенные соединения", str(validation["unrouted_net_violations"])],
        ],
        [6.0, 10.0],
    )
    add_text(
        doc,
        "DRC 0 подтверждает соответствие активному набору правил Altium. Он не подтверждает электродинамические характеристики антенны, рассчитанный импеданс, размеры посадочных мест по документации изготовителей и технологическую выполнимость выбранного гибридного стека.",
    )
    culture = data["routing_culture_validation"]
    counts = culture["counts"]
    add_heading(doc, "8.1. Строгий геометрический аудит трассировки", 2)
    add_table(
        doc,
        ["Проверка", "Результат"],
        [
            ["Итог строгого контроля", culture["gate"]],
            ["Узлы, требующие обязательной переработки", str(counts["junctions_hard_rework"])],
            ["Тупики или окончания, требующие адресной проверки", str(counts["dangling_or_stub_ends"])],
            ["Длинные неортогональные сегменты", str(counts["long_off_angle_segments"])],
            ["Группы совпадающих сегментов", str(counts["coincident_segment_groups"])],
        ],
        [8.0, 8.0],
    )
    add_text(
        doc,
        "Строгий геометрический контроль не пройден. Часть находок может относиться к допустимым выходам из контактных площадок, полигональной меди и синтезированным секциям антенной решетки, но до адресной классификации и исправления остальных находок трассировку нельзя считать полностью соответствующей требованиям ГОСТ, IPC и инженерной культуры.",
    )

    add_heading(doc, "9. Требования к изготовителю")
    requirements = [
        "Подтвердить возможность гибридной десятислойной сборки RO3003G2 0,127 мм с FR-4 Tg150.",
        "Вернуть фактические прессованные толщины, Dk, Df, шероховатость меди и итоговую толщину внешней меди после металлизации.",
        "Рассчитать RF50, CLOCK50, USB90 и CAN120 в полевом решателе на фактическом стеке.",
        "Добавить измерительный купон для одиночной линии 50 Ом и дифференциальных пар 90 и 120 Ом.",
        "Предоставить отчет измерений и фактический стек вместе с партией EVT.",
        "Не заменять RO3003G2 и согласованный тип внешней меди без нового расчета антенного узла и фидеров.",
    ]
    for index, item in enumerate(requirements, start=1):
        add_text(doc, f"{index}. {item}")

    add_heading(doc, "10. Источники")
    source_rows = [
        ["Rogers RO3003G2 Data Sheet", data["material_source_url"]],
        ["Резонит, типовые сборки многослойных плат", data["fabricator_source_url"]],
        ["Резонит, измеренные значения материалов и контроль импеданса", data["fabricator_impedance_source_url"]],
        ["Резонит, толщина меди для расчетов", data["fabricator_copper_source_url"]],
        ["Резонит, требования к заказу импеданса", data["fabricator_order_source_url"]],
        ["Резонит, правила конструкции", data["fabricator_construction_rules_url"]],
        ["Резонит, анализ диапазона 76...81 ГГц", data["fabricator_77ghz_article_url"]],
    ]
    add_table(doc, ["Источник", "Ссылка"], source_rows, [6.0, 10.0])

    add_heading(doc, "11. Заключение")
    add_text(
        doc,
        f"Расчетный стек симметричен и использует опубликованные производственные толщины. Номинальная сумма составляет {fmt(data['nominal_stack_thickness_before_mask_finish_mm'], 3)} мм до маски и финиша. Предварительный профиль RF50 для типового ED-процесса равен 0,27217 мм. R10.3.37 прошла полный DRC с нулевым числом предупреждений, нарушений и неразведенных соединений, но строгий геометрический аудит трассировки имеет результат FAIL. До исправления и повторного аудита геометрии, подтверждения гибридного стека изготовителем, полевого расчета, измерительного купона, полного электродинамического расчета антенного узла и размерного аудита посадочных мест production authority сохраняется NOT_AUTHORIZED.",
    )

    raw_path = output_path.with_suffix(".raw.docx")
    doc.save(raw_path)
    transformed, policy_report = transform_docx(raw_path.read_bytes(), version="0.9.3.37-R10.3.37")
    output_path.write_bytes(transformed)
    raw_path.unlink()
    audit = audit_docx(output_path.read_bytes())
    return {"output": str(output_path), "policy": policy_report, "audit": audit}


def main() -> None:
    calc_dir = REPO / "hardware" / "radar" / "altium" / "RADAR_D79_v0.9.0_R10_ENGINEERING_REWORK" / "07_Расчеты_СВЧ"
    data = json.loads((calc_dir / "R10_расчет_импеданса.json").read_text(encoding="utf-8"))
    result = build_document(data, calc_dir / "R10_расчет_импеданса.docx")
    qa_path = calc_dir / "R10_расчет_импеданса_docx_QA.json"
    qa_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["qa_path"] = str(qa_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
