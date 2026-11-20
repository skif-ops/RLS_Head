import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repo = "C:/Users/skifn/.codex/.chatgpt-projects/g-p-6a9feb917c48819182ec25e1ef55310c/RLS_Head-git";
const calcDir = path.join(
  repo,
  "hardware/radar/altium/RADAR_D79_v0.9.0_R10_ENGINEERING_REWORK/07_Расчеты_СВЧ",
);
const outputPath = path.join(calcDir, "R10_расчет_импеданса.xlsx");
const previewDir = path.join(repo, "build-cad/.r10_impedance_preview");
const json = JSON.parse(await fs.readFile(path.join(calcDir, "R10_расчет_импеданса.json"), "utf8"));

const wb = Workbook.create();
const summary = wb.worksheets.add("Итоги");
const profiles = wb.worksheets.add("Расчет профилей");
const applicability = wb.worksheets.add("Применимость");
const sensitivity = wb.worksheets.add("Чувствительность");
const stack = wb.worksheets.add("Стек 2 мм");
const sources = wb.worksheets.add("Источники");
const fontName = "Arial";
const dark = "#203864";
const pale = "#D9E2F3";
const inputFill = "#FFF2CC";
const warningFill = "#FCE4D6";

for (const sheet of [summary, profiles, applicability, sensitivity, stack, sources]) {
  sheet.showGridLines = false;
}

function setBase(range, size = 10) {
  range.format.font = { name: fontName, size, color: "#000000" };
  range.format.verticalAlignment = "center";
}

function setTitle(sheet, rangeAddress, title) {
  const range = sheet.getRange(rangeAddress);
  range.values = [[title]];
  range.format.font = { name: fontName, size: 14, bold: true, color: "#000000" };
  range.format.rowHeight = 24;
}

function setHeader(range) {
  range.format.fill = dark;
  range.format.font = { name: fontName, size: 10, bold: true, color: "#FFFFFF" };
  range.format.horizontalAlignment = "center";
  range.format.verticalAlignment = "center";
  range.format.wrapText = true;
  range.format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
}

function setTableBody(range) {
  setBase(range, 10);
  range.format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
}

function statusRu(status) {
  if (status === "PRELIMINARY_FIELD_SOLVER_AND_COUPON_REQUIRED") {
    return "Предварительно. Нужны полевой расчет и купон";
  }
  if (status === "SCREENING_ONLY_FACTORY_STACK_AND_FIELD_SOLVER_REQUIRED") {
    return "Проверочная оценка. Нужны стек изготовителя и полевой расчет";
  }
  if (status === "REZONIT_DOCUMENT_RECALC_FIELD_SOLVER_AND_COUPON_REQUIRED") {
    return "Пересчитано по опубликованным данным Резонита. Нужны полевой расчет и купон";
  }
  if (status === "ALTERNATIVE_ONLY_WRITTEN_FABRICATOR_CONFIRMATION_REQUIRED") {
    return "Альтернативный вариант. Требуется письменное подтверждение изготовителя";
  }
  return status;
}

function topologyRu(topology) {
  return topology
    .replace("open microstrip L1 over continuous L2 RF_GND", "Открытая микрополосковая линия L1 над сплошным L2 RF_GND")
    .replace("embedded asymmetric line between L2 and L4", "Несимметричная встроенная линия L3 между L2 и L4")
    .replace("embedded edge-coupled pair between L2 and L4", "Встроенная краевая дифференциальная пара L3 между L2 и L4")
    .replace("embedded edge-coupled pair between L7 and L9", "Встроенная краевая дифференциальная пара L8 между L7 и L9")
    .replace("bottom microstrip differential pair over continuous L9 DIGITAL_GND", "Нижняя микрополосковая дифференциальная пара L10 над сплошным L9 DIGITAL_GND");
}

