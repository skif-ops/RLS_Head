# Issue #216: CI587 Altium EVT lock diagnostic

This directory preserves the PcbDoc after native Altium Designer 26.10.1
edits to the CI587 import. The original imported project, eight SchDocs and
PcbLib remain in `../ci587_2026-10-20/native_snapshot/`. The PcbDoc here is a
diagnostic snapshot, not the canonical `altium/native/` release file.

The source package was qualified before import: CI run 39490119592, artifact
12296185608, 112/112 files verified and 52/52 source bindings matched at
import time. The current checkout has since changed the audit script and
script project. `equivalence_diagnostic/current_source_binding.json` is FAIL
for those two files. A newly qualified package is required before canonical
promotion; the older import receipt must not be relabeled as current-source
qualified.

The saved PcbDoc now contains the ten named EVT routing rules, including
locked differential-pair width/gap and power-net width values. The Altium
audit exported each required numeric value on all four copper layers. The
board shape is 100 x 80 mm with four 3 mm corner arcs. Four 3.2 mm NPTH
mounting holes are at (5,5), (95,5), (5,75) and (95,75) mm. The copper stack
has the four contracted layers, nominal 35 µm copper and 0.18 / 1.10 / 0.18
mm interlayer dielectrics with Er 4.2. Three native differential pairs and
the required pair/net classes have the contracted membership.

`equivalence_diagnostic/native_audit_result.json` is PASS for its defined
subset: 92 components, 67 named nets, ten required rules with numeric values,
the layer stack, mechanical datum, three pairs, ten required classes, MCU
pinmap and direct symbol-pin checks. It reports repeated member names in ten
classes as warnings after repeated class-script execution. The required
members are present, but this remains a native review item. The saved native
file preflight, 67-group physical netlist comparison and hierarchy validation
also pass. These subset results do not authorize routing.

The last native schematic compile still reports 6 errors and 155 warnings,
recorded in `../ci587_2026-10-20/compile_messages.txt`. No new zero-error
compile, native BOM, complete keepout/connector datum, no-mmWave review,
canonical import receipt or full `ALTIUM_EQUIVALENCE_GATE` PASS is recorded.
Routing authority remains `NOT_AUTHORIZED`. Production authority remains
`NOT_AUTHORIZED`. Issue #216 remains open.
