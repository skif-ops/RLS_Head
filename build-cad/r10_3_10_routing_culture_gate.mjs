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
const defaultSource = path.join(
  releaseRoot,
  "01_Исходник_Altium",
  "RADAR_D79_POWER_24V_v0.9.3.9_R10_3_9_POWER_3OZ_ASCII.PcbDoc",
);
const source = process.argv[2] ? path.resolve(repo, process.argv[2]) : defaultSource;
const revision = process.argv[4] ?? "R10.3.9";
const filePrefix = revision.replaceAll(".", "_");
const outputDir = process.argv[3]
  ? path.resolve(repo, process.argv[3])
  : path.join(releaseRoot, "05_DRC_и_аудит", filePrefix, "routing_culture");
const milToMm = 0.0254;
const powerPattern = /^(?:VIN_RAW|VIN_PROTECTED_24V|RADAR_12V|TI_(?:PVIN3V3|REGOUT_3V3|1V0|1V2|1V8|PMICOUT_.*|V.*))$/;

function parseRecord(line) {
  const result = {};
  for (const field of line.replace(/[\r\n]+$/, "").split("|")) {
    const separator = field.indexOf("=");
    if (separator >= 0) result[field.slice(0, separator)] = field.slice(separator + 1);
  }
  return result;
}

function lengthMm(value) {
  if (!value) return null;
  const match = String(value).trim().match(/^([-+0-9.eE]+)(mil|mm)?$/);
  if (!match) return null;
  const number = Number(match[1]);
  return match[2] === "mm" ? number : number * milToMm;
}

function csvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function writeCsv(file, rows) {
  if (!rows.length) return;
  const fields = Object.keys(rows[0]);
  const lines = [fields.join(",")];
  for (const row of rows) lines.push(fields.map((field) => csvCell(row[field])).join(","));
  fs.writeFileSync(file, `\uFEFF${lines.join("\r\n")}\r\n`, "utf8");
}

function pointKey(x, y) {
  return `${x.toFixed(4)},${y.toFixed(4)}`;
}

function angleDifference(first, second) {
  let difference = Math.abs(first - second) % 360;
  if (difference > 180) difference = 360 - difference;
  return difference;
}

function pointSegmentDistance(point, first, second) {
  const dx = second.x - first.x;
  const dy = second.y - first.y;
  if (dx === 0 && dy === 0) return Math.hypot(point.x - first.x, point.y - first.y);
  const ratio = Math.max(
    0,
    Math.min(1, ((point.x - first.x) * dx + (point.y - first.y) * dy) / (dx * dx + dy * dy)),
  );
  return Math.hypot(point.x - (first.x + ratio * dx), point.y - (first.y + ratio * dy));
}

const records = fs
  .readFileSync(source, "latin1")
  .split(/\r?\n/)
  .filter((line) => line.startsWith("|RECORD="))
  .map(parseRecord);
const nets = new Map(
  records
    .filter((record) => record.RECORD === "Net" && /^\d+$/.test(record.ID ?? ""))
    .map((record) => [Number(record.ID), record.NAME ?? ""]),
);
const netName = (record) => (/^\d+$/.test(record.NET ?? "") ? nets.get(Number(record.NET)) ?? "" : record.NET ?? "");

const padsAndVias = records
  .filter((record) => ["Pad", "Via"].includes(record.RECORD))
  .map((record) => ({
    net: netName(record),
    layer: record.LAYER ?? "",
    startLayer: record.STARTLAYER ?? "",
    endLayer: record.ENDLAYER ?? "",
    x: lengthMm(record.X),
    y: lengthMm(record.Y),
    radius: Math.max(lengthMm(record.XSIZE) ?? 0, lengthMm(record.YSIZE) ?? 0, lengthMm(record.DIAMETER) ?? 0) / 2,
  }))
  .filter((record) => record.x !== null && record.y !== null);

const tracks = records
  .filter((record) => record.RECORD === "Track")
  .map((record, ordinal) => {
    const x1 = lengthMm(record.X1);
    const y1 = lengthMm(record.Y1);
    const x2 = lengthMm(record.X2);
    const y2 = lengthMm(record.Y2);
    const width = lengthMm(record.WIDTH);
    if ([x1, y1, x2, y2, width].some((value) => value === null)) return null;
    return {
      ordinal,
      index: record.INDEXFORSAVE ?? "",
      net: netName(record),
      layer: record.LAYER ?? "",
      width,
      first: { x: x1, y: y1 },
      second: { x: x2, y: y2 },
      length: Math.hypot(x2 - x1, y2 - y1),
    };
  })
  .filter(Boolean);

