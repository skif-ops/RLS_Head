import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "file:///C:/Program%20Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1026-487-0_26.1026.487.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = process.cwd();
const version = "1.2.0";
const releaseDate = "2026-11-02";
const contractPath = path.join(root, "hardware", "system_carrier", "altium", "import_attempts", "power24v_2026-11-01", "package_v4", "contracts", "BOM_SYS_CARRIER_LAYOUT_004.csv");
const nativeBomPath = path.join(root, "hardware", "system_carrier", "altium", "equivalence", "bom_export.csv");
const oldWorkbookPath = path.join(root, "release", "EVT_ГСН_полный_производственный_комплект_2026-10-30", "04_Комплектующие", "BOM_и_закупка_EVT.xlsx");
const outputPath = path.join(root, "release", `EVT_ГСН_BOM_и_закупка_24В_v${version}_${releaseDate}.xlsx`);
const qaPath = path.join(root, "release", `EVT_ГСН_BOM_и_закупка_24В_v${version}_${releaseDate}_QA.json`);
const previewDir = path.join(root, ".codex-temp", "bom_v120_previews");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  const [headers, ...data] = rows.filter((candidate) => candidate.some((value) => value !== ""));
  return data.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function columnName(index) {
  let value = index;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ""))];
}

function disposition(population) {
  if (population === "POPULATE") return "FIT";
  if (population === "DNP_DEFAULT") return "DNP";
  return "PCB_ONLY";
}

function title(sheet, columns, text) {
  const range = sheet.getRange(`A1:${columnName(columns)}1`);
  range.merge();
  range.format.fill = "#1F4E78";
  range.format.font = { name: "Arial", size: 16, bold: true, color: "#FFFFFF" };
  range.format.rowHeight = 30;
  sheet.getRange("A1").values = [[text]];
}

function header(sheet, rangeAddress) {
  const range = sheet.getRange(rangeAddress);
  range.format.fill = "#4472C4";
  range.format.font = { name: "Arial", size: 10, bold: true, color: "#FFFFFF" };
  range.format.wrapText = true;
  range.format.verticalAlignment = "center";
  range.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
  range.format.rowHeight = 34;
}

function body(sheet, rangeAddress) {
  const range = sheet.getRange(rangeAddress);
  range.format.font = { name: "Arial", size: 10, color: "#000000" };
  range.format.verticalAlignment = "center";
  range.format.wrapText = true;
  range.format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
}

function setWidths(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
  });
}

const contractRows = parseCsv(await fs.readFile(contractPath, "utf8"));
const nativeRows = parseCsv(await fs.readFile(nativeBomPath, "utf8"));
if (contractRows.length !== 105 || nativeRows.length !== 105) {
  throw new Error(`Expected 105 BOM rows, got contract=${contractRows.length}, native=${nativeRows.length}`);
}

const nativeByRef = new Map(nativeRows.map((row) => [row.Designator, row.MPN]));
const mismatches = contractRows.filter((row) => nativeByRef.get(row.ref) !== row.value_or_mpn);
if (mismatches.length > 0) {
  throw new Error(`Native BOM mismatch: ${JSON.stringify(mismatches.slice(0, 10))}`);
}

const oldInput = await FileBlob.load(oldWorkbookPath);
const oldWorkbook = await SpreadsheetFile.importXlsx(oldInput);
const oldPriceValues = oldWorkbook.worksheets.getItem("Цены_и_источники").getUsedRange().values;
const priceMap = new Map();
for (const row of oldPriceValues.slice(3)) {
  if (!row[0]) continue;
  priceMap.set(String(row[0]), {
    price: typeof row[1] === "number" ? row[1] : null,
    currency: row[2] || "USD",
    date: row[3] || "2026-10-30",
    priceType: row[4] || "оценка",
    source: row[5] || "",
    url: row[6] || "",
    note: row[7] || "Проверить перед заказом",
  });
}

