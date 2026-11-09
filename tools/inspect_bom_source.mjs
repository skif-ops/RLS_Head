import { FileBlob, SpreadsheetFile } from "file:///C:/Program%20Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1026-487-0_26.1026.487.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const path = process.argv[2];
if (!path) {
  throw new Error("Usage: node inspect_bom_source.mjs <workbook.xlsx>");
}

const input = await FileBlob.load(path);
const workbook = await SpreadsheetFile.importXlsx(input);
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  const values = used ? used.values : [];
  console.log(JSON.stringify({
    sheet: sheet.name,
    rows: values.length,
    columns: values.reduce((maximum, row) => Math.max(maximum, row.length), 0),
    preview: values.slice(0, 12),
  }, null, 2));
}
