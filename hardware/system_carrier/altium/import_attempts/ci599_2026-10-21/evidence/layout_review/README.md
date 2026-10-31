# CI599 schematic page layout review, 2026-10-22

The CI599 source and its genuine imported Altium SchDocs place the circuit
content in the upper-left corner of oversized pages. The problem is in the
generated KiCad placement, not only in Altium's zoom setting. The source
`20_MCU_CORE.kicad_sch` uses A1, but the imported MCU symbol and attached
connections reach 26,300 mil (668 mm) in Y, about 74 mm beyond that page.
Altium's diagnostic A0 page change removed off-sheet compile warnings but
did not repair the source layout.

The table uses the saved CI599 native `FileHeader` records. Functional bounds
include components, pins, wires, labels, ports and sheet symbols, and exclude
the imported drawing frame and title block. Values are rounded to 1 mm.

| Sheet | CI599 page | Functional bounds | Page share, width x height |
| --- | --- | --- | --- |
| EVT_SYS_CARRIER | A2, 594 x 420 mm | 201 x 201 mm | 34% x 48% |
| 10_POWER_INPUT | A2, 594 x 420 mm | 81 x 71 mm | 14% x 17% |
| 20_MCU_CORE | A0 diagnostic, 1189 x 841 mm | 109 x 234 mm | 9% x 28% |
| 30_TIME_GNSS | A2, 594 x 420 mm | 65 x 56 mm | 11% x 13% |
| 40_IMU | A2, 594 x 420 mm | 32 x 27 mm | 5% x 6% |
| 50_RADAR_IO_CAN | A2, 594 x 420 mm | 60 x 36 mm | 10% x 8% |
| 60_ETHERNET | A2, 594 x 420 mm | 113 x 89 mm | 19% x 21% |
| 70_DEBUG_BOOT | A2, 594 x 420 mm | 13 x 20 mm | 2% x 5% |

The [CI599 MCU](ci599_mcu_source.png) and
[power](ci599_power_source.png) exports show the source pages. The MCU
symbol is clipped at the top of its A1 source page. The native Altium
`View > Fit Document` view showed the same upper-left concentration.

The generator layout ECO on this branch assigns A2 to the root hierarchy,
A3 to MCU and A4 to the other child sheets. It arranges the root symbols
on a 3-column grid, moves the MCU symbol fully inside A3, centers the
child circuitry, and hides the generated `hierarchy_path` and BOM `MPN`
properties in the drawing while retaining their values. A local
[eight-page preview](layout_eco_local_preview.png) was rendered with
KiCad 10.0.6. The sparse IMU and DEBUG_BOOT sheets still contain substantial
blank space because their contracted circuits have only four and two
physical components, respectively.

Local KiCad 10.0.6 ERC reported zero violations for both CI599 and the
layout ECO. KiCad XML netlists matched exactly by net name and sorted
reference/pin endpoints: 215 nets and 483 endpoints in each. All 92
component references and their 92 MPN values also matched. This verifies
that the layout ECO did not change the KiCad electrical connectivity or BOM
identity in the local comparison. It does not constitute native Altium
equivalence.

The CI599 import package is now stale against the changed generator:
current-source binding fails on `tools/generate_system_carrier_schematic.py`.
A new qualified CI import package, native reimport, compile, audit and full
`ALTIUM_EQUIVALENCE_GATE` PASS are required before promotion. Routing and
production authority remain `NOT_AUTHORIZED`.

The qualified CI606 reimport and native page measurements are recorded in
[the CI606 diagnostic attempt](../../../ci606_2026-10-22/README.md). Its initial
native compile still has six errors and 59 warnings, so it remains diagnostic.
