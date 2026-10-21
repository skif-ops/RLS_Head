# Issue #216: CI599 native Altium import diagnostic

CI run 39654845416 produced `system-carrier-altium-import` artifact
12372120369 at branch head `4f5c4e695804cee7196e9a0ee739492ccf529606`.
The downloaded ZIP SHA-256 is
`0ee790824e28983a73233cc47acbb3b15490324c2548b76bab1f22c5cdd32016`.
The local package verifier passed 115/115 files, and the current-source
binding passed 55/55 files before import. The evidence directory contains
both machine results and the package manifest.

Altium Designer 26.10.1 Trial completed the KiCad Import Wizard on the
verified `EVT_SYS_CARRIER.kicad_pro`, its root `.kicad_sch`, and
`SystemCarrier_Local.kicad_sym`. It saved a native project, eight SchDocs
and two SchLibs. The source package has no KiCad PCB. To examine the project
with a board attached, the saved CI587 EVT-lock PcbDoc was copied into the
working directory and added to the project. Altium could not initially match
its 92 components to the imported sheets by unique ID. It then created 92
links by designator and executed a checked ECO with no failed operations.
The ECO updated component parameters and removed the inherited EVT net and
pair classes. The qualified `ApplyEVTClasses` script restored ten required
classes and three differential pairs. The final saved PcbDoc is preserved in
`native_snapshot/`; its SHA-256 is
`f0c6f30b5a65c0eede9ac934c9d318be639f018fb15165f85cb1130926c08c9a`.
The ECO log is `evidence/pcb_eco.log`. This remains a diagnostic board, not
the canonical native PCB.

The Altium import-time compile reported 28 errors and 171 warnings. After
setting Global net-identifier scope and disabling port naming, a native
validation reported 21 errors and 176 warnings. Fifteen errors involve
multiple signals being merged into `3V3`, including output sheet entries
and duplicate net names. Five errors concern floating unused Ethernet
pins, and one concerns a `RADAR_12V` power-pin/output-port conflict.
The complete Altium message exports are retained in `evidence/`. Altium
subsequently raised an access violation in `WorkspaceManager.DLL`; the
project was saved, closed, and reopened. A second access violation dialog
was closed before the native BOM window could be used.

The native BOM window initially displayed 62 grouped line items. Its CSV
export is preserved as `evidence/native_bom_export.csv` with repository LF
line endings. The validator found all 92 designators but returned `FAIL`:
Altium's default Comment/Footprint grouping merged C13, C15, C20, C40, C62,
C64, C65 and C80 into a row with two distinct MPN values. That first result
is `evidence/native_bom_result.json`. After removing both grouping columns,
the native BOM window displayed 92 of 92 line items. The ungrouped export is
`evidence/native_bom_ungrouped_export.csv`, with the MPN column enabled. Its
exact designator-to-MPN comparison against the layout BOM returned `PASS`:
92 of 92 designators, no errors or warnings. The machine result is
`evidence/native_bom_ungrouped_result.json`. Altium's Excel export failed
because Microsoft Excel is not installed; both CSV exports succeeded.

The native project Protel netlist is preserved as
`evidence/schematic_protel_netlist.NET`. Its diagnostic comparison against
the qualified CI599 KiCad baseline reports `PASS`: 67 connected groups,
335 assigned pins, zero missing connected pins, zero extra pins, zero
merges and zero splits. The 148 intentionally unconnected KiCad pins are
absent from Protel netlists. This does not clear the native compiler's
21 errors.

The read-only Altium PCB exporter ran on the saved post-ECO board. Its ten
raw inventories are in `evidence/native_audit/`. Native audit returned
`PASS` for 92 components, 67 nets, the four-layer stack, board datum, ten
required rules, three differential pairs, ten classes, MCU pinmap and direct
symbol-pin checks. Separate validators returned `PASS` for 335 connected
physical endpoints in 67 groups against the qualified KiCad baseline,
92 footprint assignments and 22 connector pad mappings. The hierarchy
export initially contained no rows because the child SchDocs were not open.
After opening all seven child sheets and rerunning the Altium procedure, its
66 native port rows passed the hierarchy validator. The raw hierarchy CSV
and all validator results are retained in `evidence/native_audit/`.
The post-ECO native file preflight also passed. These subset checks do not
clear the compile failure or authorize routing. The component inventory
places zero of 92 component origins inside the 100 x 80 mm board bounding
box; all component X positions are at least 7,075 mil, while the board ends
at 3,937 mil.

The serialized SchDocs contain 92 physical component designators with 92
nonempty MPN parameters. Their values match the 92 rows of
`BOM_SYS_CARRIER_LAYOUT_004.csv` exactly. The diagnostic extracts Altium
CFB `FileHeader` records, matching `RECORD=34` designators and `RECORD=41`
MPN parameters by owner index; eight KiCad power flags are excluded. This
proves parameter import, and the ungrouped native BOM now passes exact
designator-to-MPN validation. The CFB
preflight passes only the nontrivial native-file format check and does not
establish electrical equivalence.

Native compile repair, placement of all 92 components inside the board,
no-mmWave review, complete equivalence evidence and
`ALTIUM_EQUIVALENCE_GATE` PASS remain outstanding. The canonical
`altium/native/` files and `import_receipt.json` have not been promoted.
The local handoff evaluator still reports `WAITING_NATIVE_IMPORT`. Routing
authority and production authority remain `NOT_AUTHORIZED`;
`READY_FOR_ROUTING` is false, and issue #216 remains open.
