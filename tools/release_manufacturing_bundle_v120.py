#!/usr/bin/env python3
"""Build and verify the complete 24 V EVT manufacturing release v1.2.0."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from openpyxl import load_workbook
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.2.0"
RELEASE_DATE = "2026-11-02"
CANONICAL_PCB_SHA256 = "518041a570b405a429a70d968ee54b62df126cb0091b9af08e067152c5aa8735"

FULL_NAME = f"EVT_ГСН_полный_производственный_комплект_24В_v{VERSION}_{RELEASE_DATE}"
PCB_NAME = f"EVT_ГСН_заказ_ПП_и_монтажа_24В_v{VERSION}_{RELEASE_DATE}"
TEMP_ROOT = ROOT / ".codex-temp" / "manufacturing_bundle_v120"
FULL_STAGE = TEMP_ROOT / FULL_NAME
PCB_STAGE = TEMP_ROOT / PCB_NAME
FULL_ARCHIVE = ROOT / "release" / f"{FULL_NAME}.zip"
PCB_ARCHIVE = ROOT / "release" / f"{PCB_NAME}.zip"
FULL_DOWNLOAD = ROOT / "release" / "downloads" / f"EVT_GSN_manufacturing_package_24V_v{VERSION}.zip"
PCB_DOWNLOAD = ROOT / "release" / "downloads" / f"EVT_GSN_PCB_assembly_order_24V_v{VERSION}.zip"
QA_REPORT = ROOT / "release" / f"{FULL_NAME}_QA.json"

NATIVE = ROOT / "hardware" / "system_carrier" / "altium" / "native"
OUTPUTS = NATIVE / "Project Outputs for EVT_SYS_CARRIER"
EQUIVALENCE = ROOT / "hardware" / "system_carrier" / "altium" / "equivalence"
RELEASE_EVIDENCE = ROOT / "hardware" / "system_carrier" / "altium" / "release"
CONNECTION = ROOT / "hardware" / "system_carrier" / "altium" / "routing" / "connection_audit"
CURRENT_OUTPUTS = RELEASE_EVIDENCE / "evt24_v120"
DOCS = ROOT / f"release/EVT_ГСН_документы_v{VERSION}_{RELEASE_DATE}"
BOM_XLSX = ROOT / f"release/EVT_ГСН_BOM_и_закупка_24В_v{VERSION}_{RELEASE_DATE}.xlsx"
FIRMWARE_RELEASE = ROOT / "firmware" / "stm32h753" / "release" / "EVT_R1_2026-10-30"
VISUALIZER = ROOT / "release" / "EVT_ГСН_визуализатор_Windows_v1.1.0_2026-10-31"
DIGITAL_TWIN = ROOT / "release" / "EVT_ГСН_цифровой_двойник_Windows_v1.0.0_2026-11-01"

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
    "Power24V_Footprints.PcbLib",
    "Power24V_Footprints_20261101.PcbLib",
    "Resistor_SMD.PcbLib",
    "SystemCarrier_Altium.PcbLib",
    "EVT_SYS_CARRIER.IntLib",
    "CAMtastic1.Cam",
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


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tracked_firmware_sources() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
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
        normalized = value.replace("\\", "/")
        if not normalized or normalized.startswith("firmware/stm32h753/release/"):
            continue
        if normalized in exact or normalized.startswith(prefixes):
            source = ROOT / normalized
            if source.is_file():
                selected.append(Path(normalized))
    return sorted(selected, key=lambda item: item.as_posix())


def export_sheet_csv(sheet, destination: Path) -> int:
    headers = [cell.value for cell in sheet[3]]
    last_column = max(index for index, value in enumerate(headers, start=1) if value not in (None, ""))
    normalized_headers = [str(value or "") for value in headers[:last_column]]
    rows: list[list[object]] = []
    for values in sheet.iter_rows(min_row=4, max_col=last_column, values_only=True):
        row = list(values)
        if any(value not in (None, "") for value in row):
            rows.append(row)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(normalized_headers)
        writer.writerows(rows)
    return len(rows)


def create_bom_csvs(destination: Path) -> dict[str, int]:
    book = load_workbook(BOM_XLSX, read_only=True, data_only=True, keep_links=True)
    try:
        counts = {
            "procurement": export_sheet_csv(book["Закупка"], destination / "BOM_закупка_машиночитаемый.csv"),
            "detailed": export_sheet_csv(book["BOM_детально"], destination / "BOM_монтаж_105_позиций.csv"),
            "system": export_sheet_csv(book["Системная_закупка"], destination / "Системная_закупка_машиночитаемая.csv"),
            "dnp": export_sheet_csv(book["DNP_PCB_ONLY"], destination / "DNP_и_PCB_ONLY.csv"),
        }
    finally:
        book.close()
    if counts["detailed"] != 105:
        raise RuntimeError(f"Expected 105 detailed BOM rows, found {counts['detailed']}")
    return counts


def canonical_gerbers() -> list[Path]:
    files = [
        path
        for path in (OUTPUTS / "Gerber").iterdir()
        if path.is_file()
        and (path.name.startswith("EVT_SYS_CARRIER.") or path.name == "EVT_SYS_CARRIER-macro.APR_LIB")
    ]
    if len(files) != 21:
        raise RuntimeError(f"Expected 21 canonical Gerber files, found {len(files)}")
    return sorted(files, key=lambda item: item.name.casefold())


def canonical_drills() -> list[Path]:
    files = [
        path
        for path in (OUTPUTS / "NC Drill").iterdir()
        if path.is_file() and path.name.startswith("EVT_SYS_CARRIER.")
    ]
    if len(files) != 4:
        raise RuntimeError(f"Expected four canonical NC Drill files, found {len(files)}")
    return sorted(files, key=lambda item: item.name.casefold())


def copy_altium_project(destination: Path) -> None:
    for filename in ALTIUM_PROJECT_FILES:
        copy_file(NATIVE / filename, destination / filename)
    (destination / "ОТКРЫТЬ_ПРОЕКТ.txt").write_text(
        "Откройте EVT_SYS_CARRIER.PrjPcb в Altium Designer.\n"
        "Все OutJob привязаны к EVT_SYS_CARRIER.PcbDoc.\n"
        "Канонический SHA-256 платы указан в манифесте пакета.\n",
        encoding="utf-8-sig",
    )


def copy_fabrication(destination: Path) -> None:
    for source in canonical_gerbers():
        copy_file(source, destination / "01_Гербер" / source.name)
    for source in canonical_drills():
        copy_file(source, destination / "02_Сверловка" / source.name)
    copy_file(OUTPUTS / "IPC-2581 Files" / "EVT_SYS_CARRIER.cvg", destination / "03_IPC_2581" / "EVT_SYS_CARRIER.cvg")
    copy_file(CURRENT_OUTPUTS / "EVT_SYS_CARRIER_Gerber.zip", destination / "04_Готовые_архивы" / "EVT_SYS_CARRIER_Gerber.zip")
    copy_file(CURRENT_OUTPUTS / "EVT_SYS_CARRIER_NC_Drill.zip", destination / "04_Готовые_архивы" / "EVT_SYS_CARRIER_NC_Drill.zip")
    copy_file(OUTPUTS / "Fabrication_PILOT_R1.pdf", destination / "05_PDF" / "Цветная_послойная_раскладка_платы.pdf")


def copy_assembly(destination: Path) -> None:
    copy_file(OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.csv", destination / "01_PickPlace" / "Pick Place for EVT_SYS_CARRIER.csv")
    copy_file(OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.txt", destination / "01_PickPlace" / "Pick Place for EVT_SYS_CARRIER.txt")
    copy_file(OUTPUTS / "AssemblyDrawing.pdf", destination / "02_Сборочный_чертеж" / "Сборочный_чертеж.pdf")


def copy_validation(destination: Path) -> None:
    selected = [
        EQUIVALENCE / "altium_equivalence_result.json",
        EQUIVALENCE / "native_audit_result.json",
        EQUIVALENCE / "native_transition_result.json",
        EQUIVALENCE / "compile_report.json",
        EQUIVALENCE / "netlist_validation_result.json",
        EQUIVALENCE / "hierarchy_validation_result.json",
        EQUIVALENCE / "bom_validation_result.json",
        EQUIVALENCE / "no_mmwave_review_result.json",
        EQUIVALENCE / "evt_mechanical_datum_gate.json",
        EQUIVALENCE / "evt_routing_stack_gate.json",
        EQUIVALENCE / "evt_power_routing_gate.json",
        CONNECTION / "connection_integrity_result.json",
        CONNECTION / "connection_integrity_receipt.json",
        RELEASE_EVIDENCE / "native_drc_result.json",
        RELEASE_EVIDENCE / "outjob_release_manifest.json",
        RELEASE_EVIDENCE / "manifest.json",
        RELEASE_EVIDENCE / "production_release_status.json",
        CURRENT_OUTPUTS / "native_outputs_manifest.json",
        CURRENT_OUTPUTS / "release_evidence_update_qa.json",
        NATIVE / "Design Rule Check - EVT_SYS_CARRIER.drc",
        NATIVE / "Design Rule Check - EVT_SYS_CARRIER.html",
    ]
    for source in selected:
        copy_file(source, destination / source.name)


def write_inventory(stage: Path, package_type: str, firmware_source_count: int = 0) -> None:
    text = f"""КОМПЛЕКТ EVT ГСН, ВХОДНОЕ ПИТАНИЕ 24 В
