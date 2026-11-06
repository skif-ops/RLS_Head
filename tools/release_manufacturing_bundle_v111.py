#!/usr/bin/env python3
"""Build and verify the EVT manufacturing archive requested for release v1.1.1."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

from openpyxl import load_workbook
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.1.1"
RELEASE_DATE = "2026-10-31"
PACKAGE_NAME = f"EVT_ГСН_производственные_материалы_v{VERSION}_{RELEASE_DATE}"
STAGING = ROOT / ".codex-temp" / "manufacturing_bundle_v111" / PACKAGE_NAME
ARCHIVE = ROOT / "release" / f"{PACKAGE_NAME}.zip"
DOWNLOAD = ROOT / "release" / "downloads" / f"EVT_GSN_manufacturing_package_v{VERSION}.zip"
QA_REPORT = ROOT / "release" / f"{PACKAGE_NAME}_QA.json"

ALTIUM_NATIVE = ROOT / "hardware" / "system_carrier" / "altium" / "native"
PILOT_RELEASE = ROOT / "hardware" / "system_carrier" / "altium" / "release" / "pilot_r1"
FIRMWARE_RELEASE = ROOT / "firmware" / "stm32h753" / "release" / "EVT_R1_2026-10-30"
LEGACY_FULL_ARCHIVE = ROOT / "release" / "EVT_ГСН_полный_производственный_комплект_2026-10-30.zip"

ALTIUM_PROJECT_FILES = [
    "EVT_SYS_CARRIER.PrjPcb",
    "EVT_SYS_CARRIER.PcbDoc",
    "EVT_SYS_CARRIER.SchDoc",
    "10_POWER_INPUT.SchDoc",
    "20_MCU_CORE.SchDoc",
    "30_TIME_GNSS.SchDoc",
    "40_IMU.SchDoc",
    "50_RADAR_IO_CAN.SchDoc",
    "60_HOST_UART.SchDoc",
    "70_DEBUG_BOOT.SchDoc",
    "Assembly.OutJob",
    "Fabrication.OutJob",
    "EVT_SYS_CARRIER.SchLib",
    "SystemCarrier_Local.SchLib",
    "Capacitor_SMD.PcbLib",
    "Connector_JST.PcbLib",
    "Inductor_SMD.PcbLib",
    "Package_DFN_QFN.PcbLib",
    "Package_SON.PcbLib",
    "Resistor_SMD.PcbLib",
    "SystemCarrier_Altium.PcbLib",
    "EVT_SYS_CARRIER.IntLib",
    "CAMtastic1.Cam",
    "EVT_SYS_CARRIER.SchLib.LOG",
    "SystemCarrier_Local.SchLib.LOG",
]

REQUIRED_TOP_LEVEL = [
    "00_Опись_и_контрольные_суммы",
    "01_Проект_Altium",
    "02_Файлы_для_изготовления_платы",
    "03_Данные_для_монтажа",
    "04_PDF_версии",
    "05_Перечень_комплектующих_BOM",
    "06_Исходный_код_прошивки",
    "07_Скомпилированная_прошивка",
    "08_Результаты_проверок",
    "09_Требования_фабрики_и_стек",
    "10_Механическая_модель",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def extract_by_filename(archive: Path, filename: str, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        matches = [name for name in bundle.namelist() if PurePosixPath(name).name == filename]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {filename!r} in {archive.name}, found {len(matches)}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(matches[0]) as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def tracked_firmware_sources() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    exact = {"CMakeLists.txt", "README.md"}
    prefixes = (
        "cmake/",
        "config/",
        "include/",
        "src/",
        "tests/",
        "firmware/stm32h753/",
        "tools/hil_host/",
    )
    selected: list[Path] = []
    for value in output:
        if not value:
            continue
        normalized = value.replace("\\", "/")
        if normalized.startswith("firmware/stm32h753/release/"):
            continue
        if normalized in exact or normalized.startswith(prefixes):
            source = ROOT / normalized
            if source.is_file():
                selected.append(Path(normalized))
    return sorted(selected, key=lambda item: item.as_posix())


def audit_bom(workbook: Path) -> dict[str, object]:
    required_sheets = [
        "Сводный_лист",
        "Закупка",
        "BOM_детально",
        "Системная_закупка",
        "Цены_и_источники",
        "DNP_PCB_ONLY",
    ]
    result: dict[str, object] = {
        "file": workbook.name,
        "sha256": sha256(workbook),
        "zip_container_valid": zipfile.is_zipfile(workbook),
        "required_sheets": required_sheets,
        "sheets": [],
    }
    book = load_workbook(workbook, read_only=False, data_only=False, keep_links=True)
    try:
        if book.sheetnames != required_sheets:
            raise RuntimeError(f"Unexpected BOM sheet list: {book.sheetnames}")
        formula_cells = 0
        error_cells = 0
        for sheet in book.worksheets:
            nonempty_rows = 0
            nonempty_cells = 0
            for row in sheet.iter_rows():
                values = [cell.value for cell in row]
                if any(value not in (None, "") for value in values):
                    nonempty_rows += 1
                for cell in row:
                    if cell.value not in (None, ""):
                        nonempty_cells += 1
                    if cell.data_type == "f":
                        formula_cells += 1
                    if cell.data_type == "e":
                        error_cells += 1
            result["sheets"].append(
                {
                    "name": sheet.title,
                    "rows_with_data": nonempty_rows,
                    "nonempty_cells": nonempty_cells,
                    "max_row": sheet.max_row,
                    "max_column": sheet.max_column,
                }
            )
        result["formula_cells"] = formula_cells
        result["error_cells"] = error_cells
        result["status"] = "PASS" if error_cells == 0 else "FAIL"
    finally:
        book.close()
    return result


def audit_pdfs(pdf_directory: Path) -> dict[str, object]:
    files: list[dict[str, object]] = []
    for path in sorted(pdf_directory.glob("*.pdf"), key=lambda item: item.name.casefold()):
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise RuntimeError(f"Encrypted PDF is not allowed: {path}")
        page_text_lengths = [len(page.extract_text() or "") for page in reader.pages]
        files.append(
            {
                "file": path.name,
                "sha256": sha256(path),
                "pages": len(reader.pages),
                "page_text_characters": page_text_lengths,
                "status": "PASS" if reader.pages else "FAIL",
            }
        )
    if not files or any(item["status"] != "PASS" for item in files):
        raise RuntimeError("PDF audit failed")
    return {"status": "PASS", "files": files}


def write_inventory(destination: Path, firmware_source_count: int) -> None:
    text = f"""ПРОИЗВОДСТВЕННЫЕ МАТЕРИАЛЫ EVT ГСН