const groups = new Map();
for (const track of tracks) {
  const groupKey = `${track.net}\u0000${track.layer}`;
  if (!groups.has(groupKey)) groups.set(groupKey, []);
  groups.get(groupKey).push(track);
}

const junctionRows = [];
const danglingRows = [];
const offAngleRows = [];
const overlapRows = [];
const exactSegments = new Map();

for (const track of tracks) {
  const dx = track.second.x - track.first.x;
  const dy = track.second.y - track.first.y;
  const angle = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 180;
  const deviation = Math.abs(angle - Math.round(angle / 45) * 45);
  if (track.length >= 1 && deviation > 5) {
    offAngleRows.push({
      net: track.net,
      layer: track.layer,
      index: track.index,
      length_mm: Number(track.length.toFixed(5)),
      width_mm: Number(track.width.toFixed(5)),
      angle_deg: Number(angle.toFixed(3)),
      deviation_deg: Number(deviation.toFixed(3)),
      x1_mm: Number(track.first.x.toFixed(5)),
      y1_mm: Number(track.first.y.toFixed(5)),
      x2_mm: Number(track.second.x.toFixed(5)),
      y2_mm: Number(track.second.y.toFixed(5)),
    });
  }
  const endpointA = pointKey(track.first.x, track.first.y);
  const endpointB = pointKey(track.second.x, track.second.y);
  const normalized = endpointA < endpointB ? `${endpointA}|${endpointB}` : `${endpointB}|${endpointA}`;
  const segmentKey = `${track.net}\u0000${track.layer}\u0000${normalized}`;
  if (!exactSegments.has(segmentKey)) exactSegments.set(segmentKey, []);
  exactSegments.get(segmentKey).push(track);
}

for (const [segmentKey, matches] of exactSegments) {
  if (matches.length < 2) continue;
  overlapRows.push({
    net: matches[0].net,
    layer: matches[0].layer,
    coincident_segments: matches.length,
    indices: matches.map((track) => track.index).join(";"),
    widths_mm: [...new Set(matches.map((track) => track.width.toFixed(5)))].join(";"),
    segment_key: segmentKey.split("\u0000").at(-1),
  });
}

