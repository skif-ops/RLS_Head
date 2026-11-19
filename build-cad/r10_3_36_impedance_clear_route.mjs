import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repo = path.dirname(scriptDir);
const releaseRoot = path.join(
  repo,
  "hardware",
  "radar",
  "altium",
  "RADAR_D79_v0.9.0_R10_ENGINEERING_REWORK",
);
const source = path.join(
  releaseRoot,
  "01_Исходник_Altium",
  "RADAR_D79_POWER_24V_v0.9.3.34_R10_3_34_IMPEDANCE_TRANSITIONS_ASCII.PcbDoc",
);
const output = path.join(
  releaseRoot,
  "01_Исходник_Altium",
  "RADAR_D79_POWER_24V_v0.9.3.36_R10_3_36_IMPEDANCE_CLEAR_ROUTE_ASCII.PcbDoc",
);
const auditFile = path.join(
  releaseRoot,
  "05_DRC_и_аудит",
  "R10_3_36",
  "R10_3_36_контракт_импедансной_трассировки.json",
);

function parseRecord(line) {
  const record = {};
  for (const field of line.replace(/[\r\n]+$/, "").split("|")) {
    const separator = field.indexOf("=");
    if (separator >= 0) record[field.slice(0, separator)] = field.slice(separator + 1);
  }
  return record;
}

function replaceField(line, field, value) {
  const pattern = new RegExp(`\\|${field}=[^|\\r\\n]*`);
  return pattern.test(line)
    ? line.replace(pattern, `|${field}=${value}`)
    : line.replace(/[\r\n]+$/, "") + `|${field}=${value}\r\n`;
}

function track(net, layer, a, b, widthMil, index) {
  return `|RECORD=Track|NET=${net}|LAYER=${layer}|X1=${a.x.toFixed(4)}mil|Y1=${a.y.toFixed(4)}mil|X2=${b.x.toFixed(4)}mil|Y2=${b.y.toFixed(4)}mil|WIDTH=${widthMil.toFixed(4)}mil|USERROUTED=TRUE|SELECTION=FALSE|LOCKED=FALSE|UNIONINDEX=0|INDEXFORSAVE=${index}\r\n`;
}

function via(net, point, index) {
  return `|RECORD=Via|NET=${net}|LAYER=MULTILAYER|X=${point.x.toFixed(4)}mil|Y=${point.y.toFixed(4)}mil|DIAMETER=13.7795mil|HOLESIZE=5.9055mil|STARTLAYER=MID8|ENDLAYER=BOTTOM|USERROUTED=TRUE|SELECTION=FALSE|LOCKED=FALSE|UNIONINDEX=0|TENTING=TRUE|TENTINGTOP=TRUE|TENTINGBOTTOM=TRUE|SOLDERMASKEXPANSIONMODE=Manual|SOLDERMASKEXPANSION_MANUAL=-20mil|CSEV=2|CSE=-20mil|HOLEPOSITIVETOLERANCE=0mil|HOLENEGATIVETOLERANCE=0.9843mil|INDEXFORSAVE=${index}\r\n`;
}

const lines = fs.readFileSync(source, "latin1").split(/(?<=\r\n|\n)/);
let maximumTrackIndex = 0;
let maximumViaIndex = 0;
let firstTrackIndex = -1;

for (let index = 0; index < lines.length; index += 1) {
  const record = parseRecord(lines[index]);
  if (record.RECORD === "Track") {
    maximumTrackIndex = Math.max(maximumTrackIndex, Number(record.INDEXFORSAVE ?? 0));
    if (firstTrackIndex < 0) firstTrackIndex = index;
  }
  if (record.RECORD === "Via") {
    maximumViaIndex = Math.max(maximumViaIndex, Number(record.INDEXFORSAVE ?? 0));
  }
}

const removedTracks = new Set([9574, 9575, 9576, 9577, 9578, 9579, 9580]);
const removedVias = new Set([9006, 9007]);
const outputLines = [];
const removedTrackIndexes = [];
const removedViaIndexes = [];
const modifiedTrackIndexes = [];

for (const line of lines) {
  const record = parseRecord(line);
  const index = Number(record.INDEXFORSAVE ?? -1);
  if (record.RECORD === "Track" && removedTracks.has(index)) {
    removedTrackIndexes.push(index);
    continue;
  }
  if (record.RECORD === "Via" && removedVias.has(index)) {
    removedViaIndexes.push(index);
    continue;
  }

  let updated = line;
  if (record.RECORD === "Track" && [5742, 7347].includes(index)) {
    updated = replaceField(updated, "WIDTH", "10.4972mil");
  }
  if (record.RECORD === "Track" && index === 9560) {
    updated = replaceField(updated, "X2", "2820.0000mil");
  }
  if (record.RECORD === "Track" && index === 9561) {
    updated = replaceField(updated, "X1", "2820.0000mil");
  }
  if (updated !== line) modifiedTrackIndexes.push(index);
  outputLines.push(updated);
}

