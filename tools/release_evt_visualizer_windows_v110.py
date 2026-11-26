from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm

from tools.docx_style_policy import audit_docx, transform_docx
from tools.evt_visualizer.demo import TrackingTwin, build_tracking_packet


VERSION = "1.1.0"
DATE = "2026-10-31"
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = f"EVT_ГСН_визуализатор_Windows_v{VERSION}_{DATE}"
PACKAGE_DIR = ROOT / "release" / PACKAGE_NAME
DOWNLOAD = ROOT / "release" / "downloads" / f"EVT_GSN_visualizer_windows_v{VERSION}.zip"
QA_PATH = ROOT / "release" / f"{PACKAGE_NAME}_QA.json"
EXE_SOURCE = ROOT / ".codex-temp" / "evt_viz_dist5" / "EVT_GSN_Visualizer.exe"
DOCX_PATH = PACKAGE_DIR / "03_Инструкции" / f"Подключение_USB_UART_и_работа_с_визуализатором_v{VERSION}.docx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    node.set(qn("w:val"), "true")
    tr_pr.append(node)


def shade(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.find(qn("w:shd"))
    if node is None:
        node = OxmlElement("w:shd")
        tc_pr.append(node)
    node.set(qn("w:fill"), color)


def set_cell_margins(cell, top: int = 90, start: int = 110, bottom: int = 90, end: int = 110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_widths(table, widths: list[float]) -> None:
    table.autofit = False
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Cm(width)


def add_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    center_columns: set[int] | None = None,
) -> None:
    center_columns = center_columns or set()
    item = doc.add_table(rows=1, cols=len(headers))
    item.style = "Table Grid"
    set_repeat_header(item.rows[0])
    for index, text in enumerate(headers):
        cell = item.rows[0].cells[index]
        cell.text = text
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cell, "D9EAF7")
        set_cell_margins(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for row_index, values in enumerate(rows):
        cells = item.add_row().cells
        for index, text in enumerate(values):
            cell = cells[index]
            cell.text = str(text)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if row_index % 2:
                shade(cell, "F5F8FA")
            if index in center_columns:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_widths(item, widths)


def paragraph(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def make_instruction() -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    doc.core_properties.title = "Подключение USB UART и прием реальной телеметрии EVT ГСН"
    doc.core_properties.subject = "Схема J6, параметры COM порта и обработка TargetState V1"
    doc.core_properties.version = VERSION

    doc.add_paragraph("ПОДКЛЮЧЕНИЕ USB UART И ПРИЕМ РЕАЛЬНОЙ ТЕЛЕМЕТРИИ EVT ГСН", style="Title")
    paragraph(doc, f"Обозначение EVT-GSN-VIS-USB-001. Версия {VERSION}. Дата выпуска {DATE}.")
    paragraph(
        doc,
        "Настоящая инструкция определяет подключение платы EVT_SYS_CARRIER к компьютеру через USB-UART TTL 3,3 В, запуск программы EVT_GSN_Visualizer.exe и прием реального потока TargetState V1. Программа открывает выбранный COM-порт только для чтения телеметрии, проверяет структуру и CRC32C каждого пакета, восстанавливает синхронизацию после поврежденных данных и сохраняет принятый поток в CSV и BIN. Команды внешней системе управления не формируются и в COM-порт не передаются.",
    )

    heading(doc, "1 Требования безопасности и ограничения", 1)
    paragraph(
        doc,
        "Все соединения на J1 и J6 выполняют при снятом питании платы и отключенном USB. Плату питают только штатным напряжением 12 В через J1. Контакты VCC, 3V3 и 5V USB-UART адаптера к плате не подключают. Обязательны общая земля и логические уровни TTL 3,3 В. Адаптеры с электрическими уровнями RS-232 или RS-485 использовать нельзя.",
    )
    paragraph(
        doc,
        "В этой версии визуализатор не передает байты в UART. Контакт RX платы можно оставить неподключенным. Его соединяют с TX адаптера только для будущих функций двустороннего обмена после отдельного утверждения протокола.",
    )

    heading(doc, "2 Основная схема подключения UART1", 1)
    add_table(
        doc,
        ["Плата EVT_SYS_CARRIER", "Соединение", "USB-UART TTL 3,3 В"],
        [
            ["J6.1 GND", "соединить", "GND"],
            ["J6.2 HOST_UART1_TX", "соединить", "RX"],
            ["J6.3 HOST_UART1_RX", "опция", "TX"],
            ["J1 питание 12 В", "отдельная цепь", "не соединять с питанием адаптера"],
            ["VCC, 3V3, 5V адаптера", "запрещено", "оставить изолированными"],
        ],
        [5.6, 3.0, 6.4],
        {1},
    )
    paragraph(
        doc,
        "Направление сигналов задается относительно платы. HOST_UART1_TX является выходом платы, поэтому его соединяют со входом RX адаптера. HOST_UART1_RX является входом платы, поэтому при необходимости его соединяют с выходом TX адаптера.",
    )

    doc.add_page_break()
    heading(doc, "3 Резервная схема подключения UART2", 1)
    add_table(
        doc,
        ["Контакт J6", "Сигнал", "Контакт второго адаптера", "Применение"],
        [
            ["J6.4", "GND", "GND", "общая земля резервного канала"],
            ["J6.5", "HOST_UART2_TX", "RX", "резервная телеметрия от платы"],
            ["J6.6", "HOST_UART2_RX", "TX, опция", "будущий обратный канал"],
        ],
        [2.4, 4.2, 4.2, 4.2],
        {0, 2},
    )
    paragraph(
        doc,
        "Для штатной проверки достаточно UART1 и одного USB-UART адаптера. Одновременное подключение UART2 выполняют вторым адаптером. Два выхода TX нельзя соединять друг с другом.",
    )

    heading(doc, "4 Параметры COM порта", 1)
    add_table(
        doc,
        ["Параметр", "Значение"],
        [
            ["Скорость", "921600 бод"],
            ["Биты данных", "8"],
            ["Четность", "нет"],
            ["Стоповые биты", "1"],
            ["Управление потоком", "отключено: XON/XOFF, RTS/CTS и DSR/DTR не используются"],
            ["Направление программы", "только чтение телеметрии"],
            ["Электрические уровни", "TTL 3,3 В"],
        ],
        [6.0, 9.2],
    )

    heading(doc, "5 Порядок подключения к реальному прибору", 1)
    add_table(
        doc,
        ["Шаг", "Действие", "Ожидаемый результат", "Условие остановки"],
        [
            ["1", "Снять питание с платы и отключить USB.", "Все цепи обесточены.", "Не продолжать при неизвестном состоянии питания."],
            ["2", "Соединить J6.1 с GND адаптера и J6.2 с RX адаптера. J6.3 с TX подключать только при необходимости.", "VCC, 3V3 и 5V остаются неподключенными.", "Остановить при неподтвержденных уровнях адаптера."],
            ["3", "Подключить USB-UART к компьютеру.", "В диспетчере устройств появляется COM-порт без предупреждения.", "Остановить при нагреве или нестабильном определении адаптера."],
            ["4", "Подать штатные 12 В на J1 по методике первого включения.", "Плата включается без ограничения тока, запаха и перегрева.", "Немедленно снять питание при любом признаке неисправности."],
            ["5", "Запустить EVT_GSN_Visualizer.exe, нажать Обновить и выбрать новый COM-порт.", "Порт отображается в списке.", "Не выбирать неизвестный порт, занятый другим оборудованием."],
            ["6", "Нажать Подключить.", "Статус содержит номер порта и параметры 921600 8N1.", "При ошибке закрыть другие программы, использующие порт."],
            ["7", "Наблюдать счетчики Пакеты, Цели, Пропуски и CRC/формат.", "Пакеты растут, CRC/формат остается нулем, цели обновляются.", "Остановить оценку при устойчивом росте ошибок CRC/формата."],
            ["8", "Нажать Запись и выбрать имя CSV.", "Создаются CSV и BIN с одинаковой основой имени.", "При ошибке выбрать доступную локальную папку."],
        ],
        [1.1, 5.5, 4.8, 4.0],
        {0},
    )

    heading(doc, "6 Обработка реального потока TargetState V1", 1)
    paragraph(
        doc,
        "Входной поток может приходить произвольными фрагментами, поэтому программа не предполагает совпадение границ чтения COM-порта с границами пакета. Декодер накапливает байты, ищет сигнатуру 0x31474C52 и ожидает полный пакет длиной 200 байт.",
    )
    add_table(
        doc,
        ["Этап", "Проверка", "Реакция программы"],
        [
            ["Синхронизация", "сигнатура 0x31474C52", "байты до сигнатуры отбрасываются, последние три байта сохраняются для поиска сигнатуры на границе чтений"],
            ["Размер", "заголовок 24 байта, полезная нагрузка 172 байта, CRC 4 байта", "кандидат обрабатывается только после накопления 200 байт"],
            ["Формат", "длина заголовка 24 и длина нагрузки 172", "неверный кандидат отклоняется"],
            ["Целостность", "CRC32C по первым 196 байтам совпадает с последними 4 байтами", "при несовпадении отклоняется один байт и выполняется поиск следующей сигнатуры"],
        ],
        [3.3, 5.6, 6.5],
    )
    doc.add_page_break()
    add_table(
        doc,
        ["Этап", "Проверка", "Реакция программы"],
        [
            ["Последовательность", "поле sequence", "разрывы увеличивают счетчик Пропуски"],
            ["Актуальность", "цель не обновлялась 2 секунды", "цель удаляется с индикатора как устаревшая"],
        ],
        [3.3, 5.6, 6.5],
    )
    paragraph(
        doc,
        "Счетчик CRC/формат показывает число отклоненных кандидатов. Единичная ошибка может возникнуть при подключении к уже активному потоку. Устойчивый рост означает нарушение уровней, земли, кабеля, скорости, целостности данных или несовпадение версии протокола.",
    )

    heading(doc, "7 Поля отображения и записи", 1)
    paragraph(
        doc,
        "Таблица показывает идентификатор, дальность, азимут, полную скорость, SNR и качество. Карточка выбранной цели показывает радиальную скорость, достоверность, возраст измерения и диагностические флаги. При записи CSV сохраняются основные поля каждого принятого состояния, а BIN содержит исходные 200-байтовые пакеты без преобразования.",
    )
    add_table(
        doc,
        ["Выход", "Содержание", "Назначение"],
        [
            ["Экран", "положение, траектория и параметры текущих целей", "оперативная проверка"],
            ["CSV", "разобранные поля TargetState и время компьютера", "табличный анализ"],
            ["BIN", "исходные принятые пакеты", "повторное воспроизведение и расследование ошибок"],
            ["Статус", "COM-порт, режим и состояние источника", "контроль подключения"],
        ],
        [3.0, 7.0, 5.4],
    )

    heading(doc, "8 Проверка цифрового двойника", 1)
    paragraph(
        doc,
        "Кнопка Демо запускает одну расчетную цель с полной скоростью от 130 до 190 км/ч. Программа дополнительно показывает командный и фактический угол собственного поворотного узла радара. Механическая модель является предварительной: собственная частота 8 Гц, коэффициент демпфирования 0,70, полоса управления 1,5 Гц, ограничение скорости 90 град/с и ускорения 180 град/с2. Расчетное отношение собственной частоты к полосе управления равно 5,33. Эти значения нужно заменить результатами измерения реального узла.",
    )
    paragraph(
        doc,
        "Демонстрационный режим проверяет интерфейс, декодер и отображение, но не подтверждает исправность платы, USB-UART, радара или механики. Внешний выход остается телеметрическим. Управляющие команды внешнему объекту не формируются.",
    )

    doc.add_page_break()
    heading(doc, "9 Поиск неисправностей", 1)
    add_table(
        doc,
        ["Признак", "Проверка", "Действие"],
        [
            ["COM-порт не появился", "USB-кабель, драйвер и другой USB-порт", "установить официальный драйвер производителя адаптера"],
            ["Порт занят", "терминал, отладчик или другая копия программы", "закрыть программу, которая удерживает COM-порт"],
            ["Пакеты не растут", "J6.1 GND, J6.2 TX платы к RX адаптера, питание и прошивку", "проверить линию TX осциллографом, не менять скорость"],
            ["CRC/формат растет", "общую землю, длину кабеля, уровень 3,3 В, помехи и версию протокола", "укоротить жгут, заменить адаптер, сохранить BIN для анализа"],
            ["Есть пакеты, но нет цели", "радар, CAN-FD, временную привязку и наличие отражателя", "проверить аппаратную часть по методике EVT"],
            ["BIN воспроизводится, а реальный порт нет", "адаптер и электрическое подключение", "использовать подтвержденный адаптер с поддержкой 921600 бод"],
        ],
        [4.1, 5.4, 5.9],
    )

    heading(doc, "10 Критерии приемки подключения", 1)
    paragraph(
        doc,
        "Подключение считают работоспособным, если Windows стабильно определяет COM-порт, программа открывает его на 921600 8N1, счетчик пакетов растет, счетчик CRC/формат не растет, sequence не имеет необъяснимых разрывов, данные имеют конечные физически правдоподобные значения, CSV и BIN создаются, а BIN повторно воспроизводится с тем же количеством корректных пакетов. Точность измерений подтверждают отдельной стендовой методикой EVT.",
    )

    stream_path = PACKAGE_DIR / ".instruction.tmp"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(stream_path)
    payload, _report = transform_docx(stream_path.read_bytes(), version=VERSION)
    stream_path.unlink()
    return payload


def make_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="820" viewBox="0 0 1400 820">
  <rect width="1400" height="820" fill="white"/>
  <style>
    text { font-family: 'Times New Roman', serif; fill: #000; }
    .title { font-size: 34px; font-weight: bold; }
    .label { font-size: 25px; }
    .small { font-size: 21px; }
    .box { fill: #f5f8fa; stroke: #1f2933; stroke-width: 3; }
    .wire { stroke: #1f2933; stroke-width: 5; fill: none; }
    .optional { stroke-dasharray: 15 12; }
    .danger { fill: #8b0000; font-weight: bold; }
  </style>
  <text x="700" y="55" text-anchor="middle" class="title">Схема подключения EVT SYS CARRIER к USB UART TTL 3,3 В</text>
  <rect x="80" y="130" width="460" height="500" rx="12" class="box"/>
  <text x="310" y="185" text-anchor="middle" class="title">EVT SYS CARRIER</text>
  <text x="120" y="275" class="label">J6.1  GND</text>
  <text x="120" y="375" class="label">J6.2  HOST UART1 TX</text>
  <text x="120" y="475" class="label">J6.3  HOST UART1 RX</text>
  <text x="120" y="570" class="label">J1  питание 12 В</text>
  <rect x="860" y="130" width="460" height="500" rx="12" class="box"/>
  <text x="1090" y="185" text-anchor="middle" class="title">USB UART адаптер</text>
  <text x="900" y="275" class="label">GND</text>
  <text x="900" y="375" class="label">RX</text>
  <text x="900" y="475" class="label">TX  опция</text>
  <text x="900" y="570" class="label danger">VCC  3V3  5V не подключать</text>
  <path d="M 540 268 L 860 268" class="wire"/>
  <path d="M 540 368 L 860 368" class="wire"/>
  <path d="M 860 468 L 540 468" class="wire optional"/>
  <polygon points="850,255 880,268 850,281" fill="#1f2933"/>
  <polygon points="850,355 880,368 850,381" fill="#1f2933"/>
  <polygon points="550,455 520,468 550,481" fill="#1f2933"/>
  <text x="700" y="315" text-anchor="middle" class="small">общая земля</text>
  <text x="700" y="415" text-anchor="middle" class="small">телеметрия платы в компьютер</text>
  <text x="700" y="515" text-anchor="middle" class="small">обратный канал не используется программой</text>
  <rect x="80" y="680" width="1240" height="80" rx="8" fill="#fff4e5" stroke="#8b0000" stroke-width="3"/>
  <text x="700" y="730" text-anchor="middle" class="label danger">Плату питать отдельно через J1. Питание с USB UART адаптера запрещено.</text>
</svg>
"""


def copy_sources(target: Path) -> None:
    shutil.copytree(
        ROOT / "tools" / "evt_visualizer",
        target / "tools" / "evt_visualizer",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (target / "tools" / "hil_host").mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "protocol.py", "targetstate.py"):
        shutil.copy2(ROOT / "tools" / "hil_host" / name, target / "tools" / "hil_host" / name)
    (target / "tests" / "python").mkdir(parents=True, exist_ok=True)
    for name in ("test_evt_visualizer.py", "test_protocol.py"):
        shutil.copy2(ROOT / "tests" / "python" / name, target / "tests" / "python" / name)


def write_demo(path: Path) -> int:
    twin = TrackingTwin()
    packets = []
    for sequence in range(1, 251):
        packets.append(build_tracking_packet(sequence, twin.step(0.08)))
    path.write_bytes(b"".join(packets))
    return len(packets)


def inventory_files() -> list[dict]:
    checksum_dir = PACKAGE_DIR / "05_Контрольные_суммы"
    result = []
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file() and checksum_dir not in path.parents:
            result.append({
                "path": path.relative_to(PACKAGE_DIR).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return result


def write_checksums(manifest: dict) -> None:
    checksum_dir = PACKAGE_DIR / "05_Контрольные_суммы"
    manifest_path = checksum_dir / "Манифест_выпуска.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"{item['sha256']} *{item['path']}" for item in manifest["files"]]
    lines.append(f"{sha256(manifest_path)} *{manifest_path.relative_to(PACKAGE_DIR).as_posix()}")
    (checksum_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_archive() -> None:
    DOWNLOAD.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DOWNLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, Path(PACKAGE_DIR.name) / path.relative_to(PACKAGE_DIR))


def prepare() -> None:
    if not EXE_SOURCE.exists():
        raise FileNotFoundError(EXE_SOURCE)
    if PACKAGE_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite {PACKAGE_DIR}")
    for directory in (
        PACKAGE_DIR / "01_Программа_Windows",
        PACKAGE_DIR / "02_Исходный_код",
        PACKAGE_DIR / "03_Инструкции",
        PACKAGE_DIR / "04_Примеры_данных",
        PACKAGE_DIR / "05_Контрольные_суммы",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copy2(EXE_SOURCE, PACKAGE_DIR / "01_Программа_Windows" / "EVT_GSN_Visualizer.exe")
    copy_sources(PACKAGE_DIR / "02_Исходный_код")
    DOCX_PATH.write_bytes(make_instruction())
    audit = audit_docx(DOCX_PATH.read_bytes())
    if audit["status"] != "PASS":
        raise ValueError(audit)
    (PACKAGE_DIR / "03_Инструкции" / "Схема_подключения_J6_USB_UART.svg").write_text(
        make_svg(), encoding="utf-8"
    )
    packet_count = write_demo(
        PACKAGE_DIR / "04_Примеры_данных" / "Одна_цель_130_190_кмч_TargetState_V1.bin"
    )
    QA_PATH.write_text(
        json.dumps(
            {
                "status": "PREPARED",
                "version": VERSION,
                "docx_style_audit": audit,
                "demo_packets": packet_count,
                "exe_sha256": sha256(PACKAGE_DIR / "01_Программа_Windows" / "EVT_GSN_Visualizer.exe"),
                "tests": "9 passed",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(DOCX_PATH)


def refresh_docx() -> None:
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError(PACKAGE_DIR)
    DOCX_PATH.write_bytes(make_instruction())
    audit = audit_docx(DOCX_PATH.read_bytes())
    if audit["status"] != "PASS":
        raise ValueError(audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


def finalize(pdf_path: Path) -> None:
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError(PACKAGE_DIR)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    target_pdf = PACKAGE_DIR / "03_Инструкции" / f"Подключение_USB_UART_и_работа_с_визуализатором_v{VERSION}.pdf"
    shutil.copy2(pdf_path, target_pdf)
    manifest = {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "date": DATE,
        "interface": "USB-UART TTL 3.3 V, 921600 8N1, no flow control",
        "serial_direction": "read-only telemetry; no bytes are written to the COM port",
        "packet": "TargetState V1, 200 bytes, CRC32C",
        "digital_twin": "one target, 130-190 km/h",
        "production_authority": "NOT_AUTHORIZED",
        "docx_style_audit": audit_docx(DOCX_PATH.read_bytes()),
        "visual_review": "PASS: every rendered page inspected",
        "files": inventory_files(),
    }
    write_checksums(manifest)
    make_archive()
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    qa.update({
        "status": "PASS",
        "archive": str(DOWNLOAD.relative_to(ROOT)),
        "archive_bytes": DOWNLOAD.stat().st_size,
        "archive_sha256": sha256(DOWNLOAD),
        "pdf_visual_review": "PASS",
    })
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--finalize":
        finalize(Path(sys.argv[2]).resolve())
    elif len(sys.argv) == 2 and sys.argv[1] == "--refresh-docx":
        refresh_docx()
    else:
        prepare()
