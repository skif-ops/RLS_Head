# CI614 native Altium import diagnostic, 2026-10-22

This snapshot records the new import after spreading the `10_POWER_INPUT`
schematic across its A4 page. It is diagnostic evidence for issue #216.
Routing and production authority remain `NOT_AUTHORIZED`.

## Source and native files

- Branch head `36748be8b4b35e509c5ba9d13e388eb0f852600d` passed CI run
  `39787477019` (run 614). The `system-carrier-altium-import` artifact ID is
  `12428539103`; its ZIP SHA-256 is
  `0a2e283912cb14e48957fdc3f56fbfb86efdf72530460e4cd9abacc00be348da`.
- Package verification passed 117/117 files. Current-source binding passed
  57/57 files before import and on recheck. The package manifest and results
  are retained in `evidence/`.
- Altium Designer 26.10.1 Trial completed the KiCad Import Wizard using the
  CI614 `.kicad_pro`, root `.kicad_sch`, and local symbol library. The eight
  native SchDocs were saved. The qualified check copy has a unique project
  filename so Altium cannot confuse it with simultaneously open older imports.
- `native_snapshot/EVT_SYS_CARRIER.PcbDoc` is byte-identical to the previously
  audited CI606 diagnostic PCB, SHA-256
  `f0c6f30b5a65c0eede9ac934c9d318be639f018fb15165f85cb1130926c08c9a`.
  It was attached to the CI614 project in Altium. This import did not create
  a new PCB. The carried board still needs placement and routing.
- All eight saved SchDocs and the PcbDoc passed CFB/OLE file checks. The
  root schematic and PCB pair passed the native file preflight. File hashes
  and sizes are in `evidence/attempt_receipt.json`.

## Layout and electrical checks

- The [POWER_INPUT source preview](../ci606_2026-10-22/evidence/layout_review/power_input_source_eco.png)
  shows the new distribution, wider power IC symbols, separated pin labels,
  and long names inside the A4 border. The imported `10_POWER_INPUT.SchDoc`
  was opened in Altium with its full drawing frame visible. Automatic cross
  references were disabled in the project to prevent long generated port
  suffixes from crossing the sheet edge.
- The guarded Altium ECO changed U7-6 from Power to Output and D3-6/7/9/10
  plus J6-7 from Input to Passive. Those five pins remain intentionally
  unconnected. The before and after pin inventories show exactly six changes.
- Altium `Validate PCB Project` reported **zero errors and 49 warnings** after
  the ECO, with `Compile successful, no errors found`. The complete saved
  message list is `evidence/ci614_native_compile_after_eco.txt`.
- A fresh project Protel netlist contains 335 assigned pins in 67 groups.
  `evidence/ci614_schematic_netlist_probe.json` passes comparison with the
  CI614 KiCad baseline: no missing connected pins, extra pins, merged groups,
  or split groups.
- The read-only `ExportNativeAudit` procedure ran on the CI614 project's
  carried PcbDoc. All ten fresh inventories are in `evidence/native_audit/`.
  Native PCB, pin map, four-layer stack, mechanical, pair/class, and rule
  checks pass. The fresh footprint check covers all 92 components, and the
  connector check covers 22 native pads; both pass.
- After loading all seven child SchDocs, `ExportNativeHierarchy` produced 66
  native port rows. The hierarchy validator passes all 66 rows against the
  contract and the fresh pad/net inventory.

## Gate state

The 49 compile warnings remain, including pin and port direction conflicts,
floating net labels, nets without driving sources, and one sheet-entry
direction conflict. The zero-warning equivalence prerequisite is therefore
not met. Fresh CI614 BOM, no-mmWave human review, and hash-bound exporter
runtime receipts are also outstanding. The carried PCB has fresh audit
evidence, but all 92 component origins remain outside the board outline and
placement/routing are unfinished. The source layout still has crowded labels
near J1 and several vertical passive components, so the visual fix also
remains incomplete.

`ALTIUM_EQUIVALENCE_GATE` was not run. The canonical `altium/native/` pair
remains unpopulated. `READY_FOR_ROUTING=false`; routing authority and
production authority remain `NOT_AUTHORIZED`.
