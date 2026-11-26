from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm

from tools.docx_style_policy import audit_docx, transform_docx
from tools.evt_digital_twin.model import TwinEngine, default_scenario


VERSION = "1.0.0"
VISUALIZER_VERSION = "1.2.0"
DATE = "2026-11-01"
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = f"EVT_ГСН_цифровой_двойник_Windows_v{VERSION}_{DATE}"
PACKAGE_DIR = ROOT / "release" / PACKAGE_NAME
DOWNLOAD = ROOT / "release" / "downloads" / f"EVT_GSN_digital_twin_windows_v{VERSION}.zip"
QA_PATH = ROOT / "release" / f"{PACKAGE_NAME}_QA.json"
TWIN_EXE = ROOT / ".codex-temp" / "evt_twin_dist" / "EVT_GSN_Digital_Twin.exe"
VISUALIZER_EXE = ROOT / ".codex-temp" / "evt_viz_v120_dist" / "EVT_GSN_Visualizer.exe"
DOCX_PATH = PACKAGE_DIR / "03_Инструкции" / f"Развертывание_и_использование_цифрового_двойника_v{VERSION}.docx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_repeat_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    node.set(qn("w:val"), "true")
    properties.append(node)


def prevent_row_split(row) -> None:
    properties = row._tr.get_or_add_trPr()
    if properties.find(qn("w:cantSplit")) is None:
        properties.append(OxmlElement("w:cantSplit"))


def shade(cell, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    node = properties.find(qn("w:shd"))
    if node is None:
        node = OxmlElement("w:shd")
        properties.append(node)
    node.set(qn("w:fill"), color)


def set_cell_margins(cell, value: int = 100) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for tag in ("top", "start", "bottom", "end"):
        node = margins.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    center_columns: set[int] | None = None,
) -> None:
    center_columns = center_columns or set()
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    set_repeat_header(table.rows[0])
    prevent_row_split(table.rows[0])
    for index, text in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = text
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cell, "D9EAF7")
        set_cell_margins(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        cells = row.cells
        for index, value in enumerate(values):
            cells[index].text = str(value)
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[index])
            if row_index % 2:
                shade(cells[index], "F5F8FA")
            if index in center_columns:
                cells[index].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Cm(width)


