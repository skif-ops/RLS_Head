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
project was saved, closed, and reopened. The native BOM window opened, but
no BOM export from this attempt was saved.

The serialized SchDocs contain 92 physical component designators with 92
nonempty MPN parameters. Their values match the 92 rows of
`BOM_SYS_CARRIER_LAYOUT_004.csv` exactly. The diagnostic extracts Altium
CFB `FileHeader` records, matching `RECORD=34` designators and `RECORD=41`
MPN parameters by owner index; eight KiCad power flags are excluded. This
proves parameter import, not the required native BOM export. The CFB
preflight passes only the nontrivial native-file format check and does not
establish electrical equivalence.

The CI599 PCB ECO, native netlist and hierarchy comparison, full rule and
stack audit against the new schematics, placement, no-mmWave review, and
`ALTIUM_EQUIVALENCE_GATE` PASS remain outstanding. The canonical
`altium/native/` files and `import_receipt.json` have not been promoted.
The local handoff evaluator still reports `WAITING_NATIVE_IMPORT`. Routing
authority and production authority remain `NOT_AUTHORIZED`;
`READY_FOR_ROUTING` is false, and issue #216 remains open.
