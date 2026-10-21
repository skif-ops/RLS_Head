# Issue #216: CI587 Altium EVT lock diagnostic

This directory preserves the PcbDoc and updated `20_MCU_CORE.SchDoc` after
native Altium Designer 26.10.1 edits to the CI587 import. The original
imported project, eight SchDocs and PcbLib remain in
`../ci587_2026-10-20/native_snapshot/`. The files here are diagnostic
snapshots, not the canonical `altium/native/` release files.

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

The original native schematic compile reported 6 errors and 155 warnings in
`../ci587_2026-10-20/compile_messages.txt`. The imported MCU sheet was A2
landscape, while 97 of its net labels and ports reached 19,400 mil in Y and
were reported off sheet. Changing only that native sheet to A1 landscape
removed those 97 warnings. A fresh Altium compile produced 6 errors and 58
warnings, recorded in
`equivalence_diagnostic/compile_after_mcu_sheet_a1.txt`. The five floating
input errors on unused Ethernet pins and the `RADAR_12V` power-pin/port
conflict remain. This compile is FAIL; the native sheet edit has not been
promoted to the canonical Altium design. A native BOM CSV export contains all
92 contracted designators in 62 grouped rows, but 77 designators have empty
MPN fields. `equivalence_diagnostic/bom_validation_result.json` is FAIL for
these 77 exact MPN mismatches. The CI587 KiCad source supplied MPN fields for
only 15 designators. The generator has now been changed to serialize the
authoritative BOM MPN for all 92 designators and to set the MCU sheet to A1.
A local KiCad 10 probe generated a parseable eight-sheet scaffold with 92/92
MPN fields and zero ERC violations; this does not qualify a new CI import
package or repair the already imported Altium project. CI #592 failed while
installing KiCad 9 because Launchpad returned HTTP 503 for PPA packages.
Complete keepout/connector datum, no-mmWave review, canonical import receipt
and full `ALTIUM_EQUIVALENCE_GATE` PASS remain absent.
Routing authority remains `NOT_AUTHORIZED`. Production authority remains
`NOT_AUTHORIZED`. Issue #216 remains open.
