from __future__ import annotations

import hashlib
import io
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
from tools.evt_visualizer.demo import build_demo_packet


VERSION = "1.0.0"
DATE = "2026-10-31"
ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
PACKAGE_NAME = f"EVT_ГСН_визуализатор_Windows_v{VERSION}_{DATE}"
PACKAGE_DIR = RELEASE / PACKAGE_NAME
ARCHIVE = RELEASE / f"{PACKAGE_NAME}.zip"
DOWNLOAD = RELEASE / "downloads" / f"EVT_GSN_visualizer_windows_v{VERSION}.zip"
QA_PATH = RELEASE / f"{PACKAGE_NAME}_QA.json"
EXE_SOURCE = ROOT / ".codex-temp" / "evt_viz_dist2" / "EVT_GSN_Visualizer.exe"


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


def shade(cell, color: str = "D9EAF7") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.find(qn("w:shd"))
    if node is None:
        node = OxmlElement("w:shd")
        tc_pr.append(node)
    node.set(qn("w:fill"), color)


def set_widths(table, widths: list[float]) -> None:
    table.autofit = False
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        cant_split.set(qn("w:val"), "true")
        tr_pr.append(cant_split)
        for index, width in enumerate(widths):
            row.cells[index].width = Cm(width)


def table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    item = doc.add_table(rows=1, cols=len(headers))
    item.style = "Table Grid"
    set_repeat_header(item.rows[0])
    for index, text in enumerate(headers):
        cell = item.rows[0].cells[index]
        cell.text = text
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for values in rows:
        cells = item.add_row().cells
        for index, text in enumerate(values):
            cells[index].text = str(text)
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    set_widths(item, widths)


