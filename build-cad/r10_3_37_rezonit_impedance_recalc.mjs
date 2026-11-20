import crypto from "node:crypto";
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
  "RADAR_D79_POWER_24V_v0.9.3.36_R10_3_36_IMPEDANCE_CLEAR_ROUTE_ASCII.PcbDoc",
);
const output = path.join(
  releaseRoot,
  "01_Исходник_Altium",
  "RADAR_D79_POWER_24V_v0.9.3.37_R10_3_37_REZONIT_IMPEDANCE_RECALC_ASCII.PcbDoc",
);
const auditFile = path.join(
  releaseRoot,
  "05_DRC_и_аудит",
  "R10_3_37",
  "R10_3_37_пересчет_стека_и_импеданса.json",
);

const milToMm = 0.0254;
const mmToMil = (value) => `${(value / milToMm).toFixed(4)}mil`;

const profiles = {
  USB90_INNER: { nets: ["USB_DP", "USB_DM"], layer: "MID8", widthMm: 0.19808, gapMm: 0.15 },
  USB90_BOTTOM: { nets: ["USB_DP", "USB_DM"], layer: "BOTTOM", widthMm: 0.24301, gapMm: 0.15 },
  CAN120_INNER: { nets: ["RADAR_CANH", "RADAR_CANL"], layer: "MID8", widthMm: 0.12471, gapMm: 0.20 },
  CAN120_BOTTOM: { nets: ["RADAR_CANH", "RADAR_CANL"], layer: "BOTTOM", widthMm: 0.15152, gapMm: 0.20 },
};

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
  if (!pattern.test(line)) throw new Error(`Field ${field} was not found`);
  return line.replace(pattern, `|${field}=${value}`);
}

function replaceToken(line, oldToken, newToken) {
  if (!line.includes(oldToken)) throw new Error(`Stack token was not found: ${oldToken}`);
  return line.replace(oldToken, newToken);
}

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex").toUpperCase();
}

function modernStack(line) {
  const replacements = [
    ["V9_STACK_LAYER3_COPTHICK=0.7mil", "V9_STACK_LAYER3_COPTHICK=1.7717mil"],
    ["V9_STACK_LAYER4_DIELCONST=3.070", "V9_STACK_LAYER4_DIELCONST=3.160"],
    ["V9_STACK_LAYER5_COPTHICK=0.7mil", "V9_STACK_LAYER5_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER7_COPTHICK=1.4mil", "V9_STACK_LAYER7_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER8_NAME=D3 FR4 Core 0.300mm", "V9_STACK_LAYER8_NAME=D3 FR4 Core 0.100mm"],
    ["V9_STACK_LAYER8_DIELCONST=4.600", "V9_STACK_LAYER8_DIELCONST=3.700"],
    ["V9_STACK_LAYER8_DIELHEIGHT=0.300mm", "V9_STACK_LAYER8_DIELHEIGHT=0.100mm"],
    ["V9_STACK_LAYER9_COPTHICK=1.4mil", "V9_STACK_LAYER9_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER10_NAME=D4 FR4 7628 0.193mm", "V9_STACK_LAYER10_NAME=D4 FR4 PP 0.255mm"],
    ["V9_STACK_LAYER10_DIELCONST=4.600", "V9_STACK_LAYER10_DIELCONST=4.250"],
    ["V9_STACK_LAYER10_DIELHEIGHT=0.193mm", "V9_STACK_LAYER10_DIELHEIGHT=0.255mm"],
    ["V9_STACK_LAYER10_DIELMATERIAL=FR-4 Tg150 7628", "V9_STACK_LAYER10_DIELMATERIAL=FR-4 Tg150 2116+2116"],
    ["V9_STACK_LAYER11_COPTHICK=4.1mil", "V9_STACK_LAYER11_COPTHICK=4.1339mil"],
    ["V9_STACK_LAYER12_NAME=D5 FR4 2116 0.115mm", "V9_STACK_LAYER12_NAME=D5 FR4 PP 0.448mm"],
    ["V9_STACK_LAYER12_DIELCONST=4.200", "V9_STACK_LAYER12_DIELCONST=4.400"],
    ["V9_STACK_LAYER12_DIELHEIGHT=0.115mm", "V9_STACK_LAYER12_DIELHEIGHT=0.448mm"],
    ["V9_STACK_LAYER12_DIELMATERIAL=FR-4 Tg150 2116", "V9_STACK_LAYER12_DIELMATERIAL=FR-4 Tg150 2116+2116+7628"],
    ["V9_STACK_LAYER13_COPTHICK=4.1mil", "V9_STACK_LAYER13_COPTHICK=4.1339mil"],
    ["V9_STACK_LAYER14_NAME=D6 FR4 7628 0.193mm", "V9_STACK_LAYER14_NAME=D6 FR4 PP 0.255mm"],
    ["V9_STACK_LAYER14_DIELCONST=4.600", "V9_STACK_LAYER14_DIELCONST=4.250"],
    ["V9_STACK_LAYER14_DIELHEIGHT=0.193mm", "V9_STACK_LAYER14_DIELHEIGHT=0.255mm"],
    ["V9_STACK_LAYER14_DIELMATERIAL=FR-4 Tg150 7628", "V9_STACK_LAYER14_DIELMATERIAL=FR-4 Tg150 2116+2116"],
    ["V9_STACK_LAYER15_COPTHICK=1.4mil", "V9_STACK_LAYER15_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER16_NAME=D7 FR4 Core 0.300mm", "V9_STACK_LAYER16_NAME=D7 FR4 Core 0.100mm"],
    ["V9_STACK_LAYER16_DIELCONST=4.600", "V9_STACK_LAYER16_DIELCONST=3.700"],
    ["V9_STACK_LAYER16_DIELHEIGHT=0.300mm", "V9_STACK_LAYER16_DIELHEIGHT=0.100mm"],
    ["V9_STACK_LAYER17_COPTHICK=1.4mil", "V9_STACK_LAYER17_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER19_COPTHICK=0.7mil", "V9_STACK_LAYER19_COPTHICK=0.5906mil"],
    ["V9_STACK_LAYER20_DIELCONST=3.070", "V9_STACK_LAYER20_DIELCONST=3.160"],
    ["V9_STACK_LAYER21_COPTHICK=0.7mil", "V9_STACK_LAYER21_COPTHICK=1.7717mil"],
  ];
  let updated = line;
  for (const [oldToken, newToken] of replacements) updated = replaceToken(updated, oldToken, newToken);
  return updated;
}