const newPartSources = new Map([
  ["TPS26630RGER", { price: null, currency: "USD", date: releaseDate, priceType: "RFQ_REQUIRED", source: "Texas Instruments, официальная страница изделия", url: "https://www.ti.com/product/TPS2663", note: "Запросить цену для пилотного количества перед заказом" }],
  ["LM76005RNPR", { price: null, currency: "USD", date: releaseDate, priceType: "RFQ_REQUIRED", source: "Texas Instruments, официальная страница изделия", url: "https://www.ti.com/product/LM76005", note: "Официальный ориентир 1ku не применяется к стоимости пилотной партии" }],
  ["CSD19537Q3", { price: null, currency: "USD", date: releaseDate, priceType: "RFQ_REQUIRED", source: "Texas Instruments, официальная страница изделия", url: "https://www.ti.com/product/CSD19537Q3", note: "Запросить цену для пилотного количества перед заказом" }],
  ["BSS138", { price: 0.04, currency: "USD", date: releaseDate, priceType: "официальный ориентир", source: "onsemi, официальный каталог", url: "https://www.onsemi.com/download/data-sheet/pdf/bss138-d.pdf", note: "Ориентир, проверить наличие и цену у поставщика в Китае" }],
  ["SMCJ36CA", { price: null, currency: "USD", date: releaseDate, priceType: "RFQ_REQUIRED", source: "Littelfuse, официальный datasheet SMCJ", url: "https://www.littelfuse.com/assetdocs/littelfuse_tvs_diode_smcj_datasheet.pdf?assetguid=37388813-0d6d-4329-969b-1aa8b7614ac1", note: "Запросить цену для пилотного количества перед заказом" }],
  ["XAL7070-103MEC", { price: 3.58, currency: "USD", date: releaseDate, priceType: "официальная цена 1 шт.", source: "Coilcraft, официальный магазин", url: "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal7070/xal7070-103/", note: "Цена за 1 шт. на дату выпуска, проверить перед заказом" }],
]);
for (const [mpn, source] of newPartSources) priceMap.set(mpn, source);

const groups = new Map();
for (const row of contractRows) {
  const key = [row.value_or_mpn, row.manufacturer, row.footprint_id, row.population].join("|");
  const group = groups.get(key) || {
    mpn: row.value_or_mpn,
    manufacturer: row.manufacturer,
    footprint: row.footprint_id,
    population: row.population,
    procurementClass: row.procurement_class,
    descriptions: [],
    refs: [],
    quantity: 0,
  };
  group.quantity += Number(row.qty || 1);
  group.descriptions.push(row.description);
  group.refs.push(row.ref);
  groups.set(key, group);
}

const grouped = [...groups.values()].map((group) => ({
  ...group,
  description: unique(group.descriptions).join("; "),
  refs: group.refs.sort((left, right) => left.localeCompare(right, "en", { numeric: true })),
  disposition: disposition(group.population),
  price: priceMap.get(group.mpn) || { price: null, currency: "USD", date: "", priceType: "RFQ_REQUIRED", source: "", url: "", note: "Запросить цену перед заказом" },
})).sort((left, right) => {
  const dispositionOrder = { FIT: 0, DNP: 1, PCB_ONLY: 2 };
  const classOrder = { LOCKED_MPN: 0, COMMODITY_SPEC: 1, PCB_ONLY: 2 };
  return dispositionOrder[left.disposition] - dispositionOrder[right.disposition]
    || (classOrder[left.procurementClass] ?? 9) - (classOrder[right.procurementClass] ?? 9)
    || left.mpn.localeCompare(right.mpn, "en", { numeric: true });
});

if (grouped.length !== 57 || grouped.filter((group) => group.disposition === "FIT").length !== 52) {
  throw new Error(`Unexpected grouping: total=${grouped.length}, FIT=${grouped.filter((group) => group.disposition === "FIT").length}`);
}

const workbook = Workbook.create();
const summarySheet = workbook.worksheets.add("Сводный_лист");
const purchaseSheet = workbook.worksheets.add("Закупка");
const detailSheet = workbook.worksheets.add("BOM_детально");
const systemSheet = workbook.worksheets.add("Системная_закупка");
const sourcesSheet = workbook.worksheets.add("Цены_и_источники");
const dnpSheet = workbook.worksheets.add("DNP_PCB_ONLY");