setTitle(summary, "A2", "Пересчет импеданса платы R10.3.37 по документам Резонита");
summary.getRange("A4:B13").values = [
  ["Ревизия", json.revision],
  ["Допуск к производству", json.production_authority],
  ["Номинальная готовая толщина, мм", json.target_finished_thickness_mm],
  ["Номинальная сумма стека до маски и финиша, мм", json.nominal_stack_thickness_before_mask_finish_mm],
  ["СВЧ-ламинат", "RO3003G2 0,127 мм; тип и шероховатость меди подтверждает изготовитель"],
  ["Опорный слой СВЧ", "L2 RF_GND"],
  ["Нативный DRC R10.3.37", `${json.native_validation.rule_violations} нарушений, ${json.native_validation.warnings} предупреждений`],
  ["Неразведенные соединения", json.native_validation.unrouted_net_violations],
  ["SHA-256 бинарного PcbDoc", json.native_validation.native_pcbdoc.sha256],
  ["Строгий аудит трассировки", `${json.routing_culture_validation.gate}: ${json.routing_culture_validation.counts.junctions_hard_rework} жестких замечаний по узлам, ${json.routing_culture_validation.counts.long_off_angle_segments} длинных неортогональных сегментов`],
];
setTableBody(summary.getRange("A4:B13"));
summary.getRange("A4:A13").format.font = { name: fontName, size: 10, bold: true, color: "#000000" };
summary.getRange("B5").format.fill = warningFill;
summary.getRange("B13").format.fill = warningFill;
summary.getRange("A15:H15").values = [[
  "Профиль",
  "Номинал, Ом",
  "Слой",
  "Опора",
  "Ширина, мм",
  "Зазор, мм",
  "Расчет, Ом",
  "Статус",
]];
setHeader(summary.getRange("A15:H15"));
json.profiles.forEach((row, index) => {
  const r = 16 + index;
  summary.getRange(`A${r}:F${r}`).values = [[
    row.profile,
    row.target_ohm,
    row.layer,
    row.reference,
    row.width_mm,
    row.gap_mm === "" ? null : row.gap_mm,
  ]];
  summary.getRange(`G${r}`).formulas = [[`='Расчет профилей'!T${6 + index}`]];
  summary.getRange(`H${r}`).values = [[statusRu(row.status)]];
});
const summaryProfilesEnd = 15 + json.profiles.length;
const summaryNotesStart = summaryProfilesEnd + 2;
const summaryNotesEnd = summaryNotesStart + 5;
setTableBody(summary.getRange(`A16:H${summaryProfilesEnd}`));
summary.getRange(`B16:B${summaryProfilesEnd}`).format.numberFormat = "0.0";
summary.getRange(`E16:G${summaryProfilesEnd}`).format.numberFormat = "0.00000";
summary.getRange(`A${summaryNotesStart}:B${summaryNotesEnd}`).values = [
  ["Статус трассировки", "DRC 0, но строгий геометрический контроль не пройден. Полное соответствие требованиям ГОСТ, IPC и инженерной культуры не подтверждено."],
  ["Медь", "Приняты 45 мкм на внешних и 15 мкм на сигнальных и опорных внутренних слоях. Силовые PWR_A и PWR_B сохранены 105 мкм по расчету тока 24 В."],
  ["Критический допуск", "Толщина D1 0,127 мм, итоговая медь, Dk и модель подтрава должны быть подтверждены изготовителем."],
  ["Контроль заказа", "В заказ включить контролируемый импеданс, купон, отчет измерений и фактический прессованный стек."],
  ["Ограничение", "Размеры последовательных секций антенной решетки определяются электродинамической моделью, а не профилем RF50."],
  ["СВЧ рисунок R10.3.37", "Наблюдаемые ширины 0,10160, 0,21336 и 0,21340 мм нельзя автоматически заменять на RF50."],
];
setTableBody(summary.getRange(`A${summaryNotesStart}:B${summaryNotesEnd}`));
summary.getRange(`A${summaryNotesStart}:A${summaryNotesEnd}`).format.font = { name: fontName, size: 10, bold: true, color: "#000000" };
summary.getRange("A1:G1").format.rowHeight = 8;
summary.getRange("A:A").format.columnWidth = 30;
summary.getRange("B:B").format.columnWidth = 45;
summary.getRange("C:D").format.columnWidth = 17;
summary.getRange("E:G").format.columnWidth = 14;
summary.getRange("H:H").format.columnWidth = 36;
summary.getRange(`A2:H${summaryNotesEnd}`).format.wrapText = true;
summary.getRange("A2:H2").format.wrapText = false;