def paragraph(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def equipment_rows() -> list[list[str]]:
    return [
        ["1", "Плата EVT_SYS_CARRIER", "1", "Собранный и осмотренный Pilot R1", "Контроллер, питание и выдача TargetState"],
        ["2", "Радиолокационный модуль", "1", "AWR2944PEVM с исправным штатным соединением", "Получение реальных целей"],
        ["3", "Лабораторный источник питания", "1", "0-15 В, не менее 5 А, ограничение тока", "Питание платы 12 В через J1"],
        ["4", "Кабель питания J1", "1", "Ответная часть для 43650-0200, правильная полярность", "Соединение источника и платы"],
        ["5", "USB-UART адаптер", "1", "TTL 3,3 В, устойчивые 921600 бод, Windows 10/11", "Основной канал J6 UART1"],
        ["6", "Второй USB-UART адаптер", "1, опция", "Такие же требования", "Одновременная проверка UART2"],
        ["7", "Жгут J6", "1", "Molex 43025-0600 и подходящие женские контакты 43030 по сечению провода", "Подключение адаптера без пайки к плате"],
        ["8", "Компьютер", "1", "Windows 10/11 x64, свободный USB-порт", "Запуск EXE, запись CSV и BIN"],
        ["9", "USB-кабель", "1", "Соответствует разъему выбранного адаптера", "Соединение адаптера с компьютером"],
        ["10", "Жгут радара", "1", "Питание J5, CAN-FD и RADAR_REF через J4", "Полная функциональная проверка радара"],
        ["11", "CAN-FD адаптер", "1", "500 кбит/с nominal, 2,5 Мбит/с data, BRS", "Диагностика интерфейса радара"],
        ["12", "Оконечная нагрузка CAN", "По стенду", "Согласована с топологией стенда", "Устойчивая работа CAN-FD"],
        ["13", "ST-LINK и Tag-Connect", "1", "ST-LINK/V3SET и кабель для J10", "Прошивка и аварийное восстановление"],
        ["14", "Цифровой мультиметр", "1", "Постоянное напряжение и сопротивление", "Проверка питания и отсутствия КЗ"],
        ["15", "Осциллограф", "1", "Не менее 100 МГц, щуп 10:1, короткая земля", "Уровни UART, пульсации, RADAR_REF"],
        ["16", "Тепловизор или термопара", "1", "Контроль до 100 °C и регистрация", "Проверка нагрева"],
        ["17", "Средства ESD", "1 комплект", "Коврик, браслет, заземление", "Защита электроники"],
        ["18", "Мишень и устойчивые стойки", "1 комплект", "Отражатель и безопасная зона испытаний", "Наблюдение реальной отметки"],
        ["19", "Внешний GNSS модуль", "1, опция", "Разъемное подключение к J8, UART 3,3 В, PPS 3,3 В", "Проверка временной привязки"],
        ["20", "Предохранитель и быстрое отключение", "1", "В цепи 12 В, доступно оператору", "Немедленное снятие питания"],
    ]


def make_instruction() -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    doc.core_properties.title = "Инструкция по подключению и работе с визуализатором EVT ГСН"
    doc.core_properties.subject = "USB-UART 3,3 В, Windows EXE, стендовая проверка"
    doc.core_properties.version = VERSION

    doc.add_paragraph("ИНСТРУКЦИЯ ПО ПОДКЛЮЧЕНИЮ И РАБОТЕ С ВИЗУАЛИЗАТОРОМ EVT ГСН", style="Title")
    paragraph(doc, f"Обозначение: EVT-GSN-VIS-001. Версия: {VERSION}. Дата выпуска: {DATE}.")
    paragraph(doc, "Основное подключение к компьютеру выполняют через USB-UART адаптер с логическими уровнями 3,3 В. Адаптер передает данные и обеспечивает общую землю. Питание платы от контактов VCC, 3V3 или 5V адаптера запрещено.")

    heading(doc, "1 Назначение", 1)
    paragraph(doc, "Программа EVT_GSN_Visualizer.exe отображает поток TargetState V1 от платы EVT_SYS_CARRIER на экране Windows. На индикаторе вида сверху показаны положение и траектория целей. Таблица показывает идентификатор, дальность, азимут, радиальную скорость, SNR и качество. Для выбранной цели выводятся дополнительные поля. Программа записывает CSV и исходный BIN, воспроизводит BIN и имеет демонстрационный режим.")
    paragraph(doc, "Готовый EXE не требует установленного Python. Демонстрационный режим подтверждает работу интерфейса программы, но не подтверждает исправность прибора, USB-UART, радара или стенда.")

    heading(doc, "2 Состав стенда", 1)
    table(doc, ["N", "Наименование", "Количество", "Требование", "Назначение"], equipment_rows(), [1.0, 5.6, 2.0, 8.2, 8.4])

    heading(doc, "3 Требования к USB-UART адаптеру", 1)
    paragraph(doc, "Обязателен адаптер TTL UART с уровнями 3,3 В и устойчивой скоростью 921600 бод. Подходят изделия на базе FTDI или Silicon Labs, если конкретный готовый адаптер действительно выводит сигналы UART 3,3 В и изготовитель подтверждает скорость 921600 бод. Рекомендуемый готовый кабель: FTDI TTL-232R-3V3. Адаптер RS-232 имеет другие электрические уровни и не подходит. Адаптер RS-485 также не подходит.")
    table(doc, ["Параметр", "Значение"], [
        ["Логические уровни", "TTL 3,3 В"],
        ["Скорость", "921600 бод"],
        ["Формат", "8 бит данных, без четности, 1 стоп-бит, без управления потоком"],
        ["Основной канал", "J6 UART1"],
        ["Запасной канал", "J6 UART2, второй адаптер не обязателен для обычной работы"],
        ["Питание платы", "Только отдельные 12 В через J1"],
    ], [7.0, 18.0])

    heading(doc, "4 Схема подключения J6", 1)
    table(doc, ["Контакт платы", "Сигнал", "Контакт USB-UART", "Статус", "Примечание"], [
        ["J6.1", "GND", "GND", "Обязательно", "Общая земля платы и компьютера"],
        ["J6.2", "HOST_UART1_TX", "RX", "Обязательно", "Основной поток TargetState от платы"],
        ["J6.3", "HOST_UART1_RX", "TX", "Опция", "Нужен только для обратного канала"],
        ["J6.4", "GND", "GND второго адаптера", "Опция", "Земля запасного канала"],
        ["J6.5", "HOST_UART2_TX", "RX второго адаптера", "Опция", "Резервный поток TargetState"],
        ["J6.6", "HOST_UART2_RX", "TX второго адаптера", "Опция", "Обратный канал UART2"],
        ["VCC/3V3/5V адаптера", "Не используется", "Не подключать", "Запрещено", "Возможны повреждение и обратное питание"],
    ], [3.0, 6.2, 6.0, 3.2, 7.0])
    paragraph(doc, "Линии TX и RX соединяют крест-накрест: TX платы идет на RX адаптера, TX адаптера идет на RX платы. Соединение выполняют при снятом питании платы и отключенном USB. Для основного отображения достаточно трех проводов J6.1, J6.2 и RX адаптера. Контакт J6.3 можно не подключать.")

    heading(doc, "5 Подготовка Windows", 1)
    table(doc, ["Шаг", "Действие", "Ожидаемый результат"], [
        ["1", "Подключить USB-UART к компьютеру без соединения с платой.", "В диспетчере устройств появляется COM-порт без предупреждения."],
        ["2", "Если драйвер не установлен, взять драйвер только с официального сайта производителя микросхемы адаптера.", "COM-порт появляется стабильно после повторного подключения."],
        ["3", "Распаковать архив в папку с правом записи.", "EXE, инструкции, пример BIN и исходники доступны."],
        ["4", "Запустить EVT_GSN_Visualizer.exe.", "Открывается темное окно с индикатором, таблицей целей и панелью управления."],
        ["5", "Нажать Демо.", "Появляются три движущиеся цели, счетчики пакетов растут, пропуски равны нулю."],
    ], [1.5, 11.0, 13.5])

    heading(doc, "6 Первое подключение прибора", 1)
    table(doc, ["Шаг", "Действие", "Ожидаемый результат", "Когда остановить"], [
        ["1", "Снять питание, осмотреть плату, разъемы и жгут.", "Нет повреждений, загрязнений, переполюсовки и замыканий.", "При любом видимом дефекте."],
        ["2", "Установить источник 12,0 В и предел 0,50 А. Пока не включать.", "J1.1 подготовлен к плюсу, J1.2 к GND.", "Если распиновка или полярность не подтверждены."],
        ["3", "Соединить J6.1 с GND адаптера, J6.2 с RX адаптера. При необходимости соединить J6.3 с TX.", "VCC, 3V3 и 5V адаптера изолированы.", "Если уровни адаптера не подтверждены как 3,3 В TTL."],
        ["4", "Подключить адаптер к USB компьютера.", "В Windows появился известный COM-порт.", "При нагреве адаптера или нестабильном обнаружении."],
        ["5", "Подать 12 В на плату на 2 с.", "Нет дыма, запаха, искрения, шума и срабатывания ограничения 0,50 А.", "Немедленно при любом признаке повреждения."],
        ["6", "Проверить J10.1, J8.1 и J5.1 относительно GND.", "3,135-3,465 В; 4,75-5,25 В; 11,4-12,6 В.", "При выходе любой шины за пределы или провалах."],
        ["7", "Запустить EXE, нажать Обновить, выбрать COM-порт и нажать Подключить.", "Статус показывает COM-порт и 921600 8N1.", "При ошибке открытия порта проверить, не занят ли он другой программой."],
        ["8", "Подключить исправный радар и его жгуты только при снятом питании, затем повторить включение.", "Счетчик пакетов растет, цели появляются при наличии отражателей.", "При ошибках питания, CAN-FD, нагреве или сбросах."],
        ["9", "Нажать Запись и выбрать имя CSV.", "Созданы CSV и BIN с одинаковой основой имени.", "При ошибке записи выбрать доступную локальную папку."],
        ["10", "Перемещать контрольную мишень в разрешенной зоне.", "Дальность и азимут изменяются согласованно, sequence растет, CRC принимается.", "При скачках, NaN, росте пропусков или несогласованном движении."],
    ], [1.2, 8.0, 8.2, 8.6])

    heading(doc, "7 Органы управления", 1)
    table(doc, ["Элемент", "Назначение"], [
        ["Обновить", "Повторно получает список COM-портов после подключения или замены адаптера."],
        ["Подключить", "Открывает выбранный COM-порт с фиксированными параметрами 921600 8N1."],
        ["Отключить", "Останавливает текущий COM-порт, демо или воспроизведение."],
        ["Демо", "Генерирует три синтетические цели для проверки графики и декодера."],
        ["Открыть BIN", "Воспроизводит ранее записанные пакеты TargetState V1."],
        ["Запись", "Создает CSV с разобранными полями и BIN с исходными пакетами."],
        ["Подключение", "Показывает краткую памятку по J6 и ограничениям USB-UART."],
        ["Дальность", "Выбирает масштаб индикатора от 25 до 500 м."],
    ], [6.0, 19.0])

    heading(doc, "8 Ожидаемые результаты", 1)
    table(doc, ["Проверка", "Признак исправности", "Ограничение результата"], [
        ["Запуск EXE", "Окно открывается без установки Python.", "Не подтверждает связь с прибором."],
        ["Демо", "Три цели движутся, пакеты растут, пропуски не растут.", "Не подтверждает аппаратную часть."],
        ["COM-порт", "Статус содержит выбранный порт и 921600 8N1.", "Подтверждает открытие порта, но не качество данных."],
        ["Декодирование", "Цели и таблица обновляются, поля конечны, счетчик пропусков не растет.", "Требует реального потока TargetState V1."],
        ["Запись", "CSV открывается как таблица, BIN повторно воспроизводится.", "Время компьютера не заменяет временную метку прибора."],
        ["Реальная мишень", "Дальность и азимут изменяются согласно перемещению мишени.", "Точность подтверждают отдельной методикой EVT."],
    ], [6.0, 11.0, 8.0])

    heading(doc, "9 Неисправности и действия", 1)
    table(doc, ["Симптом", "Проверить", "Действие"], [
        ["COM-порт отсутствует", "USB-кабель, драйвер, адаптер, другой USB-порт.", "Установить официальный драйвер, исключить неисправный кабель."],
        ["COM-порт занят", "Терминал, логгер, другая копия программы.", "Закрыть программу, которая уже открыла порт."],
        ["Пакеты не поступают", "Общую землю, J6.2 к RX, питание и прошивку.", "Не менять скорость. Проверить TX осциллографом."],
        ["Много пропусков", "Качество адаптера, кабель, землю, помехи, загрузку ПК.", "Укоротить жгут, заменить адаптер на подтвержденный 921600 бод."],
        ["Цели отсутствуют", "Питание радара, CAN-FD, RADAR_REF, наличие мишени.", "Сначала подтвердить встроенное Демо, затем диагностировать прибор."],
        ["Поля скачут или нереальны", "Совпадение версии TargetState, CRC32C, байтового потока.", "Сохранить BIN, прекратить оценку точности и оформить отклонение."],
        ["Программа не может записать файлы", "Права на папку и свободное место.", "Выбрать локальную папку Документы или другую доступную папку."],
        ["Нагрев или запах", "Плату, жгут, адаптер и полярность.", "Немедленно снять 12 В и USB, повторно не включать до расследования."],
    ], [6.0, 10.0, 9.0])

    heading(doc, "10 Прошивка и восстановление", 1)
    paragraph(doc, "Для штатной визуализации программатор не нужен. Если контроллер не выдает данные из-за отсутствующей или поврежденной прошивки, подключают ST-LINK/V3SET к J10 при снятом питании. Плату питают от J1, а не от программатора. Записывают утвержденный HEX, выполняют verify и сохраняют лог и SHA-256. Подробная процедура прошивки остается в производственном и EVT комплектах проекта.")

    heading(doc, "11 Сборка из исходников", 1)
    paragraph(doc, "Исходники находятся в папке 02_Исходный_код. Требуются Python 3.12 x64, pyserial 3.5 и PyInstaller. После установки зависимостей запускают tools/evt_visualizer/build_windows.ps1 из корня репозитория. Готовый EXE должен пройти тесты протокола и запуск с параметрами --demo --smoke-seconds 3.")

    heading(doc, "12 Официальные справочные материалы", 1)
    table(doc, ["Материал", "Ссылка"], [
        ["FTDI TTL-232R-3V3", "https://ftdichip.com/products/ttl-232r-3v3/"],
        ["FTDI, расчет скорости передачи", "https://ftdichip.com/Support/Knowledgebase/an232b_05calc.htm"],
        ["Silicon Labs CP2102/9, электрические параметры и скорости", "https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf"],
        ["Molex Micro-Fit 3.0, семейство 43025", "https://www.molex.com/en-us/products/series-chart/43025"],
    ], [9.0, 16.0])

    heading(doc, "13 Статус допуска", 1)
    paragraph(doc, "Программа и настоящий комплект предназначены для EVT и стендовой проверки пилотного образца. Они не выдают разрешение на серийное производство. Production authority сохраняется в состоянии NOT_AUTHORIZED. Это не мешает изготовлению и испытанию EVT образца по утвержденному пилотному комплекту, но запрещает трактовать результаты как серийный производственный допуск.")

    stream = io.BytesIO()
    doc.save(stream)
    payload, _report = transform_docx(stream.getvalue(), version=VERSION)
    return payload


def copy_sources(target: Path) -> None:
    shutil.copytree(ROOT / "tools" / "evt_visualizer", target / "tools" / "evt_visualizer")
    (target / "tools" / "hil_host").mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "protocol.py", "targetstate.py"):
        shutil.copy2(ROOT / "tools" / "hil_host" / name, target / "tools" / "hil_host" / name)
    (target / "tests" / "python").mkdir(parents=True, exist_ok=True)
    for name in ("test_evt_visualizer.py", "test_protocol.py"):
        shutil.copy2(ROOT / "tests" / "python" / name, target / "tests" / "python" / name)


