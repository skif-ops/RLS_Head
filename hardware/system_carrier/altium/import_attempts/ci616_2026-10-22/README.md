# CI616 native Altium import diagnostic, 2026-10-22

This snapshot records the Altium import after the second readability pass on
`10_POWER_INPUT`. It is diagnostic evidence for issue #216. Routing and
production authority remain `NOT_AUTHORIZED`.

## Source and import

- Branch head `6dbd28b5811a975466c6c19572cfdaf4b5fcf09e` produced CI run
  `39805306503` (run 616). The completed System Carrier scaffold job uploaded
  `system-carrier-altium-import`, artifact ID `12436698327`. Its ZIP SHA-256 is
  `fcc8ace1b363b76a82a6099d36adef92fca3570a1425e12ae4cfb1dc950ddcd7`.
- Package integrity passed for 117/117 files. Current-source binding passed
  for 57/57 files before import. The source manifest and results are in
  `evidence/`.
- Altium Designer 26.10.1 Trial completed the KiCad Import Wizard from that
  package. Eight native SchDocs were saved in the uniquely named CI616 project.
  The `native_snapshot/` directory contains the saved project, eight SchDocs,
  two SchLibs, and the PcbDoc. File hashes and sizes are in
  `evidence/attempt_receipt.json`.
- The PcbDoc is a byte-identical carry-forward of the audited CI606 diagnostic
  board, SHA-256
  `f0c6f30b5a65c0eede9ac934c9d318be639f018fb15165f85cb1130926c08c9a`.
  This import did not create a new PCB. The 92 component footprints remain
  outside the board outline; placement and routing remain unfinished.

## Layout and native checks

- The revised [POWER_INPUT source render](../../layout_review/power_input_2026-10-22/power_input_source.png)
  shows the wider distribution on the A4 page, separated J1 and passive labels,
  and long names inside the frame. The saved CI616 `10_POWER_INPUT.SchDoc` was
  opened in Altium and inspected at full-sheet and local zoom. Automatic
  cross-references were disabled in the CI616 project to avoid long generated
  port suffixes outside the border. The previous CI614 import predates the
  second source layout pass.
- A targeted Altium ECO changed U7-6 from Power to Output and D3-6/7/9/10 plus
  J6-7 from Input to Passive. Before and after pin inventories show exactly
  these six changes.
- `Validate PCB Project` completed with zero errors and 49 warnings. The saved
  message list is `evidence/ci616_native_compile_after_eco.txt`. The warnings
  include IO pin/port direction conflicts, six floating net labels, and ten
  nets without a driving source. No warnings were suppressed.
- The project Protel netlist has 335 assigned pins in 67 connected groups.
  Comparison with the CI616 KiCad baseline passed with no missing connected
  pins, extra pins, merged groups, or split groups.
- Fresh read-only native PCB audit inventories passed PCB, pin map, stack,
  mechanical, pair/class, and rule validation. Footprint validation passed for
  all 92 components; connector validation passed for 22 pads. The hierarchy
  export passed all 66 native child-sheet port rows against the contract.
- A fresh Altium BOM export with one row per component passed exact designator
  and MPN comparison for all 92 parts. The default grouped export combined
  eight capacitors with different MPNs, so its first validation failed. Both
  raw exports and results are retained in `evidence/`; the ungrouped export is
  `ci616_native_bom.csv` and its validation is `ci616_native_bom_validation.json`.
- The saved root SchDoc and PcbDoc passed native file preflight.

## Gate state

The 49 compile warnings violate the zero-warning equivalence prerequisite.
No-mmWave human review and hash-bound exporter runtime receipts are still
outstanding. `ALTIUM_EQUIVALENCE_GATE` was not run.
The canonical `altium/native/` pair remains unpopulated.
`READY_FOR_ROUTING=false`; routing and production authority remain
`NOT_AUTHORIZED`. Issue #216 remains open.