function legacyStack(line) {
  const replacements = [
    ["LAYER1COPTHICK=0.7mil", "LAYER1COPTHICK=1.7717mil"],
    ["LAYER1DIELCONST=3.070", "LAYER1DIELCONST=3.160"],
    ["LAYER2COPTHICK=0.7mil", "LAYER2COPTHICK=0.5906mil"],
    ["LAYER6COPTHICK=1.4mil", "LAYER6COPTHICK=0.5906mil"],
    ["LAYER6DIELCONST=4.600", "LAYER6DIELCONST=3.700"],
    ["LAYER6DIELHEIGHT=0.300mm", "LAYER6DIELHEIGHT=0.100mm"],
    ["LAYER7COPTHICK=1.4mil", "LAYER7COPTHICK=0.5906mil"],
    ["LAYER7DIELCONST=4.600", "LAYER7DIELCONST=4.250"],
    ["LAYER7DIELHEIGHT=0.193mm", "LAYER7DIELHEIGHT=0.255mm"],
    ["LAYER7DIELMATERIAL=FR-4 Tg150 7628", "LAYER7DIELMATERIAL=FR-4 Tg150 2116+2116"],
    ["LAYER3COPTHICK=1.4mil", "LAYER3COPTHICK=4.1339mil"],
    ["LAYER3DIELCONST=4.100", "LAYER3DIELCONST=4.400"],
    ["LAYER3DIELHEIGHT=0.250mm", "LAYER3DIELHEIGHT=0.448mm"],
    ["LAYER3DIELMATERIAL=FR-4 Tg150 Core", "LAYER3DIELMATERIAL=FR-4 Tg150 2116+2116+7628"],
    ["LAYER4COPTHICK=1.4mil", "LAYER4COPTHICK=4.1339mil"],
    ["LAYER4DIELCONST=4.600", "LAYER4DIELCONST=4.250"],
    ["LAYER4DIELHEIGHT=0.193mm", "LAYER4DIELHEIGHT=0.255mm"],
    ["LAYER4DIELMATERIAL=FR-4 Tg150 7628", "LAYER4DIELMATERIAL=FR-4 Tg150 2116+2116"],
    ["LAYER8COPTHICK=1.4mil", "LAYER8COPTHICK=0.5906mil"],
    ["LAYER8DIELCONST=4.600", "LAYER8DIELCONST=3.700"],
    ["LAYER8DIELHEIGHT=0.300mm", "LAYER8DIELHEIGHT=0.100mm"],
    ["LAYER9COPTHICK=1.4mil", "LAYER9COPTHICK=0.5906mil"],
    ["LAYER5COPTHICK=0.7mil", "LAYER5COPTHICK=0.5906mil"],
    ["LAYER5DIELCONST=3.070", "LAYER5DIELCONST=3.160"],
    ["LAYER32COPTHICK=0.7mil", "LAYER32COPTHICK=1.7717mil"],
  ];
  let updated = line;
  for (const [oldToken, newToken] of replacements) updated = replaceToken(updated, oldToken, newToken);
  return updated;
}

