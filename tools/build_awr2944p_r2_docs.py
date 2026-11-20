from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from docx_style_policy import transform_docx


FONT = "Times New Roman"
BLUE = "D9EAF7"


def set_run_font(run, size: int, bold: bool = False, color: str = "000000") -> None:
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def set_paragraph_format(paragraph, *, table: bool = False, centered: bool = False) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1.0
    fmt.first_line_indent = Cm(0 if table else 1.25)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.JUSTIFY


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    keep_next = OxmlElement("w:keepNext")
    p_pr.append(keep_next)


def remove_paragraph_border(paragraph_or_style) -> None:
    p_pr = paragraph_or_style._element.get_or_add_pPr()
    border = p_pr.find(qn("w:pBdr"))
    if border is not None:
        p_pr.remove(border)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, end])
    set_run_font(run, 12)


def configure_document(title: str, code: str) -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(14)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        style = styles[name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(14)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.first_line_indent = Cm(1.25)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        remove_paragraph_border(style)

    if "Equation" not in [style.name for style in styles]:
        equation = styles.add_style("Equation", WD_STYLE_TYPE.PARAGRAPH)
    else:
        equation = styles["Equation"]
    equation.font.name = FONT
    equation._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    equation.font.size = Pt(14)
    equation.font.italic = True
    equation.paragraph_format.space_before = Pt(0)
    equation.paragraph_format.space_after = Pt(0)
    equation.paragraph_format.line_spacing = 1.0
    equation.paragraph_format.first_line_indent = Cm(1.25)
    equation.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    header = section.header.paragraphs[0]
    header.text = f"{code} | AWR2944P | EVT R2"
    set_paragraph_format(header, table=True, centered=True)
    for run in header.runs:
        set_run_font(run, 12)

    footer = section.footer.paragraphs[0]
    footer.text = f"{code} | Лист "
    set_paragraph_format(footer, table=True, centered=True)
    for run in footer.runs:
        set_run_font(run, 12)
    add_page_field(footer)

    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_format(p, centered=True)
    remove_paragraph_border(p)
    run = p.add_run(title)
    set_run_font(run, 14, bold=True)
    keep_with_next(p)

    p = doc.add_paragraph()
    set_paragraph_format(p, centered=True)
    r = p.add_run(f"{code}. Версия 0.2.0-EVT-R2. 09.11.2026. Только для EVT.")
    set_run_font(r, 14)

    p = doc.add_paragraph()
    set_paragraph_format(p, centered=True)
    r = p.add_run("Production authority = NOT_AUTHORIZED")
    set_run_font(r, 14, bold=True)
    doc.add_page_break()
    return doc


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_paragraph(style=f"Heading {level}")
    set_paragraph_format(p)
    run = p.add_run(text)
    set_run_font(run, 14, bold=True)
    keep_with_next(p)


def add_text(doc: Document, text: str, *, bold_prefix: str | None = None) -> None:
    p = doc.add_paragraph()
    set_paragraph_format(p)
    if bold_prefix and text.startswith(bold_prefix):
        first = p.add_run(bold_prefix)
        set_run_font(first, 14, bold=True)
        rest = p.add_run(text[len(bold_prefix):])
        set_run_font(rest, 14)
    else:
        run = p.add_run(text)
        set_run_font(run, 14)


def add_equation(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="Equation")
    set_paragraph_format(p)
    run = p.add_run(text)
    set_run_font(run, 14)
    run.font.italic = True


def add_numbered(doc: Document, items: list[str]) -> None:
    for index, item in enumerate(items, 1):
        add_text(doc, f"{index}. {item}")


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths_cm: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    set_repeat_table_header(table.rows[0])
    prevent_row_split(table.rows[0])
    for index, text in enumerate(headers):
        cell = table.rows[0].cells[index]
        set_cell_shading(cell, BLUE)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cell.text = text
        for p in cell.paragraphs:
            set_paragraph_format(p, table=True, centered=True)
            for run in p.runs:
                set_run_font(run, 12, bold=True)
    for row_data in rows:
        cells = table.add_row().cells
        prevent_row_split(table.rows[-1])
        for index, text in enumerate(row_data):
            cell = cells[index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = text
            for p in cell.paragraphs:
                set_paragraph_format(p, table=True)
                for run in p.runs:
                    set_run_font(run, 12)
    if widths_cm:
        for row in table.rows:
            for index, width in enumerate(widths_cm):
                row.cells[index].width = Cm(width)


def add_flow_diagram(doc: Document) -> None:
    add_table(
        doc,
        ["Этап", "Преобразование", "Выход"],
        [
            ["1", "АЦП и оконная обработка", "Комплексные отсчёты по RX и chirp"],
            ["2", "FFT по быстрому времени", "Дальность и комплексная амплитуда"],
            ["3", "FFT по медленному времени", "Радиальная скорость в каждом PRF"],
            ["4", "CFAR и объединение трёх PRF", "Одна подтверждённая отметка"],
            ["5", "Фазовая оценка 16 виртуальных каналов", "Азимут и угол места"],
            ["6", "Сопровождение и упаковка CAN FD", "Target State без команд управления"],
        ],
        [1.2, 7.0, 7.0],
    )


def build_guide(output: Path) -> None:
    doc = configure_document(
        "Руководство по сборке, прошивке и первичной стендовой проверке AWR2944P",
        "Д79-24В-РЛ-РП-AWR-R2",
    )
    add_heading(doc, "1. Назначение")
    add_text(doc, "Документ задаёт порядок сборки исходного кода, загрузки образа AWR2944P, применения профилей R9 и первичной проверки цифрового контура. Прошивка предназначена только для наблюдения и сопровождения одного воздушного объекта. Она выдаёт Target State и диагностические признаки, но не вычисляет упреждение, курс сближения, команды движения, команды исполнительным механизмам или внешней системе управления.")
    add_heading(doc, "1.1. Состав выпуска", 2)
    add_table(
        doc,
        ["Файл", "Назначение", "Статус"],
        [
            ["AWR2944P_OBSERVER_EVT_R2.appimage", "Неподписанный образ для GP-устройства", "Сборка PASS"],
            ["AWR2944P_OBSERVER_EVT_R2_MSS.xer5f", "Исполняемый образ R5F MSS", "Сборка PASS"],
            ["AWR2944P_OBSERVER_EVT_R2_DSS.xe66", "Исполняемый образ C66x DSS", "Сборка PASS"],
            ["EVT_R9_TRIPRF_TRACKING_CANDIDATE.cfg", "Расчётный рабочий профиль трёх PRF", "Аппаратная проверка NOT_RUN"],
            ["EVT_R9_RANGE_PHASE_CALIBRATION.cfg", "Профиль измерения смещения дальности и фаз RX", "Калибровка NOT_RUN"],
            ["QA_EVIDENCE_EVT_OBSERVER_R2.json", "Результаты сборки и цифровых проверок", "Production authority NOT_AUTHORIZED"],
        ],
        [5.6, 6.4, 3.2],
    )

    add_heading(doc, "2. Среда сборки")
    add_table(
        doc,
        ["Средство", "Версия или путь"],
        [
            ["MMWAVE-MCUPLUS-SDK", "04.07.02.01, C:\\ti\\mmwave_mcuplus_sdk_04_07_02_01"],
            ["MCU+ SDK AWR2x44P", "10.02.00.04, зависимость TI"],
            ["mmWave DFP", "02.04.18.01, зависимость TI"],
            ["SysConfig", "1.23.0, C:\\ti\\sysconfig_1.23.0"],
            ["Code Composer Studio", "20.1.0, C:\\ti\\ccs2010"],
            ["TI ARM Clang", "4.0.2 LTS"],
            ["TI C6000", "8.3.13"],
            ["UniFlash", "Версия с поддержкой AWR2944P"],
        ],
        [6.0, 9.2],
    )
    add_heading(doc, "2.1. Сборка", 2)
    add_numbered(
        doc,
        [
            "Открыть PowerShell в корне репозитория.",
            "Запустить firmware\\awr2944p_observer\\tools\\build_target.ps1.",
            "Убедиться, что этапы SysConfig, R5F compile and link и C66x compile and link завершились без ошибок.",
            "Проверить наличие файла .work\\awr2944p_observer_target\\mmw_tdm\\awr2x44P_mmw_demoTDM.appimage.",
            "Вычислить SHA-256 и сравнить с SHA256SUMS.txt выпуска R2.",
            "Не подменять неподписанный GP-образ образом high-security. Тип загрузки должен соответствовать фактическому состоянию кристалла.",
        ],
    )

    add_heading(doc, "3. Что изменено в R2")
    add_numbered(
        doc,
        [
            "Признак CONFIG_MATCH формируется только после проверки фактической конфигурации TI data path, а не устанавливается безусловно.",
            "Добавлено объединение трёх измерений радиальной скорости с периодами chirp 30, 33 и 39 мкс.",
            "Добавлена геометрия 16 виртуальных фазовых центров для четырёх RX и четырёх TX каналов платы R9.",
            "Отметки трёх подкадров объединяются в один результат. При неполном наборе прошивка не выдаёт новую достоверную отметку и переводит сопровождение в деградированный режим.",
            "Добавлены отдельные рабочий и калибровочный профили, расчётный аудит и тест диапазона скорости от -60 до +60 м/с.",
        ],
    )

    add_heading(doc, "4. Обработка сигнала")
    add_flow_diagram(doc)
    add_text(doc, "Для линейно-частотно модулированного chirp задержка отражённого сигнала преобразуется после смешения в beat-частоту. При пренебрежении доплеровской добавкой дальность оценивается по формуле:")
    add_equation(doc, "R = c f_b / (2 S),")
    add_text(doc, "где c равно скорости света, f_b равно beat-частоте, S равно наклону частоты chirp. Для профиля R9 S = 8 МГц/мкс, а расчётная beat-частота на 300 м равна 16,01 МГц.")
    add_text(doc, "Радиальная скорость в одном PRF измеряется с неоднозначностью. В R2 используются три разных предела V1, V2, V3. Алгоритм ищет значение v в интервале от -60 до +60 м/с, которое минимизирует сумму квадратов циклических невязок:")
    add_equation(doc, "v* = arg min Σ wrap(v - v_i, 2 V_i)^2.")
    add_text(doc, "Расчётный цифровой прогон с шагом 0,1 м/с не выявил ошибок разворачивания. Это не заменяет проверку реальным доплеровским имитатором или движущейся целью.")

    add_heading(doc, "5. Загрузка образа")
    add_heading(doc, "5.1. AWR2944PEVM", 2)
    add_numbered(
        doc,
        [
            "Снять питание и установить SOP в режим загрузки Flash согласно руководству TI для конкретной ревизии EVM.",
            "Подключить штатный USB интерфейс EVM и подать разрешённое питание.",
            "Открыть UniFlash, выбрать AWR2944P и определить доступный последовательный порт.",
            "Выбрать AWR2944P_OBSERVER_EVT_R2.appimage, запустить программирование и сохранить журнал.",
            "После успешной проверки снять питание, установить SOP в функциональный режим и повторно включить EVM.",
        ],
    )
    add_heading(doc, "5.2. Целевая круглая плата", 2)
    add_text(doc, "Перед программированием целевой платы требуется сверить разводку SOP, reset, UART, JTAG, питание ядра и Flash с проектом Altium и документацией TI. Нельзя переносить положения перемычек EVM на целевую плату без проверки. Первый запуск выполняют от лабораторного источника 24 В с ограничением тока и без излучения в неконтролируемое пространство.")

    add_heading(doc, "6. Загрузка профилей")
    add_numbered(
        doc,
        [
            "Подключить сервисный USB UART к CLI UART AWR2944P с общим GND и уровнем 3,3 В. Не подключать к логике 5 В.",
            "Остановить sensorStart командой sensorStop, если датчик был запущен.",
            "Для калибровки загрузить EVT_R9_RANGE_PHASE_CALIBRATION.cfg. Для рабочего прогона использовать EVT_R9_TRIPRF_TRACKING_CANDIDATE.cfg.",
            "Проверить ответы CLI на каждую строку. Ошибка синтаксиса, памяти или времени кадра запрещает переход к sensorStart.",
            "После запуска проверить CONFIG_MATCH. Если флаг отсутствует, данные не считать конфигурационно подтверждёнными.",
            "Рабочий профиль содержит единичные значения compRangeBiasAndRxChanPhase. После физической калибровки их обязательно заменить измеренными коэффициентами.",
        ],
    )

    add_heading(doc, "7. Первичная стендовая проверка")
    add_table(
        doc,
        ["Шаг", "Действие", "Ожидаемый результат", "Условие остановки"],
        [
            ["1", "Осмотр, контроль КЗ, проверка полярности", "Нет повреждений и КЗ", "Любое КЗ или несоответствие сборке"],
            ["2", "24 В при ограничении 0,3 А", "Нет резкого роста тока", "Ограничение тока, дым, запах, нагрев"],
            ["3", "Измерить RADAR_12V и 3,3 В", "В пределах проектных допусков", "Отклонение более 5 процентов"],
            ["4", "Загрузить appimage и открыть CLI", "Стабильный ответ без reset loop", "Повторные сбросы или потеря UART"],
            ["5", "Подключить CAN FD", "Кадр 0x320, 64 байта, CRC корректен", "Bus-off, ошибки CRC, неверный DLC"],
            ["6", "Загрузить рабочий профиль", "CONFIG_MATCH установлен", "Флаг не установлен или CLI сообщил ошибку"],
            ["7", "Проверить неподвижный отражатель", "Стабильная отметка с ожидаемым знаком дальности", "Скачки, насыщение, ложная отметка"],
        ],
        [1.0, 4.3, 5.3, 4.6],
    )

    add_heading(doc, "8. Интерфейс результата")
    add_text(doc, "Измерительный кадр AWR2944P передаётся по CAN FD с стандартным идентификатором 0x320, DLC 64 и BRS. Сервисный запрос от платы обработки использует 0x321. Поля кадра, счётчик последовательности, CRC32C, тайм-ауты и восстановление после bus-off заданы отдельным контрактом CAN FD. Выход содержит дальность, радиальную скорость, азимут, угол места, SNR, состояние сопровождения и диагностические признаки. Координаты или команды для управления движением не формируются.")

    add_heading(doc, "9. Результаты цифровой проверки")
    add_table(
        doc,
        ["Проверка", "Результат"],
        [
            ["Модульные и сквозные тесты CMake/CTest", "22 из 22 PASS"],
            ["Сборка R5F MSS", "PASS"],
            ["Сборка C66x DSS", "PASS"],
            ["Формирование GP appimage", "PASS"],
            ["Расчёт 300 м по полосе IF", "PASS, без физической платы"],
            ["Разворачивание скорости от -60 до +60 м/с", "PASS, цифровой прогон"],
            ["Калибровка дальности и фаз", "NOT_RUN"],
            ["Проверка угла места на краях ±20 градусов", "NOT_RUN"],
            ["Дальность 300 м при ЭПР 0,01 м2", "NOT_RUN"],
            ["Production authority", "NOT_AUTHORIZED"],
        ],
        [9.0, 6.2],
    )

    add_heading(doc, "10. Ссылочные документы")
    add_numbered(
        doc,
        [
            "Texas Instruments, MMWAVE-MCUPLUS-SDK 04.07.02.01 User Guide.",
            "Texas Instruments, AWR2944 and AWR2944P Evaluation Module User Guide, SPRUJ22C.",
            "Texas Instruments, AWR2944P product data and technical documentation.",
            "Контракт CAN FD AWR2944P STM32, версия 1.1.0 EVT R1.",
            "Методика настройки, проверки и калибровки AWR2944P, версия 0.2.0 EVT R2.",
        ],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


def build_method(output: Path) -> None:
    doc = configure_document(
        "Методика настройки, проверки и калибровки радиолокационного канала AWR2944P",
        "Д79-24В-РЛ-ПМ-КАЛ-R2",
    )
    add_heading(doc, "1. Назначение и границы")
    add_text(doc, "Методика устанавливает порядок настройки, проверки и калибровки круглой платы D79 R9 с AWR2944P и антенной системой из четырёх RX и четырёх TX каналов. Каждый физический RF-канал питает пассивную восьмиэлементную печатную подрешётку. Для цифровой угловой обработки процессор видит 16 виртуальных фазовых центров, а не 64 независимых канала.")
    add_text(doc, "Методика относится только к обнаружению и сопровождению воздушных объектов. Выходом является Target State. Расчёт упреждения, курса сближения, перехвата и команд управления исключён.")
    add_heading(doc, "1.1. Что можно проверить без физической платы", 2)
    add_numbered(
        doc,
        [
            "Сборку исходного кода R5F и C66x и формирование appimage.",
            "Формат CAN FD, CRC32C, счётчики, состояния сопровождения и деградацию.",
            "Расчёт профиля по beat-частоте, частоте дискретизации и длительности ADC.",
            "Разворачивание радиальной скорости по трём PRF в диапазоне от -60 до +60 м/с.",
            "Проверку флага CONFIG_MATCH по структуре текущей конфигурации TI data path.",
        ],
    )
    add_text(doc, "Без платы нельзя подтвердить абсолютную дальность, фазовые коэффициенты, угловую точность, усиление антенны, дальность 300 м, ЭПР 0,01 м2, тепловой режим, ЭМС и отсутствие паразитных откликов.")

    add_heading(doc, "2. Средства измерений и оснащение")
    add_table(
        doc,
        ["Средство", "Минимальное требование", "Назначение"],
        [
            ["Лабораторный источник", "0-30 В, не менее 5 А, ограничение тока", "Первое включение 24 В"],
            ["Мультиметр", "Погрешность не хуже 0,5 процента", "Питание и сопротивления"],
            ["Осциллограф", "Не менее 100 МГц, 4 канала", "Пульсации, reset, тактирование"],
            ["USB CAN FD", "500 кбит/с arbitration, 2,5 Мбит/с data, BRS", "Приём 0x320 и сервис 0x321"],
            ["USB UART 3,3 В", "Отдельные TX, RX, GND", "CLI и журнал загрузки профиля"],
            ["Поворотный стол", "Отсчёт не хуже 0,1 градуса", "Азимут и угол места"],
            ["Лазерный дальномер", "Погрешность лучше требуемой погрешности радара", "Опорная дальность"],
            ["Уголковый отражатель", "Известные размеры и расчётная ЭПР", "Дальность и фаза"],
            ["Поглощающий материал", "Для 76-81 ГГц", "Подавление многолучёвости"],
            ["Доплеровский имитатор или линейная тележка", "Скорость с независимым измерением", "Проверка скорости"],
            ["Тепловизор или термопары", "Не менее 4 точек контроля", "Тепловой режим"],
            ["Средство 76-81 ГГц", "Анализатор, измеритель мощности или аттестованный стенд", "Частота, спектр, EIRP"],
        ],
        [4.0, 5.6, 5.6],
    )
    add_text(doc, "Серийные номера средств, дата поверки или калибровки и условия испытаний заносятся в протокол. Если требуемое средство отсутствует, соответствующий пункт отмечают NOT_RUN, а не PASS.")

    add_heading(doc, "3. Условия и безопасность")
    add_numbered(
        doc,
        [
            "Работы в диапазоне 76-81 ГГц проводить на выделенном стенде с ограничением зоны излучения и с учётом местных требований к радиоизлучению.",
            "Первое включение выполнять без антенны, направленной на людей, отражающие металлоконструкции или открытое пространство.",
            "До подачи питания проверить полярность 24 В, целостность GND, отсутствие КЗ и правильность сборки.",
            "При дыме, запахе, нештатном нагреве, повторных сбросах, ограничении тока, перенапряжении или bus-off немедленно снять питание.",
            "Калибровку проводить после тепловой стабилизации. Температуру платы и воздуха фиксировать в протоколе.",
        ],
    )

    add_heading(doc, "4. Предварительная проверка")
    add_table(
        doc,
        ["Параметр", "Метод", "Критерий перехода"],
        [
            ["24V_IN к GND", "Омметр при снятом питании", "Нет короткого замыкания"],
            ["RADAR_12V", "Мультиметр и осциллограф", "11,4-12,6 В, без срывов"],
            ["3,3 В", "Мультиметр и осциллограф", "3,135-3,465 В, без срывов"],
            ["Reset", "Осциллограф", "Нет повторяющихся нештатных импульсов"],
            ["Температура", "Тепловизор или термопары", "Нет локального быстрого разогрева"],
            ["CLI UART", "Терминал", "Ответ устойчив, ошибок загрузки нет"],
            ["CAN FD", "USB CAN FD", "0x320, DLC 64, CRC корректен"],
        ],
        [4.0, 5.6, 5.6],
    )

    add_heading(doc, "5. Настройка профиля")
    add_heading(doc, "5.1. Расчёт дальности", 2)
    add_text(doc, "В FMCW-сигнале задержка τ = 2R/c превращается после смешения в beat-частоту f_b = Sτ. Базовая оценка дальности:")
    add_equation(doc, "R = c f_b / (2 S).")
    add_text(doc, "Для рабочего профиля S = 8 МГц/мкс, 800 отсчётов при 40 Мвыб/с дают 20 мкс выборки и полосу chirp около 160 МГц. Расчётное разрешение c/(2B) равно 0,937 м. Beat-частота на 300 м равна 16,01 МГц, а на 350 м 18,68 МГц. Эти значения являются расчётными и требуют проверки аналоговой полосы, запасов и паразитных откликов на плате.")

    add_heading(doc, "5.2. Три PRF и скорость", 2)
    add_text(doc, "Периоды chirp 30, 33 и 39 мкс дают разные интервалы однозначной радиальной скорости. Для каждого подкадра измеряется свёрнутое значение v_i. Истинное значение выбирают из интервала от -60 до +60 м/с по минимуму циклической невязки:")
    add_equation(doc, "v* = arg min Σ wrap(v - v_i, 2 V_i)^2, |v| ≤ 60 м/с.")
    add_text(doc, "Программный порог максимальной невязки установлен 1,5 м/с. При превышении порога измерение скорости отвергают. На стенде обязательно проверить оба знака скорости и точки не только в центре, но и рядом с границами неоднозначности каждого PRF.")

    add_heading(doc, "5.3. Угловая оценка", 2)
    add_text(doc, "Для пары фазовых центров с расстоянием d фазовая разность в плоской волне связана с углом θ:")
    add_equation(doc, "Δφ = 2π d sin(θ) / λ,    θ = asin(λ Δφ / (2π d)).")
    add_text(doc, "Фактическая оценка использует все 16 виртуальных каналов и заданную antGeometryCfg. Печатные восьмиэлементные подрешётки формируют диаграмму каждого RF-канала, но не создают дополнительные независимые цифровые каналы. Поэтому точность угла нельзя выводить только из числа 64 печатных элементов. Требуются фазовая калибровка, измеренная диаграмма и проверка во всём секторе.")

    add_heading(doc, "6. Калибровка дальности и фаз RX")
    add_heading(doc, "6.1. Подготовка", 2)
    add_numbered(
        doc,
        [
            "Установить плату жёстко, обозначить механическую ось и нулевые плоскости азимута и угла места.",
            "Разместить сильный точечный отражатель на оси. Начальная дистанция профиля равна 1,5 м и должна быть измерена от согласованной механической базы, а не от края платы.",
            "Убрать посторонние отражатели из первой зоны Френеля или закрыть их поглотителем.",
            "Загрузить EVT_R9_RANGE_PHASE_CALIBRATION.cfg и сохранить полный CLI-журнал.",
            "Получить строку измеренных compRangeBiasAndRxChanPhase. Если измерение нестабильно, не усреднять вручную случайные выбросы, а устранить многолучёвость и насыщение.",
        ],
    )
    add_heading(doc, "6.2. Смещение дальности", 2)
    add_text(doc, "Для серии N измерений смещение определяют устойчивой оценкой:")
    add_equation(doc, "b_R = median(R_meas,k - R_ref,k),    R_corr = R_meas - b_R.")
    add_text(doc, "Проверку повторяют минимум на трёх расстояниях, включая рабочую ближнюю и среднюю зону. Одно значение на 1,5 м не подтверждает линейность шкалы. В протокол заносят исходные данные, медиану, максимальное отклонение и температуру.")
    add_heading(doc, "6.3. Комплексные коэффициенты каналов", 2)
    add_text(doc, "Пусть измерение i-го виртуального канала z_i = A_i exp(jφ_i), а опорный канал имеет z_ref. Коэффициент компенсации можно представить как:")
    add_equation(doc, "c_i = (A_ref / A_i) exp[-j(φ_i - φ_ref)].")
    add_text(doc, "Фазу усредняют как аргумент суммы комплексных единичных векторов, а не как обычное среднее градусов. Коэффициенты записывают только после проверки повторяемости при нескольких перезапусках. Измеренные значения заменяют единичный placeholder в рабочем cfg. Сразу после замены повторяют осевой тест и сохраняют новую контрольную сумму профиля.")

    add_heading(doc, "7. Калибровка углов")
    add_numbered(
        doc,
        [
            "Установить отражатель на известной дальности в дальней зоне или на расстоянии, обоснованном для выбранной апертуры и метода измерения.",
            "Снять сетку азимута при 0 градусов угла места и сетку угла места при 0 градусов азимута.",
            "Обязательные точки по углу места: -20, -15, -10, -5, 0, +5, +10, +15 и +20 градусов.",
            "Для каждой точки записать не менее 100 кадров после стабилизации, медиану угла, 95-процентный интервал, SNR и долю пропусков.",
            "Определить постоянное смещение нуля и проверить знак осей. Не применять полиномиальную коррекцию, пока её улучшение не подтверждено независимым набором точек.",
            "Повторить измерения после снятия и повторной установки платы. Разность характеризует ошибку механической базы.",
        ],
    )
    add_text(doc, "Ширина диаграммы не равна погрешности угла напрямую. Фазовая оценка может быть точнее ширины луча при достаточном SNR, но смещения, многолучёвость и неоднозначность геометрии должны быть измерены. Расчётная диаграмма массива не заменяет полно-волновое моделирование и измерение образца.")

    add_heading(doc, "8. Проверка скорости")
    add_table(
        doc,
        ["Режим", "Точки", "Оцениваемые параметры"],
        [
            ["Нулевая скорость", "Неподвижный отражатель", "Смещение нуля и шум скорости"],
            ["Положительный знак", "+5, +15, +30, +36,1, +45, +52,8, +58 м/с", "Ошибка, невязка трёх PRF, пропуски"],
            ["Отрицательный знак", "-5, -15, -30, -36,1, -45, -52,8, -58 м/с", "Знак, ошибка, невязка, пропуски"],
            ["Границы PRF", "Окрестности ±6,12, ±7,23 и ±7,96 м/с", "Отсутствие скачка алиаса"],
        ],
        [4.0, 6.4, 4.8],
    )
    add_text(doc, "Скорости 36,1 и 52,8 м/с соответствуют 130 и 190 км/ч. Опорная скорость должна измеряться независимо. Визуальная оценка по приводу или команде имитатора без обратной связи не считается эталоном.")

    add_heading(doc, "9. Проверка дальности и чувствительности")
    add_text(doc, "Для моностатического радара принятая мощность в идеализированной модели определяется выражением:")
    add_equation(doc, "P_r = P_t G_t G_r λ² σ / [(4π)³ R⁴ L].")
    add_text(doc, "Здесь σ равно ЭПР, L объединяет потери. Из формулы следует зависимость R в четвёртой степени, поэтому расчётная дальность чувствительна к усилению антенны, потерям и порогу обнаружения. Утверждение 300 м при ЭПР 0,01 м2 принимается только после измерения на аттестованном диапазоне или эквивалентном калиброванном стенде.")
    add_numbered(
        doc,
        [
            "Проверить ложные отметки без цели и сформировать карту стационарного фона.",
            "Проверить цель известной ЭПР на нескольких дальностях и углах.",
            "На углах места -20 и +20 градусов отдельно проверить SNR и вероятность обнаружения.",
            "Повторить на требуемых радиальных скоростях или с доплеровским имитатором.",
            "Не экстраполировать дальность только по одной ближней точке, если динамический диапазон и паразитные отклики не подтверждены.",
        ],
    )

    add_heading(doc, "10. Совмещение с IMU")
    add_text(doc, "Радар выдаёт направление в собственной системе координат. Для перевода в систему носителя требуется измеренная матрица установки R_b^r. Направление в системе носителя получают как u_b = R_b^r u_r. Для перевода в навигационную систему используют ориентацию носителя R_n^b: u_n = R_n^b u_b.")
    add_text(doc, "IMU имеет смещения и дрейф. Перед испытанием определяют нулевые смещения гироскопов и акселерометров на неподвижном стенде, проверяют знак осей и временное совмещение с радаром. GNSS может использоваться как внешний источник времени и координат, но потеря или недостоверность GNSS не должна превращать угловую отметку радара в подтверждённую глобальную координату.")
    add_equation(doc, "σ²_total ≈ σ²_radar + σ²_mount + σ²_IMU + σ²_time,")
    add_text(doc, "где составляющие определяются экспериментально. До измерения этих величин точность глобального направления не заявляется.")

    add_heading(doc, "11. Температурная проверка")
    add_numbered(
        doc,
        [
            "Провести базовую калибровку при комнатной температуре после тепловой стабилизации.",
            "Повторить контроль дальности, нулевого угла и межканальной фазы в нижней, средней и верхней точках согласованного диапазона температур.",
            "Регистрировать температуру AWR2944P, преобразователя 24 В, RF-зоны и воздуха.",
            "Если дрейф превышает установленный бюджет ошибки, ввести температурную таблицу только после повторяемых измерений на нескольких экземплярах.",
        ],
    )

    add_heading(doc, "12. Критерии остановки")
    add_table(
        doc,
        ["Событие", "Действие"],
        [
            ["Ток достиг ограничения источника", "Немедленно снять 24 В и искать КЗ или ошибку запуска"],
            ["RADAR_12V или 3,3 В вне допуска", "Не запускать RF и не прошивать"],
            ["Быстрый локальный нагрев", "Снять питание, сохранить тепловой кадр"],
            ["Повторные reset или зависание CLI", "Остановить sensorStart, проверить питание и тактирование"],
            ["CONFIG_MATCH не установлен", "Не считать Target State подтверждённым"],
            ["CALIBRATION_VALID не установлен", "Не принимать угловую точность"],
            ["Невязка трёх PRF более 1,5 м/с", "Отвергнуть измерение скорости"],
            ["CAN bus-off или ошибки CRC", "Остановить прогон, проверить линию и терминацию"],
            ["Неконтролируемое RF-излучение", "Немедленно остановить датчик"],
        ],
        [7.6, 7.6],
    )

    add_heading(doc, "13. Формы протоколов")
    add_heading(doc, "13.1. Идентификация", 2)
    add_table(
        doc,
        ["Поле", "Значение"],
        [
            ["Серийный номер платы", "____________________________"],
            ["Ревизия PCB и PCBA", "____________________________"],
            ["SHA-256 appimage", "____________________________"],
            ["SHA-256 рабочего cfg", "____________________________"],
            ["Дата, оператор, место", "____________________________"],
            ["Температура и влажность", "____________________________"],
        ],
        [7.6, 7.6],
    )
    add_heading(doc, "13.2. Результаты калибровки", 2)
    add_table(
        doc,
        ["Параметр", "Результат", "Единица", "PASS/FAIL/NOT_RUN"],
        [
            ["Смещение дальности b_R", "________", "м", "________"],
            ["Максимальная межканальная фазовая невязка", "________", "градус", "________"],
            ["Смещение азимута", "________", "градус", "________"],
            ["Смещение угла места", "________", "градус", "________"],
            ["Ошибка скорости при 36,1 м/с", "________", "м/с", "________"],
            ["Ошибка скорости при 52,8 м/с", "________", "м/с", "________"],
            ["SNR на 300 м, ЭПР 0,01 м2, угол места 0", "________", "дБ", "________"],
            ["SNR на 300 м, ЭПР 0,01 м2, угол места ±20", "________", "дБ", "________"],
        ],
        [6.4, 3.2, 2.4, 3.2],
    )

    add_heading(doc, "14. Решение по результатам")
    add_text(doc, "PASS по цифровым тестам не означает допуска к производству. После выполнения физических проверок комиссия фиксирует отдельные решения по программному выпуску, калибровке экземпляра, работоспособности EVT и готовности к следующей ревизии. До закрытия полно-волновой проверки антенны, измерений дальности и углов, тепловых и ЭМС испытаний сохраняется Production authority = NOT_AUTHORIZED.")

    add_heading(doc, "15. Ссылочные документы")
    add_numbered(
        doc,
        [
            "Texas Instruments, AWR2944P technical documentation.",
            "Texas Instruments, MMWAVE-MCUPLUS-SDK User Guide 04.07.02.01.",
            "Texas Instruments, mmWave radar sensing: FMCW processing fundamentals.",
            "Рабочий профиль EVT_R9_TRIPRF_TRACKING_CANDIDATE.cfg.",
            "Калибровочный профиль EVT_R9_RANGE_PHASE_CALIBRATION.cfg.",
            "Расчётный аудит awr2944p_profile_audit_r2.json.",
        ],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    build_guide(
        args.output_dir
        / "Руководство_по_сборке_прошивке_и_стендовой_проверке_AWR2944P_v0.2.0_EVT_R2.docx"
    )
    build_method(
        args.output_dir
        / "Методика_настройки_проверки_и_калибровки_AWR2944P_v0.2.0_EVT_R2.docx"
    )
    for path in args.output_dir.glob("*.docx"):
        payload, _ = transform_docx(path.read_bytes(), version="0.2.0-EVT-R2")
        path.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