if (
  firstTrackIndex < 0 ||
  removedTrackIndexes.length !== removedTracks.size ||
  removedViaIndexes.length !== removedVias.size
) {
  throw new Error(
    `Unexpected source records: tracks=${removedTrackIndexes.length}, vias=${removedViaIndexes.length}`,
  );
}

let nextTrack = maximumTrackIndex + 1;
let nextVia = maximumViaIndex + 1;
const usbBottomWidthMil = 10.4972;
const usbInnerWidthMil = 7.2874;
const dmStart = { x: 2868.1102, y: 1155.5118 };
const dpStart = { x: 2893.7008, y: 1181.1024 };
const dmVia = { x: 2940.0, y: 1155.5118 };
const dpVia = { x: 2965.5906, y: 1181.1024 };
const dmInnerTurn = { x: 2920.0, y: 1205.5118 };
const dpInnerTurn = { x: 2965.5906, y: 1285.0 };
const dmEnd = { x: 2877.9528, y: 1246.0630 };
const dpEnd = { x: 2893.7008, y: 1360.2362 };

const inserted = [
  track(258, "BOTTOM", dmStart, dmVia, usbBottomWidthMil, nextTrack++),
  track(259, "BOTTOM", dpStart, dpVia, usbBottomWidthMil, nextTrack++),
  track(258, "MID8", dmVia, dmInnerTurn, usbInnerWidthMil, nextTrack++),
  track(258, "MID8", dmInnerTurn, dmEnd, usbInnerWidthMil, nextTrack++),
  track(259, "MID8", dpVia, dpInnerTurn, usbInnerWidthMil, nextTrack++),
  track(259, "MID8", dpInnerTurn, dpEnd, usbInnerWidthMil, nextTrack++),
  via(258, dmVia, nextVia++),
  via(259, dpVia, nextVia++),
];

const insertionIndex = outputLines.findIndex((line) => parseRecord(line).RECORD === "Track");
outputLines.splice(insertionIndex, 0, ...inserted);
fs.writeFileSync(output, outputLines.join(""), "latin1");

const report = {
  schema: "R10-IMPEDANCE-CLEAR-ROUTE-001",
  revision: "R10.3.36",
  source: path.relative(repo, source).replaceAll("\\", "/"),
  output: path.relative(repo, output).replaceAll("\\", "/"),
  production_authority: "NOT_AUTHORIZED",
  stack_reference: {
    total_thickness_mm: 2.0,
    rf_dielectric: "RO3003G2 0.127 mm",
    usb_can_reference: "L9 DIGITAL_GND continuous",
  },
  impedance_profiles: {
    USB90_L8_L9: { target_ohm: 90, width_mm: 0.1851, gap_mm: 0.15 },
    USB90_L10_L9: { target_ohm: 90, width_mm: 0.26663, gap_mm: 0.15 },
    CAN120_L8_L9: { target_ohm: 120, width_mm: 0.11184, gap_mm: 0.2 },
    CAN120_L10_L9: { target_ohm: 120, width_mm: 0.1736014, gap_mm: 0.2 },
  },
  routing_decisions: [
    "USB uses parallel L10 segments with matched widths before paired L10-to-L8 transitions",
    "USB continues on L8 over continuous L9 DIGITAL_GND after the local transition",
    "CAN L8 entry geometry was opened before the layer transition to remove the local clearance pinch",
    "All controlled-width rules remain active in the native Altium design",
  ],
  removed_source_tracks: removedTrackIndexes.sort((a, b) => a - b),
  removed_source_vias: removedViaIndexes.sort((a, b) => a - b),
  modified_source_tracks: modifiedTrackIndexes.sort((a, b) => a - b),
  validation_required: [
    "Open the ASCII board in Altium and save a native PcbDoc",
    "Repour all polygons",
    "Run batch DRC with clearance, short-circuit, width, differential-pair, net-antennae and un-routed checks",
    "Obtain fabricator field-solver dimensions and a controlled-impedance coupon before production authority",
  ],
};
fs.mkdirSync(path.dirname(auditFile), { recursive: true });
fs.writeFileSync(auditFile, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(
  JSON.stringify(
    {
      output: report.output,
      audit: path.relative(repo, auditFile).replaceAll("\\", "/"),
      report,
    },
    null,
    2,
  ),
);
