from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.docx_style_policy import audit_docx, transform_docx


RELEASE = ROOT / "release"
SOURCE = RELEASE / "EVT_ГСН_документы_v1.1.1_2026-10-31"
TARGET = RELEASE / "EVT_ГСН_документы_v1.2.0_2026-11-02"
ALGORITHM = (
    TARGET
    / "01_Технический_проект"
    / "Принципы_работы_и_алгоритмы_функционирования_EVT_ГСН_v1.2.0.docx"
)
ARCHIVE = RELEASE / "EVT_ГСН_документы_v1.2.0_2026-11-02.zip"
METHODS_ARCHIVE = RELEASE / "EVT_ГСН_ПМ_EVT_и_отчетные_материалы_v1.2.0_2026-11-02.zip"
DOWNLOADS = RELEASE / "downloads"
VERSION = "1.2.0"
DATE = "2026-11-02"


REPLACEMENTS = {
    "1.1.1": VERSION,
    "2f50a0c6aa4ea9c66c26200669f5fb8c73882021": (
        "фиксируется в MANIFEST финального архива"
    ),
    "31.10.2026": "02.11.2026",
    "2026-10-30": "2026-11-02",
    "2026-10-31": "2026-11-02",
    "Gerber X2": "Gerber RS-274X",
    "pilot_r1/fab/gerber_x2": "пакет_24В/02_Файлы_для_изготовления_платы/01_Гербер_RS274X",
    "pilot_r1/fab/nc_drill": "пакет_24В/02_Файлы_для_изготовления_платы/02_Сверловка",
    "pilot_r1/fab/ipc2581": "пакет_24В/02_Файлы_для_изготовления_платы/03_IPC_2581",
    "12V_IN": "24V_IN",
    "Источник 12 В": "Источник 24 В",
    "источника 12 В": "источника 24 В",
    "Подать 12 В": "Подать 24 В",
    "подачи 12 В": "подачи 24 В",
    "Проверить 12 В": "Проверить 24 В",
    "установлен 12,0 В": "установлен 24,0 В",
    "Вход +12 В": "Вход +24 В",
    "Вход питания платы, 12,0 В": "Вход питания платы, 24,0 В nominal; допустимый диапазон 18...32 В",
    "12 В nominal, источник не менее 5 А, независимые eFuse системной и радарной ветвей": (
        "24 В nominal, допустимый диапазон 18...32 В, источник не менее 5 А; "
        "входная защита TPS26630, обратная полярность на CSD19537Q3, "
        "преобразователь LM76005 формирует V12_SYS"
    ),
    "Подключить Tag-Connect к J10, затем программатор. VREF на контакте 1 является выходом 3,3 В платы и не должен питаться от программатора. Подать 24 В с ограничением тока.": (
        "Подключить Tag-Connect к J10, затем программатор. VREF на контакте 1 является выходом 3,3 В платы и не должен питаться от программатора. Подать 24 В с ограничением тока; допустимый диапазон входа 18...32 В."
    ),
    "Лабораторный источник питания | 0-15 В, не менее 5 А": (
        "Лабораторный источник питания | 0-36 В, не менее 5 А"
    ),
}