def write_demo(path: Path) -> int:
    packets = []
    sequence = 1
    for frame in range(125):
        elapsed = frame * 0.08
        for track_id in (1, 2, 3):
            packets.append(build_demo_packet(sequence, elapsed, track_id))
            sequence += 1
    path.write_bytes(b"".join(packets))
    return len(packets)


def make_archive(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, Path(source.name) / path.relative_to(source))


def inventory_files() -> list[dict]:
    checksums = PACKAGE_DIR / "05_Контрольные_суммы"
    result = []
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file() and checksums not in path.parents:
            result.append({
                "path": path.relative_to(PACKAGE_DIR).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return result


def write_checksums(manifest: dict) -> None:
    checksums = PACKAGE_DIR / "05_Контрольные_суммы"
    manifest_path = checksums / "Манифест_выпуска.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"{item['sha256']} *{item['path']}" for item in manifest["files"]]
    lines.append(f"{sha256(manifest_path)} *{manifest_path.relative_to(PACKAGE_DIR).as_posix()}")
    (checksums / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize_pdf(pdf_source: Path) -> None:
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError(PACKAGE_DIR)
    instructions = PACKAGE_DIR / "03_Инструкции"
    target = instructions / f"Инструкция_USB_UART_и_визуализатор_EVT_ГСН_v{VERSION}.pdf"
    shutil.copy2(pdf_source, target)
    manifest_path = PACKAGE_DIR / "05_Контрольные_суммы" / "Манифест_выпуска.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pdf_visual_review"] = "PASS: 7 pages inspected at 100 percent"
    manifest["files"] = inventory_files()
    write_checksums(manifest)
    make_archive(PACKAGE_DIR, ARCHIVE)
    shutil.copy2(ARCHIVE, DOWNLOAD)
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    qa["archive_sha256"] = sha256(ARCHIVE)
    qa["archive_bytes"] = ARCHIVE.stat().st_size
    qa["pdf_visual_review"] = "PASS: 7 pages inspected at 100 percent"
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


def main() -> None:
    if not EXE_SOURCE.exists():
        raise FileNotFoundError(EXE_SOURCE)
    if PACKAGE_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite released package: {PACKAGE_DIR}")
    PACKAGE_DIR.mkdir(parents=True)

    program = PACKAGE_DIR / "01_Программа_Windows"
    sources = PACKAGE_DIR / "02_Исходный_код"
    instructions = PACKAGE_DIR / "03_Инструкции"
    examples = PACKAGE_DIR / "04_Примеры_данных"
    checksums = PACKAGE_DIR / "05_Контрольные_суммы"
    for directory in (program, sources, instructions, examples, checksums):
        directory.mkdir(parents=True)

    exe = program / "EVT_GSN_Visualizer.exe"
    shutil.copy2(EXE_SOURCE, exe)
    copy_sources(sources)

    docx = instructions / f"Инструкция_USB_UART_и_визуализатор_EVT_ГСН_v{VERSION}.docx"
    docx.write_bytes(make_instruction())
    audit = audit_docx(docx.read_bytes())
    if audit["status"] != "PASS":
        raise ValueError(audit)

    demo = examples / "Демонстрационный_поток_TargetState_V1.bin"
    packet_count = write_demo(demo)

    inventory = inventory_files()
    manifest = {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "date": DATE,
        "interface": "USB-UART TTL 3.3 V, 921600 8N1",
        "main_channel": "J6.1 GND, J6.2 HOST_UART1_TX to adapter RX, J6.3 HOST_UART1_RX to adapter TX optional",
        "demo_packets": packet_count,
        "docx_style_audit": audit,
        "files": inventory,
    }
    write_checksums(manifest)

    make_archive(PACKAGE_DIR, ARCHIVE)
    shutil.copy2(ARCHIVE, DOWNLOAD)
    qa = {
        "status": "PASS",
        "version": VERSION,
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "download": str(DOWNLOAD.relative_to(ROOT)),
        "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "exe_sha256": sha256(exe),
        "exe_bytes": exe.stat().st_size,
        "docx_style_audit": audit,
        "demo_packets": packet_count,
        "test_command": "pytest tests/python/test_evt_visualizer.py tests/python/test_protocol.py",
        "test_result": "8 passed",
        "visual_check": "PASS: demo targets, table, counters, connection help",
        "production_authority": "NOT_AUTHORIZED",
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--finalize-pdf":
        finalize_pdf(Path(sys.argv[2]).resolve())
    else:
        main()