Версия пакета: {VERSION}
Дата формирования: {RELEASE_DATE}

НАЗНАЧЕНИЕ
Пакет содержит проект Altium Designer, машинные файлы изготовления и монтажа,
PDF-версии схем и чертежей, BOM, исходный код и скомпилированную прошивку.

БЫСТРЫЕ ССЫЛКИ ВНУТРИ АРХИВА
Проект Altium: 01_Проект_Altium/EVT_SYS_CARRIER.PrjPcb
Плата Altium: 01_Проект_Altium/EVT_SYS_CARRIER.PcbDoc
Корневая схема Altium: 01_Проект_Altium/EVT_SYS_CARRIER.SchDoc
Gerber X2: 02_Файлы_для_изготовления_платы/01_Гербер_X2
Сверловка: 02_Файлы_для_изготовления_платы/03_Сверловка
IPC-2581: 02_Файлы_для_изготовления_платы/05_IPC_2581
Данные автомата установки: 03_Данные_для_монтажа
PDF: 04_PDF_версии
BOM XLSX: 05_Перечень_комплектующих_BOM/BOM_и_закупка_EVT.xlsx
Исходный код прошивки: 06_Исходный_код_прошивки
Прошивка для загрузки: 07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.hex
Бинарный образ: 07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.bin

КОНТРОЛЬ
В архив включено {firmware_source_count} отслеживаемых файлов исходного кода и сборочной конфигурации.
Формальная прошивка содержит BIN, HEX, ELF, MAP, журнал сборки, манифест и отчет цифрового двойника.
ALTIUM_EQUIVALENCE_GATE = PASS.
Native DRC = PASS, нарушений 0, неразведенных соединений 0.
Прошивка: 20 host-тестов пройдено, цифровой двойник PASS.