for (const [groupKey, netTracks] of groups) {
  const [net, layer] = groupKey.split("\u0000");
  const endpoints = new Map();
  for (const track of netTracks) {
    for (const [point, other] of [
      [track.first, track.second],
      [track.second, track.first],
    ]) {
      const key = pointKey(point.x, point.y);
      if (!endpoints.has(key)) endpoints.set(key, { point, connections: [] });
      endpoints.get(key).connections.push({
        track,
        angle: ((Math.atan2(other.y - point.y, other.x - point.x) * 180) / Math.PI + 360) % 360,
      });
    }
  }

  for (const { point, connections } of endpoints.values()) {
    const touchingInterior = netTracks.filter(
      (track) =>
        !connections.some((connection) => connection.track === track) &&
        pointSegmentDistance(point, track.first, track.second) <= 0.002,
    );
    const effectiveDegree = connections.length + touchingInterior.length * 2;
    const widths = [
      ...connections.map((connection) => connection.track.width),
      ...touchingInterior.map((track) => track.width),
    ];
    const angles = [
      ...connections.map((connection) => connection.angle),
      ...touchingInterior.flatMap((track) => [
        ((Math.atan2(track.first.y - point.y, track.first.x - point.x) * 180) / Math.PI + 360) % 360,
        ((Math.atan2(track.second.y - point.y, track.second.x - point.x) * 180) / Math.PI + 360) % 360,
      ]),
    ];
    const nonCollinearAngles = [];
    for (let first = 0; first < angles.length; first += 1) {
      for (let second = first + 1; second < angles.length; second += 1) {
        const difference = angleDifference(angles[first], angles[second]);
        if (difference > 1 && difference < 179) nonCollinearAngles.push(difference);
      }
    }
    const minimumAngle = nonCollinearAngles.length ? Math.min(...nonCollinearAngles) : null;
    const widthRatio = widths.length && Math.min(...widths) > 0 ? Math.max(...widths) / Math.min(...widths) : 1;
    if (effectiveDegree >= 3 || widthRatio >= 1.8 || (minimumAngle !== null && minimumAngle < 30)) {
      junctionRows.push({
        net,
        layer,
        x_mm: Number(point.x.toFixed(5)),
        y_mm: Number(point.y.toFixed(5)),
        effective_degree: effectiveDegree,
        endpoint_connections: connections.length,
        interior_crossings: touchingInterior.length,
        min_width_mm: Number(Math.min(...widths).toFixed(5)),
        max_width_mm: Number(Math.max(...widths).toFixed(5)),
        width_ratio: Number(widthRatio.toFixed(3)),
        minimum_noncollinear_angle_deg: minimumAngle === null ? null : Number(minimumAngle.toFixed(3)),
        power_net: powerPattern.test(net),
        review:
          effectiveDegree >= 4
            ? "STAR_OR_CROSSING_REQUIRES_REWORK"
            : minimumAngle !== null && minimumAngle < 30
              ? "ACUTE_BRANCH_REQUIRES_REWORK"
              : widthRatio >= 1.8
                ? "ABRUPT_WIDTH_CHANGE_REQUIRES_REWORK"
                : "T_JUNCTION_REVIEW",
      });
    }

    if (effectiveDegree !== 1) continue;
    const connectedTrack = connections[0].track;
    const landsOnCopperObject = padsAndVias.some((object) => {
      if (object.net !== net) return false;
      const layerCompatible =
        object.layer === layer ||
        object.layer === "MULTILAYER" ||
        object.startLayer === layer ||
        object.endLayer === layer;
      if (!layerCompatible) return false;
      return Math.hypot(object.x - point.x, object.y - point.y) <= object.radius + connectedTrack.width / 2 + 0.02;
    });
    if (!landsOnCopperObject) {
      danglingRows.push({
        net,
        layer,
        track_index: connectedTrack.index,
        x_mm: Number(point.x.toFixed(5)),
        y_mm: Number(point.y.toFixed(5)),
        width_mm: Number(connectedTrack.width.toFixed(5)),
        track_length_mm: Number(connectedTrack.length.toFixed(5)),
        review: "DANGLING_OR_STUB_END_REQUIRES_REVIEW",
      });
    }
  }
}

const powerJunctions = junctionRows.filter((row) => row.power_net);
const hardJunctions = junctionRows.filter((row) => row.review !== "T_JUNCTION_REVIEW");
const report = {
  schema: "R10-ROUTING-CULTURE-GATE-001",
  revision,
  source: path.relative(repo, source).replaceAll("\\", "/"),
  production_authority: "NOT_AUTHORIZED",
  criteria: {
    star_or_crossing: "effective degree >= 4",
    acute_branch: "minimum non-collinear angle < 30 degrees",
    abrupt_width_change: "width ratio >= 1.8 at a shared vertex",
    off_angle: "track >= 1 mm and > 5 degrees from 0/45/90 geometry",
    dangling_end: "single-degree track end not landing on a same-net pad or via",
  },
  counts: {
    tracks: tracks.length,
    junctions_total_review: junctionRows.length,
    junctions_hard_rework: hardJunctions.length,
    power_junctions_review: powerJunctions.length,
    dangling_or_stub_ends: danglingRows.length,
    long_off_angle_segments: offAngleRows.length,
    coincident_segment_groups: overlapRows.length,
  },
  gate: hardJunctions.length || danglingRows.length || offAngleRows.length || overlapRows.length ? "FAIL" : "PASS",
};

fs.mkdirSync(outputDir, { recursive: true });
writeCsv(path.join(outputDir, `${filePrefix}_узлы_ветвления.csv`), junctionRows);
writeCsv(path.join(outputDir, `${filePrefix}_тупики_и_обрывы.csv`), danglingRows);
writeCsv(path.join(outputDir, `${filePrefix}_длинные_неортогональные_сегменты.csv`), offAngleRows);
writeCsv(path.join(outputDir, `${filePrefix}_совпадающие_сегменты.csv`), overlapRows);
fs.writeFileSync(
  path.join(outputDir, `${filePrefix}_аудит_инженерной_культуры.json`),
  `${JSON.stringify(report, null, 2)}\n`,
  "utf8",
);
console.log(JSON.stringify(report, null, 2));