setTitle(profiles, "A2", "Воспроизводимый расчет профилей");
profiles.getRange("A4:U5").values = [[
  "Профиль",
  "Номинал, Ом",
  "h, мм",
  "t, мм",
  "Dk",
  "W, мм",
  "S, мм",
  "u=W/h",
  "t/h",
  "coth",
  "du1",
  "dur",
  "u для Dkэфф",
  "u для Z0",
  "a(u)",
  "b(Dk)",
  "Dkэфф",
  "f(u)",
  "Z0, Ом",
  "Результат, Ом",
  "Ошибка, %",
], Array(21).fill("")];
setHeader(profiles.getRange("A4:U4"));
json.profiles.forEach((row, index) => {
  const r = 6 + index;
  profiles.getRange(`A${r}:G${r}`).values = [[
    row.profile,
    row.target_ohm,
    row.height_mm,
    row.copper_mm,
    row.design_er,
    row.width_mm,
    row.gap_mm === "" ? null : row.gap_mm,
  ]];
  profiles.getRange(`H${r}:U${r}`).formulas = [[
    `=F${r}/C${r}`,
    `=D${r}/C${r}`,
    `=1/TANH(SQRT(6.517*H${r}))`,
    `=I${r}/PI()*LN(1+4*EXP(1)/(I${r}*J${r}^2))`,
    `=K${r}*(1+1/COSH(SQRT(E${r}-1)))/2`,
    `=H${r}+K${r}`,
    `=H${r}+L${r}`,
    `=1+LN((M${r}^4+(M${r}/52)^2)/(M${r}^4+0.432))/49+LN(1+(M${r}/18.1)^3)/18.7`,
    `=0.564*((E${r}-0.9)/(E${r}+3))^0.053`,
    `=(E${r}+1)/2+(E${r}-1)/2*(1+10/M${r})^(-O${r}*P${r})`,
    `=6+(2*PI()-6)*EXP(-((30.666/N${r})^0.7528))`,
    `=60*LN(R${r}/N${r}+SQRT(1+(2/N${r})^2))/SQRT(Q${r})`,
    `=IF(G${r}="",S${r},2*S${r}*(1-0.48*EXP(-0.96*G${r}/C${r})))`,
    `=T${r}/B${r}-1`,
  ]];
});
setTableBody(profiles.getRange(`A6:U${5 + json.profiles.length}`));
profiles.getRange(`B6:G${5 + json.profiles.length}`).format.fill = inputFill;
profiles.getRange(`B6:T${5 + json.profiles.length}`).format.numberFormat = "0.00000";
profiles.getRange(`U6:U${5 + json.profiles.length}`).format.numberFormat = "0.00%";
const profileNotesStart = 7 + json.profiles.length;
const profileNotesEnd = profileNotesStart + 4;
profiles.getRange(`A${profileNotesStart}:F${profileNotesEnd}`).values = [
  ["Обозначение", "Смысл", "Единица", "Источник", "Статус", "Примечание"],
  ["h", "Толщина диэлектрика до опорного слоя", "мм", "Стек", "Вход", "Берется из прессованного стека"],
  ["t", "Толщина меди", "мм", "Стек", "Вход", "Для L1 требуется учесть итог после металлизации"],
  ["Dk", "Расчетная диэлектрическая проницаемость", "1", "Материал", "Вход", "Для RF проверены варианты 3,03; 3,07 и 3,16"],
  ["Результат", "Z0 для одиночной линии или Zdiff для пары", "Ом", "Формула", "Предварительно", "Подтверждается фабрикой и купоном"],
];
setHeader(profiles.getRange(`A${profileNotesStart}:F${profileNotesStart}`));
setTableBody(profiles.getRange(`A${profileNotesStart + 1}:F${profileNotesEnd}`));
profiles.freezePanes.freezeRows(4);
profiles.getRange("A:A").format.columnWidth = 25;
profiles.getRange("B:U").format.columnWidth = 12;
profiles.getRange(`A${profileNotesStart}:F${profileNotesEnd}`).format.wrapText = true;

setTitle(applicability, "A2", "Применимость расчетных профилей");
applicability.getRange("A4:C4").values = [["Профиль", "Фактическая топология", "Статус применения"]];
setHeader(applicability.getRange("A4:C4"));
json.profiles.forEach((row, index) => {
  const r = 5 + index;
  applicability.getRange(`A${r}:C${r}`).values = [[row.profile, topologyRu(row.topology), statusRu(row.status)]];
});
setTableBody(applicability.getRange(`A5:C${4 + json.profiles.length}`));
applicability.getRange(`A4:C${4 + json.profiles.length}`).format.wrapText = true;
applicability.getRange("A:A").format.columnWidth = 28;
applicability.getRange("B:B").format.columnWidth = 52;
applicability.getRange("C:C").format.columnWidth = 48;