function widthFields(innerWidth, bottomWidth) {
  const fields = [];
  for (const layer of ["TOPLAYER", ...Array.from({ length: 30 }, (_, index) => `MIDLAYER${index + 1}`), "BOTTOMLAYER"]) {
    const width = layer === "BOTTOMLAYER" ? bottomWidth : innerWidth;
    fields.push([`${layer}_MINWIDTH`, mmToMil(width * 0.95)]);
    fields.push([`${layer}_MAXWIDTH`, mmToMil(width * 1.05)]);
    fields.push([`${layer}_PREFWIDTH`, mmToMil(width)]);
  }
  return fields;
}

function updatePairRule(line, innerWidth, bottomWidth, gapMm) {
  let updated = line;
  updated = replaceField(updated, "MINLIMIT", mmToMil(gapMm * 0.80));
  updated = replaceField(updated, "MAXLIMIT", mmToMil(gapMm * 1.20));
  updated = replaceField(updated, "MOSTFREQGAP", mmToMil(gapMm));
  for (const [field, value] of widthFields(innerWidth, bottomWidth)) updated = replaceField(updated, field, value);
  return replaceField(updated, "COMMENT", "R10.3.37 Rezonit document recalculation; final geometry by fabricator field solver and coupon");
}

function updateWidthRule(line, widthMm) {
  let updated = line;
  updated = replaceField(updated, "MINLIMIT", mmToMil(widthMm * 0.95));
  updated = replaceField(updated, "MAXLIMIT", mmToMil(widthMm * 1.05));
  updated = replaceField(updated, "PREFEREDWIDTH", mmToMil(widthMm));
  return replaceField(updated, "COMMENT", "R10.3.37 Rezonit document recalculation; final geometry by fabricator field solver and coupon");
}

const sourceLines = fs.readFileSync(source, "latin1").split(/(?<=\r\n|\n)/);
const netNames = new Map();
for (const line of sourceLines) {
  const record = parseRecord(line);
  if (record.RECORD === "Net" && /^\d+$/.test(record.ID ?? "")) netNames.set(Number(record.ID), record.NAME ?? "");
}

const changedTracks = [];
const changedRules = [];
let modernStackChanged = 0;
let legacyStackChanged = 0;
const outputLines = sourceLines.map((line) => {
  const record = parseRecord(line);
  if (record.RECORD === "Board" && line.includes("V9_MASTERSTACK_STYLE=")) {
    modernStackChanged += 1;
    legacyStackChanged += 1;
    return legacyStack(modernStack(line));
  }
  if (record.RECORD === "Board" && line.includes("LAYER1NAME=Top Layer")) {
    legacyStackChanged += 1;
    return legacyStack(line);
  }
  if (record.RECORD === "Track" && /^\d+$/.test(record.NET ?? "")) {
    const net = netNames.get(Number(record.NET));
    const profile = Object.entries(profiles).find(([, value]) => value.layer === record.LAYER && value.nets.includes(net));
    if (profile) {
      const [profileName, value] = profile;
      const updated = replaceField(line, "WIDTH", mmToMil(value.widthMm));
      changedTracks.push({
        index: record.INDEXFORSAVE,
        net,
        profile: profileName,
        layer: record.LAYER,
        old_width: record.WIDTH,
        new_width: parseRecord(updated).WIDTH,
        x1: record.X1,
        y1: record.Y1,
        x2: record.X2,
        y2: record.Y2,
      });
      return updated;
    }
  }
  if (record.RECORD === "DXPRule") {
    let updated = line;
    if (record.NAME === "R10_USB90_IMPEDANCE") {
      updated = updatePairRule(line, profiles.USB90_INNER.widthMm, profiles.USB90_BOTTOM.widthMm, profiles.USB90_INNER.gapMm);
    } else if (record.NAME === "R10_CAN120_IMPEDANCE") {
      updated = updatePairRule(line, profiles.CAN120_INNER.widthMm, profiles.CAN120_BOTTOM.widthMm, profiles.CAN120_INNER.gapMm);
    } else if (record.NAME === "R10_USB90_WIDTH") {
      updated = updateWidthRule(line, profiles.USB90_INNER.widthMm);
    } else if (record.NAME === "R10_USB90_BOTTOM_WIDTH") {
      updated = updateWidthRule(line, profiles.USB90_BOTTOM.widthMm);
    } else if (record.NAME === "R10_CAN120_WIDTH") {
      updated = updateWidthRule(line, profiles.CAN120_INNER.widthMm);
    } else if (record.NAME === "R10_CAN120_BOTTOM_WIDTH") {
      updated = updateWidthRule(line, profiles.CAN120_BOTTOM.widthMm);
    }
    if (updated !== line) {
      changedRules.push(record.NAME);
      return updated;
    }
  }
  return line;
});