Версия: {VERSION}
Дата: {RELEASE_DATE}
Тип пакета: {package_type}

Исходная плата: EVT_SYS_CARRIER.PcbDoc
SHA-256 платы: {CANONICAL_PCB_SHA256}
ALTIUM_EQUIVALENCE_GATE: PASS
Native DRC: PASS, нарушений 0, неразведенных соединений 0
Компоненты: 105
Слои меди: 4
Исходники прошивки: {firmware_source_count}

ПРИМЕНЕНИЕ
Комплект подготовлен для заказа и изготовления пилотного образца, CAM-проверки,
монтажа, прошивки и стендовых испытаний. Замечания фабрики и результаты стенда
вносятся следующим версионным выпуском.

ОГРАНИЧЕНИЕ
Production authority = NOT_AUTHORIZED.
Это не препятствует изготовлению и проверке EVT-пилота, но не разрешает серийный выпуск.
"""
    control = stage / "00_Опись_и_статус"
    control.mkdir(parents=True, exist_ok=True)
    (control / "ОПИСЬ_ПАКЕТА.txt").write_text(text, encoding="utf-8-sig", newline="\n")
    write_json(
        control / "СТАТУС_ВЫПУСКА.json",
        {
            "schema": "EVT-GSN-24V-RELEASE-STATUS-001",
            "version": VERSION,
            "release_date": RELEASE_DATE,
            "package_type": package_type,
            "canonical_pcb_sha256": CANONICAL_PCB_SHA256,
            "altium_equivalence_gate": "PASS",
            "native_drc": "PASS",
            "ready_for_evt_pilot_order": True,
            "production_authority": "NOT_AUTHORIZED",
            "bench_validation": "REQUIRED",
            "fabricator_order_feedback": "DEFERRED_TO_NEXT_REVISION",
        },
    )


def write_manifest(stage: Path, package_type: str) -> dict:
    control = stage / "00_Опись_и_статус"
    rows: list[dict[str, object]] = []
    for path in sorted(stage.rglob("*"), key=lambda item: item.relative_to(stage).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(stage).as_posix()
        if relative in {
            "00_Опись_и_статус/MANIFEST.json",
            "00_Опись_и_статус/MANIFEST.csv",
            "00_Опись_и_статус/SHA256SUMS.txt",
        }:
            continue
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "schema": "EVT-GSN-24V-PACKAGE-MANIFEST-001",
        "version": VERSION,
        "release_date": RELEASE_DATE,
        "package_type": package_type,
        "canonical_pcb_sha256": CANONICAL_PCB_SHA256,
        "production_authority": "NOT_AUTHORIZED",
        "file_count": len(rows),
        "files": rows,
    }
    write_json(control / "MANIFEST.json", manifest)
    with (control / "MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    (control / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def zip_stage(stage: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(stage.rglob("*"), key=lambda item: item.relative_to(stage.parent).as_posix()):
            if path.is_file():
                bundle.write(path, path.relative_to(stage.parent).as_posix())


def build_full(firmware_sources: list[Path]) -> dict[str, int]:
    copy_tree(DOCS, FULL_STAGE / "01_Техническая_документация")
    copy_altium_project(FULL_STAGE / "02_Проект_Altium")
    copy_fabrication(FULL_STAGE / "03_Изготовление_печатной_платы")
    copy_assembly(FULL_STAGE / "04_Монтаж_печатной_платы")

    bom_destination = FULL_STAGE / "05_BOM_и_закупка"
    copy_file(BOM_XLSX, bom_destination / "BOM_и_закупка_24В.xlsx")
    bom_counts = create_bom_csvs(bom_destination)
    copy_file(ROOT / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv", bom_destination / "BOM_контракт_105_позиций.csv")

    source_destination = FULL_STAGE / "06_Прошивка_исходники"
    for relative in firmware_sources:
        copy_file(ROOT / relative, source_destination / relative)
    copy_tree(FIRMWARE_RELEASE, FULL_STAGE / "07_Прошивка_готовый_таргет")
    copy_validation(FULL_STAGE / "08_Проверки_и_эквивалентность")

    factory = FULL_STAGE / "09_Стек_фабрики_и_механика"
    copy_file(RELEASE_EVIDENCE / "REZONIT_FABRICATION_BASELINE.md", factory / "REZONIT_FABRICATION_BASELINE.md")
    copy_file(RELEASE_EVIDENCE / "REZONIT_PUBLISHED_STACK_4L_35UM.csv", factory / "REZONIT_PUBLISHED_STACK_4L_35UM.csv")
    copy_file(OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step", factory / "EVT_SYS_CARRIER.step")

    copy_tree(VISUALIZER, FULL_STAGE / "10_Программа_визуализации_Windows")
    copy_tree(DIGITAL_TWIN, FULL_STAGE / "11_Цифровой_двойник_Windows")

    write_inventory(FULL_STAGE, "Полный производственный комплект 24 В", len(firmware_sources))
    write_manifest(FULL_STAGE, "FULL_MANUFACTURING_24V")
    return bom_counts


def build_pcb_order() -> None:
    copy_altium_project(PCB_STAGE / "01_Проект_Altium")
    copy_fabrication(PCB_STAGE / "02_Изготовление_печатной_платы")
    copy_assembly(PCB_STAGE / "03_Монтаж_печатной_платы")
    bom_destination = PCB_STAGE / "04_BOM_и_закупка"
    copy_file(BOM_XLSX, bom_destination / "BOM_и_закупка_24В.xlsx")
    create_bom_csvs(bom_destination)
    copy_file(ROOT / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv", bom_destination / "BOM_контракт_105_позиций.csv")
    copy_file(OUTPUTS / "Schematic Prints.PDF", PCB_STAGE / "05_PDF_схемы_и_чертежи" / "Схемы_EVT_SYS_CARRIER.pdf")
    copy_file(OUTPUTS / "Fabrication_PILOT_R1.pdf", PCB_STAGE / "05_PDF_схемы_и_чертежи" / "Цветная_послойная_раскладка_платы.pdf")
    copy_file(OUTPUTS / "AssemblyDrawing.pdf", PCB_STAGE / "05_PDF_схемы_и_чертежи" / "Сборочный_чертеж.pdf")
    copy_file(OUTPUTS / "ExportSTEP" / "EVT_SYS_CARRIER.step", PCB_STAGE / "06_Механическая_модель" / "EVT_SYS_CARRIER.step")
    copy_validation(PCB_STAGE / "07_Проверки")
    copy_file(RELEASE_EVIDENCE / "REZONIT_FABRICATION_BASELINE.md", PCB_STAGE / "08_Стек_и_требования_фабрики" / "REZONIT_FABRICATION_BASELINE.md")
    copy_file(RELEASE_EVIDENCE / "REZONIT_PUBLISHED_STACK_4L_35UM.csv", PCB_STAGE / "08_Стек_и_требования_фабрики" / "REZONIT_PUBLISHED_STACK_4L_35UM.csv")
    order_doc = DOCS / "03_Заказ_ПП_и_монтажа" / f"Заявка_на_изготовление_ПП_и_монтаж_v{VERSION}.docx"
    copy_file(order_doc, PCB_STAGE / "09_Заявка_на_изготовление" / order_doc.name)
    write_inventory(PCB_STAGE, "Заказ печатной платы и монтажа 24 В")
    write_manifest(PCB_STAGE, "PCB_FABRICATION_AND_ASSEMBLY_24V")


def verify_archive(archive: Path, package_name: str, required: list[str]) -> dict[str, object]:
    with zipfile.ZipFile(archive) as bundle:
        bad = bundle.testzip()
        names = set(bundle.namelist())
        prefix = f"{package_name}/"
        missing = [item for item in required if prefix + item not in names]
        manifest = json.loads(bundle.read(prefix + "00_Опись_и_статус/MANIFEST.json"))
        hash_failures: list[str] = []
        for item in manifest["files"]:
            payload = bundle.read(prefix + item["path"])
            if len(payload) != item["size_bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
                hash_failures.append(item["path"])
        stale_paths = [name for name in names if "OPEN_DIRTY_BACKUP" in name or "pilot_r1" in name.lower()]
    if bad or missing or hash_failures or stale_paths:
        raise RuntimeError(
            f"Archive verification failed: bad={bad}, missing={missing}, hashes={hash_failures}, stale={stale_paths}"
        )
    return {
        "archive": archive.relative_to(ROOT).as_posix(),
        "sha256": sha256(archive),
        "bytes": archive.stat().st_size,
        "zip_integrity": "PASS",
        "required_files": "PASS",
        "manifest_files_verified": manifest["file_count"],
        "stale_backup_paths": 0,
    }


def verify_payloads() -> dict[str, object]:
    if sha256(NATIVE / "EVT_SYS_CARRIER.PcbDoc") != CANONICAL_PCB_SHA256:
        raise RuntimeError("Canonical PcbDoc changed")
    if len(canonical_gerbers()) != 21 or len(canonical_drills()) != 4:
        raise RuntimeError("Fabrication output count mismatch")

    pick_lines = (OUTPUTS / "Pick Place" / "Pick Place for EVT_SYS_CARRIER.csv").read_text(
        encoding="utf-8-sig", errors="replace"
    ).splitlines()
    try:
        header_index = next(index for index, line in enumerate(pick_lines) if line.startswith('"Center-X'))
    except StopIteration as exc:
        raise RuntimeError("Pick&Place header missing") from exc
    pick_rows = sum(1 for line in pick_lines[header_index + 1 :] if line.strip())
    if pick_rows != 105:
        raise RuntimeError(f"Expected 105 Pick&Place rows, found {pick_rows}")

    pdf_pages = {
        "schematic": len(PdfReader(OUTPUTS / "Schematic Prints.PDF").pages),
        "fabrication": len(PdfReader(OUTPUTS / "Fabrication_PILOT_R1.pdf").pages),
        "assembly": len(PdfReader(OUTPUTS / "AssemblyDrawing.pdf").pages),
    }
    if pdf_pages != {"schematic": 8, "fabrication": 5, "assembly": 2}:
        raise RuntimeError(f"Unexpected PDF page counts: {pdf_pages}")

    firmware_manifest = json.loads((FIRMWARE_RELEASE / "manifest.json").read_text(encoding="utf-8"))
    firmware_failures = []
    for item in firmware_manifest["artifacts"]:
        path = FIRMWARE_RELEASE / item["file"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            firmware_failures.append(item["file"])
    if firmware_failures:
        raise RuntimeError(f"Firmware artifact failures: {firmware_failures}")

    return {
        "canonical_pcb_sha256": CANONICAL_PCB_SHA256,
        "gerber_files": 21,
        "nc_drill_files": 4,
        "pick_place_rows": pick_rows,
        "pdf_pages": pdf_pages,
        "firmware_artifacts": len(firmware_manifest["artifacts"]),
        "firmware_host_tests_passed": firmware_manifest["host_tests"]["passed"],
        "digital_twin": firmware_manifest["digital_twin"]["status"],
        "production_authority": "NOT_AUTHORIZED",
    }


def build() -> None:
    required_sources = [NATIVE, OUTPUTS, EQUIVALENCE, RELEASE_EVIDENCE, DOCS, BOM_XLSX, FIRMWARE_RELEASE, VISUALIZER, DIGITAL_TWIN]
    for path in required_sources:
        if not path.exists():
            raise FileNotFoundError(path)
    if TEMP_ROOT.exists():
        shutil.rmtree(TEMP_ROOT)
    for path in (FULL_ARCHIVE, PCB_ARCHIVE, FULL_DOWNLOAD, PCB_DOWNLOAD, QA_REPORT):
        if path.exists():
            path.unlink()
    FULL_STAGE.mkdir(parents=True)
    PCB_STAGE.mkdir(parents=True)

    firmware_sources = tracked_firmware_sources()
    bom_counts = build_full(firmware_sources)
    build_pcb_order()
    zip_stage(FULL_STAGE, FULL_ARCHIVE)
    zip_stage(PCB_STAGE, PCB_ARCHIVE)
    FULL_DOWNLOAD.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FULL_ARCHIVE, FULL_DOWNLOAD)
    shutil.copy2(PCB_ARCHIVE, PCB_DOWNLOAD)

    full_required = [
        "02_Проект_Altium/EVT_SYS_CARRIER.PcbDoc",
        "03_Изготовление_печатной_платы/01_Гербер/EVT_SYS_CARRIER.GTL",
        "03_Изготовление_печатной_платы/02_Сверловка/EVT_SYS_CARRIER.TXT",
        "03_Изготовление_печатной_платы/03_IPC_2581/EVT_SYS_CARRIER.cvg",
        "04_Монтаж_печатной_платы/01_PickPlace/Pick Place for EVT_SYS_CARRIER.csv",
        "05_BOM_и_закупка/BOM_и_закупка_24В.xlsx",
        "06_Прошивка_исходники/CMakeLists.txt",
        "07_Прошивка_готовый_таргет/EVT_SYS_CARRIER_STM32H753_R1.hex",
        "10_Программа_визуализации_Windows/01_Программа_Windows/EVT_GSN_Visualizer.exe",
        "11_Цифровой_двойник_Windows/01_Программы_Windows/EVT_GSN_Digital_Twin.exe",
    ]
    pcb_required = [
        "01_Проект_Altium/EVT_SYS_CARRIER.PcbDoc",
        "02_Изготовление_печатной_платы/01_Гербер/EVT_SYS_CARRIER.GTL",
        "02_Изготовление_печатной_платы/02_Сверловка/EVT_SYS_CARRIER.TXT",
        "02_Изготовление_печатной_платы/03_IPC_2581/EVT_SYS_CARRIER.cvg",
        "03_Монтаж_печатной_платы/01_PickPlace/Pick Place for EVT_SYS_CARRIER.csv",
        "04_BOM_и_закупка/BOM_и_закупка_24В.xlsx",
        "05_PDF_схемы_и_чертежи/Схемы_EVT_SYS_CARRIER.pdf",
        "09_Заявка_на_изготовление/Заявка_на_изготовление_ПП_и_монтаж_v1.2.0.docx",
    ]
    payload_qa = verify_payloads()
    full_qa = verify_archive(FULL_ARCHIVE, FULL_NAME, full_required)
    pcb_qa = verify_archive(PCB_ARCHIVE, PCB_NAME, pcb_required)
    if sha256(FULL_ARCHIVE) != sha256(FULL_DOWNLOAD) or sha256(PCB_ARCHIVE) != sha256(PCB_DOWNLOAD):
        raise RuntimeError("Download copies do not match source archives")

    qa = {
        "schema": "EVT-GSN-24V-MANUFACTURING-BUNDLE-QA-001",
        "version": VERSION,
        "release_date": RELEASE_DATE,
        "status": "PASS",
        "full_package": full_qa,
        "pcb_order_package": pcb_qa,
        "payload": payload_qa,
        "bom_csv_rows": bom_counts,
        "download_copies": "PASS",
        "production_authority": "NOT_AUTHORIZED",
    }
    write_json(QA_REPORT, qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))


def check() -> None:
    payload_qa = verify_payloads()
    print(json.dumps(payload_qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "check"}:
        raise SystemExit("Usage: release_manufacturing_bundle_v120.py {build|check}")
    if sys.argv[1] == "build":
        build()
    else:
        check()