setTitle(sensitivity, "A2", "Чувствительность профиля RF50");
sensitivity.getRange("A4:I4").values = [[
  "Случай",
  "W, мм",
  "h, мм",
  "t, мм",
  "Dk",
  "Z0, Ом",
  "Отклонение, %",
  "Допуск Резонита ±10 %",
  "Статус",
]];
setHeader(sensitivity.getRange("A4:I4"));
json.rf_sensitivity.forEach((row, index) => {
  const r = 5 + index;
  sensitivity.getRange(`A${r}:F${r}`).values = [[
    row.case,
    row.width_mm,
    row.height_mm,
    row.copper_mm,
    row.er,
    row.calculated_ohm,
  ]];
  sensitivity.getRange(`G${r}`).formulas = [[`=F${r}/50-1`]];
  sensitivity.getRange(`H${r}`).values = [[0.10]];
  sensitivity.getRange(`I${r}`).formulas = [[`=IF(ABS(G${r})<=H${r},"В пределах","За пределами")`]];
});
setTableBody(sensitivity.getRange(`A5:I${4 + json.rf_sensitivity.length}`));
sensitivity.getRange(`B5:F${4 + json.rf_sensitivity.length}`).format.numberFormat = "0.00000";
sensitivity.getRange(`G5:H${4 + json.rf_sensitivity.length}`).format.numberFormat = "0.00%";
sensitivity.getRange("A:A").format.columnWidth = 28;
sensitivity.getRange("B:I").format.columnWidth = 14;

setTitle(stack, "A2", "Симметричный производственный стек 2,00 мм");
stack.getRange("A4:E4").values = [["Элемент", "Тип", "Толщина, мм", "Материал", "Проверка симметрии"]];
setHeader(stack.getRange("A4:E4"));
json.stackup.forEach((row, index) => {
  const r = 5 + index;
  const mirror = json.stackup[json.stackup.length - 1 - index];
  const kindRu = row.kind === "copper" ? "медь" : "диэлектрик";
  const materialRu = row.material
    .replace("standard 5 mil", "стандарт 5 mil")
    .replace("VLP base copper", "базовая медь VLP")
    .replace("prepreg", "препрег")
    .replace("core", "ядро")
    .replace(/^copper$/, "медь");
  stack.getRange(`A${r}:D${r}`).values = [[row.item, kindRu, row.thickness_mm, materialRu]];
  stack.getRange(`E${r}`).formulas = [[`=IF(ABS(C${r}-C${4 + json.stackup.length - index})<0.000001,"Да","Нет")`]];
  if (row.item.startsWith("D") && row.material.includes("FR-4")) {
    stack.getRange(`C${r}:D${r}`).format.fill = inputFill;
  }
  if (mirror.thickness_mm !== row.thickness_mm) {
    stack.getRange(`E${r}`).format.fill = warningFill;
  }
});
const totalRow = 5 + json.stackup.length;
stack.getRange(`A${totalRow}:B${totalRow}`).values = [["Итого до маски и финиша", ""]];
stack.getRange(`C${totalRow}`).formulas = [[`=SUM(C5:C${totalRow - 1})`]];
stack.getRange(`D${totalRow}`).values = [["Требуемая толщина заказа 2,00 мм; итог прессования фиксирует изготовитель"]];
stack.getRange(`E${totalRow}`).formulas = [[`=IF(ABS(C${totalRow}-2)<=0.05,"В допуске задания","Проверить")`]];
setTableBody(stack.getRange(`A5:E${totalRow}`));
stack.getRange(`A${totalRow}:E${totalRow}`).format.font = { name: fontName, size: 10, bold: true, color: "#000000" };
stack.getRange(`C5:C${totalRow}`).format.numberFormat = "0.000";
stack.getRange(`A${totalRow + 2}:B${totalRow + 5}`).values = [
  ["Требование", "Значение"],
  ["Готовая толщина", "2,00 мм"],
  ["Публичный допуск Резонита", "не более ±0,30 мм для МПП свыше 1,5 до 3,0 мм"],
  ["Окончательная фиксация", "После расчета прессованного стека изготовителем"],
];
setHeader(stack.getRange(`A${totalRow + 2}:B${totalRow + 2}`));
setTableBody(stack.getRange(`A${totalRow + 3}:B${totalRow + 5}`));
stack.getRange("A:A").format.columnWidth = 25;
stack.getRange("B:B").format.columnWidth = 18;
stack.getRange("C:C").format.columnWidth = 16;
stack.getRange("D:D").format.columnWidth = 44;
stack.getRange("E:E").format.columnWidth = 18;
stack.getRange(`A4:E${totalRow + 5}`).format.wrapText = true;