if (modernStackChanged !== 1 || legacyStackChanged !== 1) {
  throw new Error(`Unexpected board stack record count: modern=${modernStackChanged}, legacy=${legacyStackChanged}`);
}
for (const expected of [
  "R10_USB90_IMPEDANCE",
  "R10_CAN120_IMPEDANCE",
  "R10_USB90_WIDTH",
  "R10_USB90_BOTTOM_WIDTH",
  "R10_CAN120_WIDTH",
  "R10_CAN120_BOTTOM_WIDTH",
]) {
  if (!changedRules.includes(expected)) throw new Error(`Rule was not updated: ${expected}`);
}

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, outputLines.join(""), "latin1");

const profileCounts = {};
for (const [name, value] of Object.entries(profiles)) {
  profileCounts[name] = {
    changed_tracks: changedTracks.filter((row) => row.profile === name).length,
    width_mm: value.widthMm,
    gap_mm: value.gapMm,
  };
}

const audit = {
  schema: "R10-REZONIT-IMPEDANCE-RECALC-001",
  revision: "R10.3.37",
  production_authority: "NOT_AUTHORIZED",
  source: path.relative(repo, source).replaceAll("\\", "/"),
  output: path.relative(repo, output).replaceAll("\\", "/"),
  source_sha256: sha256(source),
  output_sha256: sha256(output),
  stack: {
    order_finished_thickness_mm: 2.0,
    nominal_material_sum_before_mask_finish_mm: 2.032,
    outer_finished_copper_um: 45,
    internal_signal_and_reference_copper_um: 15,
    power_copper_um: 105,
    D1_D9_RO3003G2_mm: 0.127,
    D2_D8_FR4_2116_mm: 0.115,
    D3_D7_FR4_core_mm: 0.100,
    D4_D6_FR4_prepreg_package_mm: 0.255,
    D5_FR4_prepreg_package_mm: 0.448,
    copper_fill_rule_check: "D4/D6 0.255 >= 2*(0.015+0.105)=0.240; D5 0.448 >= 2*(0.105+0.105)=0.420",
  },
  profiles: profileCounts,
  changed_track_records: changedTracks.length,
  changed_tracks: changedTracks,
  changed_rules: [...new Set(changedRules)],
  rf_policy: "Antenna series-feed widths are intentionally unchanged. They are synthesized sections and require EM tuning rather than blanket RF50 replacement.",
  validation_required: [
    "Open the ASCII board in Altium and save as native PcbDoc",
    "Repour all polygons",
    "Run full batch DRC including width, clearance, differential-pair and unrouted checks",
    "Review actual pair gaps after width change and adjust centerlines if DRC reports a pair geometry violation",
    "Obtain fabricator pressed-stack, 2D field-solver and impedance-coupon confirmation",
    "Run antenna EM verification before production authority",
  ],
};
fs.mkdirSync(path.dirname(auditFile), { recursive: true });
fs.writeFileSync(auditFile, `${JSON.stringify(audit, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  output: audit.output,
  output_sha256: audit.output_sha256,
  changed_track_records: audit.changed_track_records,
  profile_counts: profileCounts,
  changed_rules: audit.changed_rules,
}, null, 2));
