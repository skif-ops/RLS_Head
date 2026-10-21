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
working directory and added to the project. The PcbDoc in `native_snapshot/`
is byte-identical to that older diagnostic board. No schematic-to-PCB ECO
from the CI599 sheets has been applied, so it is not a CI599-equivalent PCB.

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

The native BOM window displayed 62 grouped line items. Its CSV export is
preserved as `evidence/native_bom_export.csv` with repository LF line endings. The native BOM
validator found all 92 designators but returned `FAIL`: Altium's default
Comment/Footprint grouping merged C13, C15, C20, C40, C62, C64, C65 and C80
into a row with both `100nF_6.3V_X7R` and `100nF_16V_X7R` in its MPN cell.
The exact validator output is `evidence/native_bom_result.json`. The BOM
export's MPN column was enabled before export. An attempted change to the
grouping did not produce a verified corrected export. Altium's Excel export
also failed because Microsoft Excel is not installed; CSV export succeeded.

The native project Protel netlist is preserved as
`evidence/schematic_protel_netlist.NET`. Its diagnostic comparison against
the qualified CI599 KiCad baseline reports `PASS`: 67 connected groups,
335 assigned pins, zero missing connected pins, zero extra pins, zero
merges and zero splits. The 148 intentionally unconnected KiCad pins are
absent from Protel netlists. This does not clear the native compiler's
21 errors or verify the attached older PCB.

The serialized SchDocs contain 92 physical component designators with 92
nonempty MPN parameters. Their values match the 92 rows of
`BOM_SYS_CARRIER_LAYOUT_004.csv` exactly. The diagnostic extracts Altium
CFB `FileHeader` records, matching `RECORD=34` designators and `RECORD=41`
MPN parameters by owner index; eight KiCad power flags are excluded. This
proves parameter import, while the native BOM export still fails exact
designator-to-MPN validation. The CFB
preflight passes only the nontrivial native-file format check and does not
establish electrical equivalence.

The CI599 PCB ECO, PCB pad-net and hierarchy comparison, full rule and
stack audit against the new schematics, placement, no-mmWave review, and
`ALTIUM_EQUIVALENCE_GATE` PASS remain outstanding. The canonical
`altium/native/` files and `import_receipt.json` have not been promoted.
The local handoff evaluator still reports `WAITING_NATIVE_IMPORT`. Routing
authority and production authority remain `NOT_AUTHORIZED`;
`READY_FOR_ROUTING` is false, and issue #216 remains open.