EXACT_REPLACEMENTS = {
    "83": "105",
    "483": "607",
    "1776": "1874",
    "241": "200",
    "60": "21",
    "2f50a0c6aa4ea9c66c26200669f5fb8c73882021": (
        "фиксируется в MANIFEST финального архива"
    ),
    "90 × 70 мм, 4 слоя, 83 компонента, 483 контактные площадки": (
        "90 × 70 мм, 4 слоя, 105 компонентов, 607 контактных площадок"
    ),
    "1776 дорожек, 241 переходное отверстие, 60 заливок": (
        "1874 дорожки, 200 переходных отверстий, 21 заливка"
    ),
    "Первичный сводный выпуск комплекта EVT": (
        "Выпуск комплекта 24 В с актуализированными материалами Altium"
    ),
    "Аудит репозитория и выпуск платы Pilot R1": (
        "Native audit, DRC и equivalence актуальной платы 24 В"
    ),
    (
        "Вход 12 В поступает через J1. Системная и радарная ветви защищены "
        "независимыми eFuse TPS259470A. Преобразователь U5 формирует 3,3 В "
        "для МК, IMU, CAN и логики. U9 формирует 5 В для внешнего GNSS. "
        "Расчетная способность источника стенда составляет не менее 5 А."
    ): (
        "Вход 24 В поступает через J1. Допустимый диапазон составляет 18...32 В. "
        "TPS26630 ограничивает бросок тока и контролирует UVLO/OVP, а CSD19537Q3 "
        "защищает от обратной полярности. LM76005 формирует промежуточную шину "
        "V12_SYS. От нее U5 формирует 3,3 В, U9 формирует 5 В для внешнего GNSS, "
        "а U7 защищает отдельную ветвь RADAR_12V. Источник стенда должен выдавать "
        "24 В и не менее 5 А с регулируемым ограничением тока."
    ),
    "Питание | 12 В, ограничение тока, измерение напряжений/токов": (
        "Питание | 24 В nominal, диапазон 18...32 В, ограничение тока, измерение напряжений и токов"
    ),
    "Источник 24 В подключается к J1.": (
        "Источник 24 В подключается к J1; допустимый диапазон входа 18...32 В."
    ),
    "Источник 24 В установить в режим ограничения тока.": (
        "Источник 24 В установить в режим ограничения тока. Для первого включения установить предел 0,50 А при отключенных внешних нагрузках."
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def story_paragraphs(document: Document):
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
                for nested in cell.tables:
                    for nested_row in nested.rows:
                        for nested_cell in nested_row.cells:
                            yield from nested_cell.paragraphs
    for section in document.sections:
        for story in (section.header, section.footer):
            yield from story.paragraphs
            for table in story.tables:
                for row in table.rows:
                    for cell in row.cells:
                        yield from cell.paragraphs


def replace_text(document: Document) -> None:
    for paragraph in story_paragraphs(document):
        original = paragraph.text
        if not original:
            continue
        updated = EXACT_REPLACEMENTS.get(original, original)
        for old, new in REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != original:
            paragraph.text = updated


def format_document(source_bytes: bytes) -> tuple[bytes, dict]:
    document = Document(io.BytesIO(source_bytes))
    replace_text(document)
    intermediate = io.BytesIO()
    document.save(intermediate)
    return transform_docx(intermediate.getvalue(), version=VERSION)


def write_zip(source_root: Path, archive: Path, include: set[Path] | None = None) -> None:
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(source_root.rglob("*"), key=lambda item: item.relative_to(source_root).as_posix()):
            if not path.is_file():
                continue
            relative = path.relative_to(source_root)
            if include is not None and relative not in include:
                continue
            bundle.write(path, (Path(source_root.name) / relative).as_posix())


def build() -> dict:
    if not SOURCE.is_dir() or not ALGORITHM.is_file():
        raise FileNotFoundError("Required source document package is absent")

    algorithm_bytes = ALGORITHM.read_bytes()
    reports: dict[str, dict] = {}
    TARGET.mkdir(parents=True, exist_ok=True)

    for source in sorted(SOURCE.rglob("*.docx")):
        relative = source.relative_to(SOURCE)
        target_relative = Path(str(relative).replace("v1.1.1", f"v{VERSION}"))
        target = TARGET / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload, report = format_document(source.read_bytes())
        target.write_bytes(payload)
        reports[target_relative.as_posix()] = report["audit"]

    algorithm_payload, algorithm_report = format_document(algorithm_bytes)
    ALGORITHM.write_bytes(algorithm_payload)
    reports[ALGORITHM.relative_to(TARGET).as_posix()] = algorithm_report["audit"]

    failures = {name: report for name, report in reports.items() if report["status"] != "PASS"}
    if failures:
        raise RuntimeError(f"DOCX audit failed: {failures}")

    (TARGET / "VERSION.txt").write_text(
        f"EVT ГСН document set\nVersion: {VERSION}\nDate: {DATE}\n"
        "Power input: 24 V nominal, 18...32 V allowed\n"
        "Production authority: NOT_AUTHORIZED\n",
        encoding="utf-8-sig",
        newline="\n",
    )
    (TARGET / "Проверка_оформления.json").write_text(
        json.dumps(
            {
                "schema": "EVT-DOCX-STYLE-AUDIT-002",
                "version": VERSION,
                "status": "PASS",
                "requirements": {
                    "body_and_heading_font": "Times New Roman 14 pt",
                    "table_font": "Times New Roman 12 pt",
                    "header_footer_font": "Times New Roman 12 pt",
                    "header_footer_alignment": "CENTER_NO_INDENT",
                    "line_spacing": "single",
                    "first_line_indent_outside_tables_cm": 1.25,
                    "first_line_indent_in_tables_cm": 0,
                    "heading_first_line_indent_cm": 1.25,
                    "paragraph_spacing_before_after_pt": 0,
                    "heading_color": "black",
                    "heading_lines": "forbidden",
                    "en_and_em_dash": "forbidden",
                    "numbered_subsection_period": "required",
                },
                "documents": reports,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest_rows = []
    for path in sorted(TARGET.rglob("*"), key=lambda item: item.relative_to(TARGET).as_posix()):
        if not path.is_file() or path.name in {"MANIFEST.json", "SHA256SUMS.txt"}:
            continue
        manifest_rows.append(
            {
                "path": path.relative_to(TARGET).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": "EVT-GSN-DOCUMENT-SET-002",
        "version": VERSION,
        "date": DATE,
        "power_input": "24V_NOMINAL_18_32V",
        "production_authority": "NOT_AUTHORIZED",
        "file_count": len(manifest_rows),
        "files": manifest_rows,
    }
    (TARGET / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (TARGET / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in manifest_rows),
        encoding="utf-8",
        newline="\n",
    )

    write_zip(TARGET, ARCHIVE)
    method_relatives = {
        path.relative_to(TARGET)
        for pattern in (
            "08_Контроль_и_приемка/*.docx",
            "10_Отчетные_материалы/*.docx",
            "Проверка_оформления.json",
            "VERSION.txt",
        )
        for path in TARGET.glob(pattern)
    }
    write_zip(TARGET, METHODS_ARCHIVE, include=method_relatives)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    download_document = DOWNLOADS / f"EVT_GSN_documents_v{VERSION}.zip"
    download_methods = DOWNLOADS / f"EVT_GSN_methods_and_reports_v{VERSION}.zip"
    shutil.copy2(ARCHIVE, download_document)
    shutil.copy2(METHODS_ARCHIVE, download_methods)

    return {
        "schema": "EVT-GSN-DOCUMENT-RELEASE-QA-002",
        "version": VERSION,
        "status": "PASS",
        "document_count": len(reports),
        "archive": ARCHIVE.relative_to(ROOT).as_posix(),
        "archive_sha256": sha256(ARCHIVE),
        "methods_archive": METHODS_ARCHIVE.relative_to(ROOT).as_posix(),
        "methods_archive_sha256": sha256(METHODS_ARCHIVE),
        "production_authority": "NOT_AUTHORIZED",
    }


if __name__ == "__main__":
    result = build()
    report = RELEASE / "EVT_ГСН_документы_v1.2.0_2026-11-02_QA.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