setTitle(sources, "A2", "Источники, исходные параметры и границы применимости");
sources.getRange("A4:D4").values = [["Источник", "Параметр", "Применение", "Ссылка"]];
setHeader(sources.getRange("A4:D4"));
sources.getRange("A5:D11").values = [
  ["Rogers RO3003G2 Data Sheet", "Dk 3,07 при 77 ГГц, Df 0,0011, 0,127 мм", "Материал и оценка потерь", json.material_source_url],
  ["Резонит типовые сборки", "2116 0,115 мм, 7628 0,193 мм, стандартные ядра", "Округление стека до производственных толщин", json.fabricator_source_url],
  ["Резонит, толщина меди", "45 мкм внешняя и 15 мкм внутренняя для типовой МПП с базовой фольгой 18 мкм", "Основной пересчет геометрии", json.fabricator_copper_source_url],
  ["Резонит, диапазон 76...81 ГГц", "Dk 3,03 для RLD и 3,16 для ED; влияние толщины и шероховатости", "Проверка RF50", json.fabricator_77ghz_article_url],
  ["Резонит, оформление заказа", "Стек, сигнальные и опорные слои, таблица сопротивлений", "Задание изготовителю", json.fabricator_order_source_url],
  ["Резонит, контроль импеданса", "Инструментальная проверка и купон", "Подтверждение готовой партии", json.fabricator_impedance_source_url],
  ["Резонит, правила конструкции", "Толщина препрега относительно суммы соседних медных фольг", "Проверка пакетов D4, D5 и D6 вокруг силовой меди 105 мкм", json.fabricator_construction_rules_url],
];
setTableBody(sources.getRange("A5:D11"));
sources.getRange("A13:B17").values = [
  ["Ограничение", "Описание"],
  ["Модель", "Замкнутая модель Hammerstad-Jensen, не полевой решатель"],
  ["Дифференциальные пары", "Начальная оценка связи, окончательная геометрия по расчету изготовителя"],
  ["СВЧ-антенна", "Последовательные секции и фидеры требуют полного электродинамического расчета"],
  ["Производственный статус", "DRC 0 закрыт, строгий аудит трассировки FAIL. NOT_AUTHORIZED до исправления геометрии, полевого расчета, купона, EM проверки и проверки изготовителем"],
];
setHeader(sources.getRange("A13:B13"));
setTableBody(sources.getRange("A14:B17"));
sources.getRange("A:A").format.columnWidth = 32;
sources.getRange("B:C").format.columnWidth = 40;
sources.getRange("D:D").format.columnWidth = 72;
sources.getRange("A4:D17").format.wrapText = true;

wb.recalculate();
await fs.mkdir(calcDir, { recursive: true });
await fs.rm(previewDir, { recursive: true, force: true });
await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["Итоги", "Расчет профилей", "Применимость", "Чувствительность", "Стек 2 мм", "Источники"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1.2, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const formulaErrors = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
const keyCheck = await wb.inspect({
  kind: "table",
  range: `'Расчет профилей'!A4:U${5 + json.profiles.length}`,
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 21,
});
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outputPath);
const reloaded = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const reloadErrors = await reloaded.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "reloaded formula error scan",
});
const outputBytes = await fs.readFile(outputPath);
const qaPath = path.join(calcDir, "R10_расчет_импеданса_xlsx_QA.json");
const qa = {
  revision: json.revision,
  status: formulaErrors.ndjson.includes("matched 0 entries") && reloadErrors.ndjson.includes("matched 0 entries") ? "PASS" : "REVIEW",
  output: outputPath,
  sha256: createHash("sha256").update(outputBytes).digest("hex").toUpperCase(),
  formula_error_scan: formulaErrors.ndjson,
  reload_error_scan: reloadErrors.ndjson,
  preview_sheets: ["Итоги", "Расчет профилей", "Применимость", "Чувствительность", "Стек 2 мм", "Источники"],
};
await fs.writeFile(qaPath, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ outputPath, previewDir, qaPath, formulaErrors: formulaErrors.ndjson, reloadErrors: reloadErrors.ndjson, keyCheck: keyCheck.ndjson }, null, 2));