title(summarySheet, 6, "BOM и сводная закупка EVT ГСН, вариант входного питания 24 В");
summarySheet.getRange("A3:F3").values = [["Параметр", "Значение", "Примечание", "Показатель", "Значение", "Примечание"]];
header(summarySheet, "A3:F3");
summarySheet.getRange("A4:C9").values = [
  ["Редакция", `v${version}`, "Вариант 24 В"],
  ["Дата выпуска", releaseDate, "Цены проверяются непосредственно перед заказом"],
  ["Тираж плат, шт.", 1, "Редактируемый параметр"],
  ["Резерв закупки, %", 10, "Округление вверх до целого"],
  ["Валюта компонентов платы", "USD", "Сумма включает только позиции с известной ценой"],
  ["Production authority", "NOT_AUTHORIZED", "Не является разрешением на серийное производство"],
];
summarySheet.getRange("D4:F11").values = [
  ["Строк исходного BOM", null, "native Altium BOM"],
  ["Групп закупки", null, "сгруппировано по MPN, корпусу и population"],
  ["FIT групп", null, "к закупке и монтажу"],
  ["DNP/PCB_ONLY групп", null, "не закупать как FIT"],
  ["Оценка платы, USD", null, "только строки с известной ценой"],
  ["FIT групп без цены", null, "обязателен RFQ перед заказом"],
  ["Покупные модули, USD", null, "только строки с известной ценой"],
  ["Покупные модули, EUR", null, "только строки с известной ценой"],
];
summarySheet.getRange("E4:E11").formulas = [
  ["=COUNTA(BOM_детально!A4:A108)"],
  ["=COUNTA(Закупка!A4:A60)"],
  ["=COUNTIF(Закупка!F4:F60,\"FIT\")"],
  ["=COUNTIF(Закупка!F4:F60,\"DNP\")+COUNTIF(Закупка!F4:F60,\"PCB_ONLY\")"],
  ["=SUM(Закупка!N4:N60)"],
  ["=COUNTIF(Закупка!O4:O60,\"RFQ_REQUIRED\")"],
  ["=SUMIF(Системная_закупка!G4:G10,\"USD\",Системная_закупка!H4:H10)"],
  ["=SUMIF(Системная_закупка!G4:G10,\"EUR\",Системная_закупка!H4:H10)"],
];
summarySheet.getRange("A13:F13").values = [["Важно", "", "", "", "", ""]];
summarySheet.getRange("A13:F13").merge();
summarySheet.getRange("A13:F13").format.fill = "#FFF2CC";
summarySheet.getRange("A13:F13").format.font = { name: "Arial", size: 10, bold: true, color: "#7F6000" };
summarySheet.getRange("A14:F16").values = [
  ["Комплект составлен по BOM_SYS_CARRIER_LAYOUT_004.csv и native Altium BOM из equivalence. Совпадение 105 из 105 проверено.", "", "", "", "", ""],
  ["Цены являются ориентировочными. Для новых узлов 24 В без подтвержденной цены установлен статус RFQ_REQUIRED. Не заменять locked MPN без ECO.", "", "", "", "", ""],
  ["Для пилотного изготовления пакет можно направить фабрике на DFM и коммерческое предложение. Production authority остается NOT_AUTHORIZED до входного контроля и стендовых EVT-испытаний.", "", "", "", "", ""],
];
summarySheet.getRange("A14:F16").merge(true);
body(summarySheet, "A4:F16");
summarySheet.getRange("A14:F16").format.rowHeight = 38;
summarySheet.getRange("B6:B7").setNumberFormat("0");
summarySheet.getRange("E8:E11").setNumberFormat("0.00");
summarySheet.getRange("E4:E7").setNumberFormat("0");
setWidths(summarySheet, [31, 21, 38, 31, 18, 42]);
summarySheet.freezePanes.freezeRows(3);
summarySheet.showGridLines = false;

title(purchaseSheet, 17, "Закупка компонентов платы");
const purchaseHeaders = ["№", "MPN/спецификация", "Изготовитель", "Описание", "Корпус", "Disposition", "Класс", "На плату", "Тираж", "Резерв %", "К заказу", "Цена ед.", "Валюта", "Сумма", "Статус цены", "Источник цены", "Позиционные обозначения"];
purchaseSheet.getRange("A3:Q3").values = [purchaseHeaders];
header(purchaseSheet, "A3:Q3");
const purchaseValues = grouped.map((group, index) => [
  index + 1,
  group.mpn,
  group.manufacturer,
  group.description,
  group.footprint,
  group.disposition,
  group.procurementClass,
  group.quantity,
  1,
  10,
  null,
  group.price.price,
  group.price.currency,
  null,
  null,
  group.price.source,
  group.refs.join(", "),
]);
purchaseSheet.getRange(`A4:Q${grouped.length + 3}`).values = purchaseValues;
const formulaRows = grouped.map((_, index) => {
  const row = index + 4;
  return {
    quantity: [`=IF(F${row}=\"FIT\",ROUNDUP(H${row}*I${row}*(1+J${row}/100),0),0)`],
    amount: [`=IF(AND(F${row}=\"FIT\",ISNUMBER(L${row})),K${row}*L${row},\"\")`],
    priceStatus: [`=IF(F${row}<>\"FIT\",\"НЕ_ЗАКУПАТЬ\",IF(ISNUMBER(L${row}),\"ЦЕНА_ЕСТЬ\",\"RFQ_REQUIRED\"))`],
  };
});
purchaseSheet.getRange(`K4:K${grouped.length + 3}`).formulas = formulaRows.map((row) => row.quantity);
purchaseSheet.getRange(`N4:N${grouped.length + 3}`).formulas = formulaRows.map((row) => row.amount);
purchaseSheet.getRange(`O4:O${grouped.length + 3}`).formulas = formulaRows.map((row) => row.priceStatus);
body(purchaseSheet, `A4:Q${grouped.length + 3}`);
purchaseSheet.getRange(`H4:K${grouped.length + 3}`).setNumberFormat("0");
purchaseSheet.getRange(`L4:N${grouped.length + 3}`).setNumberFormat("0.0000");
purchaseSheet.tables.add(`A3:Q${grouped.length + 3}`, true, "PurchaseTable").style = "TableStyleMedium2";
purchaseSheet.freezePanes.freezeRows(3);
purchaseSheet.showGridLines = false;
setWidths(purchaseSheet, [6, 26, 22, 38, 42, 13, 19, 10, 8, 10, 11, 12, 10, 13, 18, 32, 26]);

