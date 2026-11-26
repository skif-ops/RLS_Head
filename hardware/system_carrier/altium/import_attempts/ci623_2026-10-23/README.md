# CI623 canonical Altium import and equivalence, 2026-10-23

This record captures the qualified native Altium import used to complete
issue #216. The canonical native files passed the equivalence gate and are
ready for PCB routing. Production authority remains `NOT_AUTHORIZED`.

## Qualified source and import

- Source commit `0584de2d096457135073493c1f97d3f506f5d54a` produced GitHub
  Actions run `39943400259`. Its `system-carrier-altium-import` artifact ID
  is `12496479601`; the downloaded ZIP SHA-256 is
  `f3dfc3293be5845a40e420e30507a7486c99c26a01285332b941225df7ffc514`.
- Package verification passed 117/117 files. Current-source binding passed
  57/57 files at import time. The immutable import-time results are retained
  in `evidence/`.
- Altium Designer 26.10.1 Trial completed the KiCad import. The canonical
  snapshot contains the root and seven child SchDocs, the PcbDoc, and two
  SchLibs. Exact hashes and sizes are recorded in
  `evidence/attempt_receipt.json`.

## Native corrections and review

- All eight schematic sheets were reviewed in Altium after the layout pass.
  Functional content is distributed across each drawing sheet, overlapping
  designators and component text were separated, and long labels on
  `10_POWER_INPUT` were kept inside the drawing frame.
- Guarded native ECOs aligned imported electrical pin types with the fixed
  contracts, removed six obsolete flag labels, and left the intentionally
  unused U8.2 and U8.4 pads without a net. The exact ECO scripts and projects
  are retained in `evidence/`.
- The locked EVT mechanical datum, four-layer routing stack, power routing
  rules, net classes, differential pairs, and rule constraints are present
  in the saved PcbDoc. The 22 contracted placement anchors are applied. The
  remaining placement and routing work belongs to the authorized routing
  phase.

## Verification

- Altium native compile passed at 2026-10-23 19:44:32 Europe/Moscow with
  zero errors and zero warnings.
- Native PCB audit, native file preflight, footprint comparison for all 92
  components, connector pinout, PCB netlist, and the 66-row hierarchy
  comparison passed.
- The current native BOM preview was reviewed in Altium. Because Excel is
  not installed and the CSV selector could not be operated reliably, the
  canonical CSV is the unchanged CI616 ungrouped native Altium export. It
  was revalidated against the same current 92-designator BOM contract and
  passed every designator and MPN comparison.
- The audit and hierarchy exporter procedures ran in Altium; their
  hash-bound runtime receipt passed. The static script API check and the
  no-mmWave review also passed.
- EVT mechanical datum, routing stack, and power routing gates passed. The
  final native CI gate passed in the post-equivalence phase.

## Authority state

`ALTIUM_EQUIVALENCE_GATE` is `PASS`. The project state is
`READY_FOR_ROUTING`, and PCB routing authority is `AUTHORIZED`.
Production authority remains `NOT_AUTHORIZED`.