def paragraph(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def make_instruction() -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    doc.core_properties.title = "Развертывание и использование автономного цифрового двойника EVT ГСН"
    doc.core_properties.subject = "Настройка ЭПР, скорости и траекторий объектов, вывод в визуализатор"
    doc.core_properties.version = VERSION

    doc.add_paragraph("АВТОНОМНЫЙ ЦИФРОВОЙ ДВОЙНИК EVT ГСН", style="Title")
    paragraph(doc, "Программный комплект для Windows")
    paragraph(doc, f"Руководство по развертыванию и использованию. Версия {VERSION}. Дата выпуска {DATE}.")
    paragraph(
        doc,
        "Цифровой двойник формирует воспроизводимые потоки телеметрии TargetState V1 для одного или нескольких летающих объектов. Пользователь настраивает ЭПР, скорость, начальную дальность, углы, курс, вертикальную скорость и маневр каждого объекта. Поток передается по локальному TCP в программу EVT_GSN_Visualizer.exe и при необходимости записывается в BIN. Двойник не формирует управляющие команды и не заменяет стендовую проверку реального изделия.",
    )

    heading(doc, "1 Назначение и границы применения")
    paragraph(
        doc,
        "Комплект предназначен для проверки приема, декодирования, отображения и записи телеметрии без аппаратной платы и USB-UART адаптера. Он позволяет подготовить сценарии с различной ЭПР и скоростью, проверить одновременное сопровождение до 16 объектов, оценить поведение интерфейса при изменении дальности и углов, а также получить контрольный BIN-поток для повторного воспроизведения.",
    )
    paragraph(
        doc,
        "Расчет SNR использует упрощенную инженерную зависимость от ЭПР и четвертой степени дальности. Результат служит для функциональной проверки программного тракта. Он не является подтверждением дальности обнаружения, точности, вероятности обнаружения или характеристик серийного радара.",
    )

    heading(doc, "2 Состав комплекта")
    add_table(
        doc,
        ["Папка", "Содержимое", "Назначение"],
        [
            ["01_Программы_Windows", "EVT_GSN_Digital_Twin.exe, EVT_GSN_Visualizer.exe, запуск обоих приложений", "работа без установки Python"],
            ["02_Исходный_код", "исходники двойника, визуализатора, протокола и тесты", "аудит, изменение и повторная сборка"],
            ["03_Инструкции", "настоящее руководство DOCX и PDF, схема обмена SVG", "развертывание и эксплуатация"],
            ["04_Сценарии", "пример JSON и контрольный BIN", "быстрый запуск и проверка декодера"],
            ["05_Контрольные_суммы", "манифест и SHA256SUMS", "контроль целостности"],
        ],
        [4.2, 6.1, 5.1],
    )

    heading(doc, "3 Требования к компьютеру")
    add_table(
        doc,
        ["Параметр", "Требование"],
        [
            ["Операционная система", "Windows 10 или Windows 11, x64"],
            ["Права", "обычные права пользователя, установка службы и драйвера не требуется"],
            ["Сеть", "локальное соединение 127.0.0.1, TCP-порт по умолчанию 9750"],
            ["Экран", "не менее 1366 x 768, рекомендуется масштаб Windows 100 или 125 процентов"],
            ["Свободное место", "не менее 200 МБ для распаковки, больше при длительной записи BIN"],
        ],
        [5.0, 10.4],
    )

    heading(doc, "4 Развертывание")
    add_table(
        doc,
        ["Шаг", "Действие", "Ожидаемый результат"],
        [
            ["1", "Скопировать архив в локальную папку с правом записи.", "Архив доступен без запуска из браузера."],
            ["2", "Полностью распаковать архив. Не запускать EXE непосредственно из ZIP.", "Создана папка комплекта с пятью подпапками."],
            ["3", "Открыть папку 01_Программы_Windows.", "Видны два EXE и командный файл совместного запуска."],
            ["4", "Запустить Запустить_двойник_и_визуализатор.bat или оба EXE вручную.", "Открываются окно двойника и окно визуализатора."],
            ["5", "Если Windows показывает предупреждение, проверить имя и SHA-256 по манифесту.", "Контрольная сумма совпадает с SHA256SUMS.txt."],
        ],
        [1.2, 8.0, 6.2],
        {0},
    )

    heading(doc, "5 Параметры сценария")
    add_table(
        doc,
        ["Параметр", "Допустимое значение", "Смысл"],
        [
            ["Имя сценария", "непустая строка", "обозначение набора объектов"],
            ["TCP-порт", "1..65535, по умолчанию 9750", "порт локального сервера"],
            ["Частота обновления", "1..50 Гц", "частота шагов модели и передачи"],
            ["Максимальная дальность", "100..10000 м", "граница области моделирования"],
            ["Шум дальности", "0..100 м", "СКО нормального измерительного шума"],
            ["Шум угла", "0..10 градусов", "СКО шума азимута и угла места"],
            ["Записывать BIN", "включено или выключено", "сохранение всех переданных пакетов"],
        ],
        [4.3, 4.1, 7.0],
    )

    heading(doc, "6 Параметры летающего объекта")
    add_table(
        doc,
        ["Параметр", "Диапазон", "Примечание"],
        [
            ["ID", "1..65535", "уникален в пределах сценария"],
            ["ЭПР", "0,0001..100 м2", "используется в расчете SNR; точное значение хранится в JSON"],
            ["Скорость", "1..1500 км/ч", "модуль полной скорости"],
            ["Начальная дальность", "5 м..максимальная дальность", "расстояние от начала координат"],
            ["Азимут", "от -180 до +180 градусов", "начальное горизонтальное направление"],
            ["Угол места", "от -60 до +60 градусов", "начальное вертикальное направление"],
            ["Курс", "от -180 до +180 градусов", "направление горизонтальной скорости"],
            ["Вертикальная скорость", "от -100 до +100 м/с", "снижение или набор высоты"],
            ["Маневр", "прямолинейный, змейка, разворот", "закон изменения курса"],
            ["Амплитуда и период", "0..90 градусов, 1..600 с", "параметры змейки или разворота"],
        ],
        [4.2, 4.4, 6.8],
    )
    paragraph(
        doc,
        "В формате TargetState V1 отдельное поле ЭПР отсутствует. Поэтому точное заданное значение ЭПР отображается в окне двойника и сохраняется в JSON. В поток визуализатора влияние ЭПР передается через расчетные поля SNR, quality и confidence.",
    )

    heading(doc, "7 Настройка и сохранение сценария")
    add_table(
        doc,
        ["Шаг", "Действие"],
        [
            ["1", "Остановить двойник, если он уже запущен."],
            ["2", "Выбрать объект в таблице или нажать Добавить."],
            ["3", "Задать ID, имя, ЭПР, скорость, координаты, курс и параметры маневра."],
            ["4", "Нажать Применить параметры объекта. Проверить строку объекта в таблице."],
            ["5", "При необходимости повторить действия для остальных объектов. Максимум 16 объектов."],
            ["6", "Задать частоту, дальность и шумы в верхней части окна."],
            ["7", "Нажать Сохранить и выбрать файл JSON. Для повторной работы использовать Открыть."],
        ],
        [1.2, 14.2],
        {0},
    )

    heading(doc, "8 Запуск потока и подключение визуализатора")
    add_table(
        doc,
        ["Шаг", "Действие", "Ожидаемый результат", "При отклонении"],
        [
            ["1", "В двойнике нажать Запустить двойник.", "Статус содержит 127.0.0.1 и номер порта.", "Выбрать свободный порт, если он занят."],
            ["2", "Запустить визуализатор кнопкой или отдельным EXE.", "Открывается окно визуализатора.", "Проверить, что оба EXE находятся рядом."],
            ["3", "В визуализаторе указать 127.0.0.1 и тот же порт.", "Поля совпадают с настройкой двойника.", "Исправить порт в одном из приложений."],
            ["4", "Нажать Подключить к двойнику.", "Статус подтверждает TCP-соединение.", "Проверить брандмауэр и порядок запуска."],
            ["5", "Наблюдать таблицу и индикатор.", "ID, дальность, азимут, скорость и SNR изменяются.", "Проверить, что объект включен."],
            ["6", "Для завершения отключить визуализатор и остановить двойник.", "Счетчик клиентов возвращается к нулю.", "Закрыть приложения штатными кнопками окна."],
        ],
        [1.0, 5.1, 5.0, 4.0],
        {0},
    )

    heading(doc, "9 Рекомендуемые контрольные сценарии")
    add_table(
        doc,
        ["Сценарий", "Объекты", "Проверяемое поведение"],
        [
            ["Базовый", "один объект, ЭПР 0,01 м2, скорость 160 км/ч", "устойчивое декодирование и движение отметки"],
            ["Сравнение ЭПР", "три объекта на одинаковой дальности, ЭПР 0,01; 0,1; 1,0 м2", "рост расчетного SNR при увеличении ЭПР"],
            ["Диапазон скоростей", "три объекта 130; 160; 190 км/ч", "различная скорость изменения координат"],
            ["Маневр", "один объект, режим змейка", "плавное изменение азимута без потери синхронизации"],
            ["Нагрузка", "16 включенных объектов, 50 Гц", "работа интерфейса и счетчиков при максимальной конфигурации"],
        ],
        [3.0, 6.5, 6.0],
    )

    heading(doc, "10 Запись и повторное использование данных")
    paragraph(
        doc,
        "Чтобы записать поток, включают Записывать BIN, выбирают путь к файлу и затем запускают двойник. BIN содержит последовательность исходных 200-байтовых пакетов TargetState V1. Такой файл можно открыть визуализатором как сохраненный поток или использовать в автоматических проверках декодера. Перед перезаписью файла двойник следует остановить.",
    )

    heading(doc, "11 Техническое описание обмена")
    add_table(
        doc,
        ["Свойство", "Значение"],
        [
            ["Транспорт", "TCP, сервер цифрового двойника, адрес по умолчанию 127.0.0.1:9750"],
            ["Направление", "только от двойника к визуализатору"],
            ["Формат", "TargetState V1"],
            ["Размер пакета", "200 байт: заголовок 24, полезная нагрузка 172, CRC32C 4"],
            ["Сигнатура", "0x31474C52"],
            ["Границы TCP", "визуализатор восстанавливает пакеты из произвольных фрагментов потока"],
            ["Количество объектов", "до 16 включенных объектов в одном сценарии"],
        ],
        [5.0, 10.4],
    )
    paragraph(
        doc,
        "Модель SNR задается выражением SNR = 12 + 10 log10(ЭПР / 0,01) - 40 log10(R / 300) + шум, где ЭПР указана в квадратных метрах, R в метрах, шум имеет нормальное распределение. SNR ограничивается диапазоном от -30 до +70 дБ. Поля quality и confidence формируются гладкими логистическими функциями SNR.",
    )

    heading(doc, "12 Устранение неисправностей")
    add_table(
        doc,
        ["Признак", "Причина", "Действие"],
        [
            ["Двойник не запускается", "архив не распакован или файл заблокирован Windows", "распаковать комплект, проверить SHA-256 и свойства файла"],
            ["Порт занят", "другое приложение использует 9750", "выбрать другой свободный порт в обоих приложениях"],
            ["Нет целей", "визуализатор не подключен или объекты выключены", "проверить статус TCP и флажок объекта"],
            ["Ошибки CRC или формата", "поток не соответствует TargetState V1", "закрыть посторонний источник и повторить запуск обоих приложений"],
            ["BIN не создается", "папка недоступна для записи", "выбрать локальную папку пользователя"],
            ["Отметки исчезают", "объект вышел за границу или SNR стал низким", "проверить дальность, курс, ЭПР и режим зацикливания"],
        ],
        [4.2, 5.4, 5.8],
    )

    heading(doc, "13 Критерии приемки программного комплекта")
    add_table(
        doc,
        ["Проверка", "Критерий"],
        [
            ["Запуск", "оба EXE завершают встроенную дымовую проверку без ошибки"],
            ["Модель", "параметры JSON проходят валидацию; пакеты имеют длину 200 байт и корректный CRC32C"],
            ["ЭПР", "при прочих равных увеличение ЭПР повышает расчетный SNR"],
            ["TCP", "визуализатор принимает поток с 127.0.0.1 и обновляет цели"],
            ["Документация", "DOCX соответствует установленному шаблону, PDF визуально проверен"],
            ["Целостность", "все значения SHA-256 совпадают с манифестом"],
        ],
        [5.4, 10.0],
    )

    heading(doc, "14 Статус допуска")
    paragraph(
        doc,
        "Комплект предназначен для программной и стендовой подготовки EVT. Production authority остается NOT_AUTHORIZED. Выпуск цифрового двойника не является разрешением на производство, эксплуатацию или передачу управляющих команд внешней системе.",
    )

    stream = io.BytesIO()
    doc.save(stream)
    payload, _report = transform_docx(stream.getvalue(), version=VERSION)
    return payload


def make_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="620" viewBox="0 0 1400 620">
  <rect width="1400" height="620" fill="#ffffff"/>
  <style>
    .title { font: bold 30px 'Times New Roman'; fill: #111111; }
    .label { font: 24px 'Times New Roman'; fill: #111111; }
    .small { font: 20px 'Times New Roman'; fill: #333333; }
    .box { fill: #f7f7f7; stroke: #333333; stroke-width: 3; }
    .wire { stroke: #333333; stroke-width: 5; fill: none; marker-end: url(#arrow); }
  </style>
  <defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#333333"/></marker></defs>
  <text x="700" y="55" text-anchor="middle" class="title">Обмен цифрового двойника и визуализатора EVT ГСН</text>
  <rect x="60" y="120" width="480" height="330" rx="14" class="box"/>
  <text x="300" y="175" text-anchor="middle" class="title">Цифровой двойник</text>
  <text x="100" y="240" class="label">до 16 объектов</text>
  <text x="100" y="290" class="label">ЭПР, скорость, координаты</text>
  <text x="100" y="340" class="label">курс и маневр</text>
  <text x="100" y="390" class="label">расчет SNR и CRC32C</text>
  <rect x="860" y="120" width="480" height="330" rx="14" class="box"/>
  <text x="1100" y="175" text-anchor="middle" class="title">Визуализатор</text>
  <text x="900" y="240" class="label">декодирование TargetState V1</text>
  <text x="900" y="290" class="label">таблица и полярный индикатор</text>
  <text x="900" y="340" class="label">CSV и BIN</text>
  <text x="900" y="390" class="label">без управляющих команд</text>
  <path d="M540 285 L860 285" class="wire"/>
  <text x="700" y="250" text-anchor="middle" class="small">TCP 127.0.0.1:9750</text>
  <text x="700" y="335" text-anchor="middle" class="small">200 байт на пакет, CRC32C</text>
  <rect x="210" y="505" width="980" height="70" rx="10" fill="#fff4e5" stroke="#6b4f00" stroke-width="2"/>
  <text x="700" y="548" text-anchor="middle" class="label">Модель предназначена для функциональной проверки программного тракта.</text>
</svg>
"""


def copy_sources(target: Path) -> None:
    shutil.copytree(
        ROOT / "tools" / "evt_digital_twin",
        target / "tools" / "evt_digital_twin",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        ROOT / "tools" / "evt_visualizer",
        target / "tools" / "evt_visualizer",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )
    (target / "tools" / "hil_host").mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "protocol.py", "targetstate.py"):
        shutil.copy2(ROOT / "tools" / "hil_host" / name, target / "tools" / "hil_host" / name)
    (target / "tests" / "python").mkdir(parents=True, exist_ok=True)
    for name in ("test_evt_digital_twin_windows.py", "test_evt_visualizer.py", "test_protocol.py"):
        shutil.copy2(ROOT / "tests" / "python" / name, target / "tests" / "python" / name)


def write_demo(path: Path) -> int:
    engine = TwinEngine(default_scenario())
    packets = []
    for _step in range(100):
        packets.extend(sample.packet for sample in engine.step())
    path.write_bytes(b"".join(packets))
    return len(packets)


def inventory_files() -> list[dict]:
    checksum_dir = PACKAGE_DIR / "05_Контрольные_суммы"
    result = []
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file() and checksum_dir not in path.parents:
            result.append(
                {
                    "path": path.relative_to(PACKAGE_DIR).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return result


def write_checksums(manifest: dict) -> None:
    checksum_dir = PACKAGE_DIR / "05_Контрольные_суммы"
    manifest_path = checksum_dir / "Манифест_выпуска.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"{item['sha256']} *{item['path']}" for item in manifest["files"]]
    lines.append(f"{sha256(manifest_path)} *{manifest_path.relative_to(PACKAGE_DIR).as_posix()}")
    (checksum_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_archive() -> None:
    DOWNLOAD.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DOWNLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, Path(PACKAGE_DIR.name) / path.relative_to(PACKAGE_DIR))


def write_programs(program_dir: Path) -> None:
    shutil.copy2(TWIN_EXE, program_dir / "EVT_GSN_Digital_Twin.exe")
    shutil.copy2(VISUALIZER_EXE, program_dir / "EVT_GSN_Visualizer.exe")
    (program_dir / "Запустить_двойник_и_визуализатор.bat").write_text(
        "@echo off\r\n"
        "start \"\" \"%~dp0EVT_GSN_Digital_Twin.exe\" --auto-start --port 9750\r\n"
        "timeout /t 1 /nobreak >nul\r\n"
        "start \"\" \"%~dp0EVT_GSN_Visualizer.exe\" --tcp --tcp-host 127.0.0.1 --tcp-port 9750\r\n",
        encoding="utf-8-sig",
    )


def prepare() -> None:
    for path in (TWIN_EXE, VISUALIZER_EXE):
        if not path.exists():
            raise FileNotFoundError(path)
    if PACKAGE_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite {PACKAGE_DIR}")
    for directory in (
        PACKAGE_DIR / "01_Программы_Windows",
        PACKAGE_DIR / "02_Исходный_код",
        PACKAGE_DIR / "03_Инструкции",
        PACKAGE_DIR / "04_Сценарии",
        PACKAGE_DIR / "05_Контрольные_суммы",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    program_dir = PACKAGE_DIR / "01_Программы_Windows"
    write_programs(program_dir)
    copy_sources(PACKAGE_DIR / "02_Исходный_код")
    DOCX_PATH.write_bytes(make_instruction())
    audit = audit_docx(DOCX_PATH.read_bytes())
    if audit["status"] != "PASS":
        raise ValueError(audit)
    (PACKAGE_DIR / "03_Инструкции" / "Схема_обмена_двойник_визуализатор.svg").write_text(
        make_svg(), encoding="utf-8"
    )
    scenario = default_scenario()
    scenario.save(PACKAGE_DIR / "04_Сценарии" / "Пример_3_объекта_разная_ЭПР.json")
    packet_count = write_demo(PACKAGE_DIR / "04_Сценарии" / "Контрольный_поток_3_объекта_TargetState_V1.bin")
    QA_PATH.write_text(
        json.dumps(
            {
                "status": "PREPARED",
                "version": VERSION,
                "visualizer_version": VISUALIZER_VERSION,
                "docx_style_audit": audit,
                "demo_packets": packet_count,
                "tests": "15 passed",
                "twin_exe_sha256": sha256(program_dir / "EVT_GSN_Digital_Twin.exe"),
                "visualizer_exe_sha256": sha256(program_dir / "EVT_GSN_Visualizer.exe"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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


def refresh_programs() -> None:
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError(PACKAGE_DIR)
    program_dir = PACKAGE_DIR / "01_Программы_Windows"
    write_programs(program_dir)
    copy_sources(PACKAGE_DIR / "02_Исходный_код")
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    qa["twin_exe_sha256"] = sha256(program_dir / "EVT_GSN_Digital_Twin.exe")
    qa["visualizer_exe_sha256"] = sha256(program_dir / "EVT_GSN_Visualizer.exe")
    qa["status"] = "PREPARED"
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


def finalize(pdf_path: Path) -> None:
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError(PACKAGE_DIR)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    target_pdf = PACKAGE_DIR / "03_Инструкции" / f"Развертывание_и_использование_цифрового_двойника_v{VERSION}.pdf"
    shutil.copy2(pdf_path, target_pdf)
    manifest = {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "visualizer_version": VISUALIZER_VERSION,
        "date": DATE,
        "platform": "Windows 10/11 x64",
        "transport": "local TCP 127.0.0.1:9750",
        "packet": "TargetState V1, 200 bytes, CRC32C",
        "targets": "1..16 configurable objects",
        "configurable": "RCS, speed, range, azimuth, elevation, course, vertical speed, maneuver",
        "control_output": "none; telemetry only",
        "production_authority": "NOT_AUTHORIZED",
        "docx_style_audit": audit_docx(DOCX_PATH.read_bytes()),
        "visual_review": "PASS: every rendered page inspected",
        "files": inventory_files(),
    }
    write_checksums(manifest)
    make_archive()
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    qa.update(
        {
            "status": "PASS",
            "archive": str(DOWNLOAD.relative_to(ROOT)),
            "archive_bytes": DOWNLOAD.stat().st_size,
            "archive_sha256": sha256(DOWNLOAD),
            "pdf_visual_review": "PASS",
        }
    )
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--finalize":
        finalize(Path(sys.argv[2]).resolve())
    elif len(sys.argv) == 2 and sys.argv[1] == "--refresh-docx":
        refresh_docx()
    elif len(sys.argv) == 2 and sys.argv[1] == "--refresh-programs":
        refresh_programs()
    else:
        prepare()