title(detailSheet, 11, "BOM детально, актуальный native Altium и контракт 24 В");
const detailHeaders = ["Designator", "MPN/спецификация", "Изготовитель", "Описание", "Корпус", "Количество", "Population", "Disposition", "Класс закупки", "Статус контракта", "Проверка native BOM"];
detailSheet.getRange("A3:K3").values = [detailHeaders];
header(detailSheet, "A3:K3");
const detailValues = contractRows.map((row) => [
  row.ref,
  row.value_or_mpn,
  row.manufacturer,
  row.description,
  row.footprint_id,
  Number(row.qty || 1),
  row.population,
  disposition(row.population),
  row.procurement_class,
  row.status,
  nativeByRef.get(row.ref) === row.value_or_mpn ? "MATCH" : "MISMATCH",
]);
detailSheet.getRange("A4:K108").values = detailValues;
body(detailSheet, "A4:K108");
detailSheet.tables.add("A3:K108", true, "DetailedBomTable").style = "TableStyleMedium2";
detailSheet.freezePanes.freezeRows(3);
detailSheet.showGridLines = false;
setWidths(detailSheet, [14, 28, 23, 40, 46, 11, 16, 13, 19, 16, 20]);

title(systemSheet, 10, "Покупные модули, оснастка и стенд");
systemSheet.getRange("A3:J3").values = [["Категория", "Наименование", "MPN/спецификация", "Изготовитель", "Кол-во", "Цена ед.", "Валюта", "Сумма", "Источник", "Примечание"]];
header(systemSheet, "A3:J3");
const systemValues = [
  ["Покупной модуль", "Радарный модуль 76...81 ГГц", "AWR2944PEVM", "Texas Instruments", 1, 855.58, "USD", null, "Ориентир 2026-10-30; сверить с TI и поставщиком", "Оценочный модуль с антенной. Экспортную доступность проверить перед заказом."],
  ["Покупной модуль", "Внешний GNSS/RTK с настраиваемыми группировками", "simpleRTK3B Pro (mosaic-X5)", "ArduSimple / Septentrio", 1, 569, "EUR", null, "Официальный магазин ArduSimple, ориентир 2026-10-30", "Подключение к J8 разъемом, без пайки. GNSS не является единственным источником доверия."],
  ["Оснастка", "Программатор и отладчик", "ST-LINK/V3SET или совместимый SWD", "STMicroelectronics", 1, 35, "USD", null, "Бюджетный ориентир 2026-10-30", "Нужен адаптер к Tag-Connect TC2030-NL."],
  ["Оснастка", "Кабель Tag-Connect SWD", "TC2030-IDC-NL", "Tag-Connect", 1, 49, "USD", null, "Ориентир 2026-10-30", "Посадочное место J10 предусмотрено на плате."],
  ["Лабораторное питание", "Источник 0...36 В, не менее 5 А", "по результату закупки", "по результату закупки", 1, 25, "USD", null, "Бюджетный ориентир 2026-10-30", "Для первого включения нужны ограничение тока и защитное заземление."],
  ["Интерфейс стенда", "USB-UART адаптер 3,3 В", "изолированный предпочтительно", "по результату закупки", 1, null, "USD", null, "RFQ_REQUIRED", "Не подключать вывод 5 В адаптера к плате. Соединить TX, RX и GND по схеме стенда."],
  ["Кабель", "USB-кабель для USB-UART адаптера", "по разъему выбранного адаптера", "по результату закупки", 1, null, "USD", null, "RFQ_REQUIRED", "Длина 1...2 м, исправная линия данных."],
];
systemSheet.getRange("A4:J10").values = systemValues;
systemSheet.getRange("H4:H10").formulas = systemValues.map((_, index) => {
  const row = index + 4;
  return [`=IF(ISNUMBER(F${row}),E${row}*F${row},\"\")`];
});
body(systemSheet, "A4:J10");
systemSheet.getRange("E4:E10").setNumberFormat("0");
systemSheet.getRange("F4:H10").setNumberFormat("0.00");
systemSheet.tables.add("A3:J10", true, "SystemPurchaseTable").style = "TableStyleMedium2";
systemSheet.freezePanes.freezeRows(3);
systemSheet.showGridLines = false;
setWidths(systemSheet, [20, 36, 31, 24, 10, 12, 10, 13, 35, 48]);