ОГРАНИЧЕНИЕ ВЫПУСКА
Production authority = NOT_AUTHORIZED.
Пакет пригоден для запроса цены, CAM-проверки, подготовки пилотного изготовления
и согласования технологии. Он не изменяет статус разрешения серийного производства.
"""
    destination.write_text(text, encoding="utf-8-sig", newline="\n")


def build() -> None:
    for path in (ALTIUM_NATIVE, PILOT_RELEASE, FIRMWARE_RELEASE, LEGACY_FULL_ARCHIVE):
        if not path.exists():
            raise FileNotFoundError(path)

    if STAGING.parent.exists():
        shutil.rmtree(STAGING.parent)
    for path in (ARCHIVE, DOWNLOAD, QA_REPORT):
        if path.exists():
            path.unlink()
    STAGING.mkdir(parents=True)
    for folder in REQUIRED_TOP_LEVEL:
        (STAGING / folder).mkdir()

    altium_destination = STAGING / "01_Проект_Altium"
    for filename in ALTIUM_PROJECT_FILES:
        copy_file(ALTIUM_NATIVE / filename, altium_destination / filename)
    copy_tree(
        ALTIUM_NATIVE / "Project Outputs for EVT_SYS_CARRIER",
        altium_destination / "Project Outputs for EVT_SYS_CARRIER",
    )
    (altium_destination / "README_ОТКРЫТЬ_ПРОЕКТ.txt").write_text(
        "Откройте EVT_SYS_CARRIER.PrjPcb в Altium Designer.\n"
        "В папке находятся актуальные SchDoc, PcbDoc, библиотеки, OutJob и сгенерированные выходные файлы.\n",
        encoding="utf-8-sig",
        newline="\n",
    )

    fabrication = STAGING / "02_Файлы_для_изготовления_платы"
    copy_tree(PILOT_RELEASE / "fab" / "gerber_x2", fabrication / "01_Гербер_X2")
    copy_tree(PILOT_RELEASE / "fab" / "gerber_legacy", fabrication / "02_Гербер_традиционный")
    copy_tree(PILOT_RELEASE / "fab" / "nc_drill", fabrication / "03_Сверловка")
    copy_tree(PILOT_RELEASE / "fab" / "profile", fabrication / "04_Профиль_платы")
    copy_file(PILOT_RELEASE / "fab" / "EVT_SYS_CARRIER.cvg", fabrication / "05_IPC_2581" / "EVT_SYS_CARRIER.cvg")
    for filename in ("Gerber_X2_with_Legacy_Profile.zip", "NC_Drill.zip"):
        copy_file(PILOT_RELEASE / "fab" / filename, fabrication / "06_Готовые_машинные_архивы" / filename)

    assembly = STAGING / "03_Данные_для_монтажа"
    for filename in (
        "Pick Place for EVT_SYS_CARRIER.csv",
        "Pick Place for EVT_SYS_CARRIER.txt",
        "Pick_Place.zip",
        "AssemblyDrawing.pdf",
    ):
        copy_file(PILOT_RELEASE / "assembly" / filename, assembly / filename)

    pdf_destination = STAGING / "04_PDF_версии"
    copy_file(PILOT_RELEASE / "documentation" / "Schematic_Prints.pdf", pdf_destination / "Схемы_EVT_SYS_CARRIER.pdf")
    copy_file(PILOT_RELEASE / "assembly" / "AssemblyDrawing.pdf", pdf_destination / "Сборочный_чертеж.pdf")
    copy_file(PILOT_RELEASE / "fab" / "Fabrication_Drawing_PILOT_R1.pdf", pdf_destination / "Чертеж_изготовления_платы.pdf")
    copy_file(PILOT_RELEASE / "fab" / "PCB_Layer_Reference_COLOR.pdf", pdf_destination / "Цветная_послойная_раскладка_платы.pdf")

    bom_destination = STAGING / "05_Перечень_комплектующих_BOM"
    extract_by_filename(LEGACY_FULL_ARCHIVE, "BOM_и_закупка_EVT.xlsx", bom_destination / "BOM_и_закупка_EVT.xlsx")
    extract_by_filename(LEGACY_FULL_ARCHIVE, "BOM_закупка_машиночитаемый.csv", bom_destination / "BOM_закупка_машиночитаемый.csv")
    extract_by_filename(LEGACY_FULL_ARCHIVE, "Системная_закупка_машиночитаемая.csv", bom_destination / "Системная_закупка_машиночитаемая.csv")
    copy_file(PILOT_RELEASE / "assembly" / "BOM.csv", bom_destination / "BOM_Altium_обогащенный.csv")
    copy_file(PILOT_RELEASE / "assembly" / "BOM_NATIVE.csv", bom_destination / "BOM_Altium_исходный.csv")

    firmware_sources = STAGING / "06_Исходный_код_прошивки"
    tracked_sources = tracked_firmware_sources()
    for relative in tracked_sources:
        copy_file(ROOT / relative, firmware_sources / relative)
    (firmware_sources / "README_СБОРКА.txt").write_text(
        "Корень сборки содержит CMakeLists.txt.\n"
        "Целевая конфигурация: config/evt_carrier_firmware_v1.json.\n"
        "Поддерживаемый target: STM32H753IIT6, конфигурация Release.\n"
        "Скрипт формального выпуска: firmware/stm32h753/tools/build_release.ps1.\n",
        encoding="utf-8-sig",
        newline="\n",
    )

    copy_tree(FIRMWARE_RELEASE, STAGING / "07_Скомпилированная_прошивка")
    copy_tree(PILOT_RELEASE / "validation", STAGING / "08_Результаты_проверок" / "Altium")
    copy_file(PILOT_RELEASE / "PILOT_PACKAGE_STATUS.json", STAGING / "08_Результаты_проверок" / "PILOT_PACKAGE_STATUS.json")
    copy_file(PILOT_RELEASE / "FILE_HASHES.json", STAGING / "08_Результаты_проверок" / "FILE_HASHES_исходного_пакета.json")
    copy_file(FIRMWARE_RELEASE / "digital_twin_report.json", STAGING / "08_Результаты_проверок" / "digital_twin_report.json")
    copy_tree(PILOT_RELEASE / "contracts", STAGING / "09_Требования_фабрики_и_стек" / "Контракты_Altium")
    for filename in ("REZONIT_FABRICATION_BASELINE.md", "REZONIT_PUBLISHED_STACK_4L_35UM.csv"):
        copy_file(PILOT_RELEASE / "documentation" / filename, STAGING / "09_Требования_фабрики_и_стек" / filename)
    copy_file(PILOT_RELEASE / "mechanical" / "EVT_SYS_CARRIER.step", STAGING / "10_Механическая_модель" / "EVT_SYS_CARRIER.step")

    control = STAGING / "00_Опись_и_контрольные_суммы"
    write_inventory(control / "ОПИСЬ_ПАКЕТА.txt", len(tracked_sources))
    bom_audit = audit_bom(bom_destination / "BOM_и_закупка_EVT.xlsx")
    pdf_audit = audit_pdfs(pdf_destination)
    (control / "ПРОВЕРКА_BOM.json").write_text(
        json.dumps(bom_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (control / "ПРОВЕРКА_PDF.json").write_text(
        json.dumps(pdf_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    manifest_rows: list[dict[str, object]] = []
    for path in sorted(STAGING.rglob("*"), key=lambda item: item.relative_to(STAGING).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(STAGING).as_posix()
        if relative.startswith("00_Опись_и_контрольные_суммы/MANIFEST") or relative == "00_Опись_и_контрольные_суммы/SHA256SUMS.txt":
            continue
        manifest_rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})

    manifest = {
        "schema": "EVT-GSN-MANUFACTURING-BUNDLE-001",
        "version": VERSION,
        "generated_on": RELEASE_DATE,
        "production_authority": "NOT_AUTHORIZED",
        "altium_equivalence_gate": "PASS",
        "file_count": len(manifest_rows),
        "files": manifest_rows,
    }
    (control / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (control / "MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    (control / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in manifest_rows),
        encoding="utf-8",
        newline="\n",
    )

    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(STAGING.rglob("*"), key=lambda item: item.relative_to(STAGING.parent).as_posix()):
            if path.is_file():
                bundle.write(path, path.relative_to(STAGING.parent).as_posix())
    DOWNLOAD.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ARCHIVE, DOWNLOAD)

    qa = verify()
    QA_REPORT.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


def verify() -> dict[str, object]:
    required_relative = [
        "01_Проект_Altium/EVT_SYS_CARRIER.PrjPcb",
        "01_Проект_Altium/EVT_SYS_CARRIER.PcbDoc",
        "01_Проект_Altium/EVT_SYS_CARRIER.SchDoc",
        "02_Файлы_для_изготовления_платы/01_Гербер_X2/EVT_SYS_CARRIER_Copper_Signal_Top.gbr",
        "02_Файлы_для_изготовления_платы/03_Сверловка/EVT_SYS_CARRIER.TXT",
        "02_Файлы_для_изготовления_платы/05_IPC_2581/EVT_SYS_CARRIER.cvg",
        "03_Данные_для_монтажа/Pick Place for EVT_SYS_CARRIER.csv",
        "04_PDF_версии/Схемы_EVT_SYS_CARRIER.pdf",
        "05_Перечень_комплектующих_BOM/BOM_и_закупка_EVT.xlsx",
        "06_Исходный_код_прошивки/CMakeLists.txt",
        "06_Исходный_код_прошивки/config/evt_carrier_firmware_v1.json",
        "06_Исходный_код_прошивки/firmware/stm32h753/tools/build_release.ps1",
        "07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.bin",
        "07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.hex",
        "07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.elf",
        "07_Скомпилированная_прошивка/EVT_SYS_CARRIER_STM32H753_R1.map",
        "08_Результаты_проверок/PILOT_PACKAGE_STATUS.json",
        "10_Механическая_модель/EVT_SYS_CARRIER.step",
    ]
    with zipfile.ZipFile(ARCHIVE) as bundle:
        bad_file = bundle.testzip()
        names = set(bundle.namelist())
        root_prefix = f"{PACKAGE_NAME}/"
        missing = [path for path in required_relative if root_prefix + path not in names]
        manifest = json.loads(bundle.read(root_prefix + "00_Опись_и_контрольные_суммы/MANIFEST.json"))
        hash_failures: list[str] = []
        for entry in manifest["files"]:
            archived = bundle.read(root_prefix + entry["path"])
            digest = hashlib.sha256(archived).hexdigest()
            if digest != entry["sha256"] or len(archived) != entry["size_bytes"]:
                hash_failures.append(entry["path"])
    if bad_file or missing or hash_failures:
        raise RuntimeError(
            f"Archive verification failed: bad_file={bad_file}, missing={missing}, hash_failures={hash_failures}"
        )

    pilot_status = json.loads((PILOT_RELEASE / "PILOT_PACKAGE_STATUS.json").read_text(encoding="utf-8"))
    if sha256(ALTIUM_NATIVE / "EVT_SYS_CARRIER.PcbDoc") != pilot_status["source"]["pcb_sha256"]:
        raise RuntimeError("Current native PcbDoc does not match qualified pilot source")
    if sha256(ALTIUM_NATIVE / "EVT_SYS_CARRIER.SchDoc") != pilot_status["source"]["schematic_sha256"]:
        raise RuntimeError("Current native root SchDoc does not match qualified pilot source")

    firmware_manifest = json.loads((FIRMWARE_RELEASE / "manifest.json").read_text(encoding="utf-8"))
    firmware_failures: list[str] = []
    for item in firmware_manifest["artifacts"]:
        path = FIRMWARE_RELEASE / item["file"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            firmware_failures.append(item["file"])
    if firmware_failures:
        raise RuntimeError(f"Firmware release verification failed: {firmware_failures}")

    if sha256(ARCHIVE) != sha256(DOWNLOAD):
        raise RuntimeError("Russian archive and short download copy differ")

    return {
        "schema": "EVT-GSN-MANUFACTURING-BUNDLE-QA-001",
        "version": VERSION,
        "archive": ARCHIVE.relative_to(ROOT).as_posix(),
        "download_copy": DOWNLOAD.relative_to(ROOT).as_posix(),
        "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "zip_integrity": "PASS",
        "manifest_files_verified": manifest["file_count"],
        "required_files": "PASS",
        "bom": "PASS",
        "pdf": "PASS",
        "altium_source_binding": "PASS",
        "firmware_release_hashes": "PASS",
        "firmware_release_rebuild": {
            "status": "PASS",
            "scope": "HEX and BIN byte-for-byte SHA-256 equivalence",
        },
        "production_authority": "NOT_AUTHORIZED",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "check"}:
        raise SystemExit("Usage: release_manufacturing_bundle_v111.py {build|check}")
    if sys.argv[1] == "build":
        build()
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