title(sourcesSheet, 8, "Цены и источники");
sourcesSheet.getRange("A3:H3").values = [["MPN/спецификация", "Цена", "Валюта", "Дата", "Тип цены", "Источник", "URL", "Комментарий"]];
header(sourcesSheet, "A3:H3");
const sourceRows = grouped.filter((group) => group.disposition === "FIT").map((group) => [
  group.mpn,
  group.price.price,
  group.price.currency,
  group.price.date,
  group.price.priceType,
  group.price.source,
  group.price.url,
  group.price.note,
]);
sourcesSheet.getRange(`A4:H${sourceRows.length + 3}`).values = sourceRows;
body(sourcesSheet, `A4:H${sourceRows.length + 3}`);
sourcesSheet.getRange(`B4:B${sourceRows.length + 3}`).setNumberFormat("0.0000");
sourcesSheet.tables.add(`A3:H${sourceRows.length + 3}`, true, "PriceSourcesTable").style = "TableStyleMedium2";
sourcesSheet.freezePanes.freezeRows(3);
sourcesSheet.showGridLines = false;
setWidths(sourcesSheet, [29, 12, 10, 13, 25, 42, 62, 46]);

const dnpGroups = grouped.filter((group) => group.disposition !== "FIT");
title(dnpSheet, 7, "DNP и PCB_ONLY");
dnpSheet.getRange("A3:G3").values = [["MPN/спецификация", "Изготовитель", "Описание", "Disposition", "Кол-во", "Designators", "Действие"]];
header(dnpSheet, "A3:G3");
dnpSheet.getRange(`A4:G${dnpGroups.length + 3}`).values = dnpGroups.map((group) => [
  group.mpn,
  group.manufacturer,
  group.description,
  group.disposition,
  0,
  group.refs.join(", "),
  group.disposition === "DNP" ? "НЕ ЗАСЕЛЯТЬ" : "не закупать как компонент",
]);
body(dnpSheet, `A4:G${dnpGroups.length + 3}`);
dnpSheet.tables.add(`A3:G${dnpGroups.length + 3}`, true, "DnpTable").style = "TableStyleMedium2";
dnpSheet.freezePanes.freezeRows(3);
dnpSheet.showGridLines = false;
setWidths(dnpSheet, [28, 22, 40, 15, 10, 25, 31]);

workbook.recalculate();

const formulaErrors = [];
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  if (!used) continue;
  used.values.forEach((row, rowIndex) => row.forEach((value, columnIndex) => {
    if (typeof value === "string" && /^#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A)/.test(value)) {
      formulaErrors.push(`${sheet.name}!${columnName(columnIndex + 1)}${rowIndex + 1}:${value}`);
    }
  }));
}
if (formulaErrors.length > 0) {
  throw new Error(`Formula errors: ${formulaErrors.join(", ")}`);
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 0.8, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheet.name}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const summary = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 4,
  tableMaxCols: 8,
  tableMaxCellChars: 60,
});

const qa = {
  schema: "EVT-GSN-BOM-RELEASE-QA-002",
  version,
  date: releaseDate,
  status: "PASS",
  source_rows: contractRows.length,
  native_rows: nativeRows.length,
  native_match: `${contractRows.length - mismatches.length}/${contractRows.length}`,
  grouped_rows: grouped.length,
  fit_groups: grouped.filter((group) => group.disposition === "FIT").length,
  dnp_pcb_only_groups: grouped.filter((group) => group.disposition !== "FIT").length,
  formula_errors: formulaErrors,
  output: path.relative(root, outputPath).replaceAll("\\", "/"),
  preview_dir: path.relative(root, previewDir).replaceAll("\\", "/"),
  production_authority: "NOT_AUTHORIZED",
};
await fs.writeFile(qaPath, `${JSON.stringify(qa, null, 2)}\n`, "utf8");
console.log(JSON.stringify(qa, null, 2));
console.log(summary.ndjson || String(summary));
