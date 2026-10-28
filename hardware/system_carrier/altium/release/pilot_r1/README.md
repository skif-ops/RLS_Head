# EVT_SYS_CARRIER Rev.A pilot package

Prepared: 2026-10-28

This directory is the current pilot manufacturing package assembled from the
final native Altium project and its verified equivalence evidence.

Production authority is `NOT_AUTHORIZED`.

## Verified contents

- Native Altium schematic, PCB, project and OutJob sources.
- Gerber X2 copper, mask, legend and paste files.
- Native legacy GKO board profile bundled with the X2 files.
- Legacy RS-274X Gerber set for CAM fallback.
- NC drill files and report for 172 holes across 12 tools.
- Native Altium IPC-2581 Revision B export. XML and content-structure checks
  confirm 92 components, 20 layers, 172 holes and 68 named nets.
- Pick-and-place CSV and text exports.
- Validated 92-designator BOM with MPN, manufacturer, population, DNP and
  procurement binding. The unchanged native Altium export is retained beside
  it as `BOM_NATIVE.csv`.
- `PILOT_BASE_REV_A` population is fixed at 84 fitted parts, 5 DNP parts and
  3 PCB-only features. The optional GNSS active-antenna bias network is DNP.
- Two-page native Altium assembly drawing. The bottom page is intentionally
  empty because the board has no bottom population.
- Eight-page schematic PDF checked for sheet-boundary and readability issues.
- Native Altium DRC report with zero violations and zero unrouted nets.
- Compile, netlist, connection-integrity and Altium-equivalence PASS evidence.
- Native Altium STEP with board outline, thickness and hole geometry. The rigid
  board export succeeds with `Export Folded Board` disabled.
- Preliminary fabrication drawing with outline, mounting datum, stack,
  impedance start values and drill table.

## Open release holds

1. The native STEP contains the board solid and holes, but no component 3D
   bodies were available. Connector access, mating-plug clearance and enclosure
   Z clearance therefore remain open.
2. The Rezonit order-specific 1.60 mm stack, finished copper and field-solver
   impedance values are not yet bound. Generic published process data is
   included only as a preparation baseline.
3. The fabrication drawing is preliminary and derived from native Altium
   mechanical, stack and drill evidence. It is not a released Altium Draftsman
   document.
These holds prevent production release. The package can be used for internal
CAM review and for obtaining the order-specific fabricator data. It must not be
submitted as an authorized production order until the holds are closed and the
production release gate passes.

## Main files

- `fab/Gerber_X2_with_Legacy_Profile.zip`
- `fab/NC_Drill.zip`
- `fab/EVT_SYS_CARRIER.cvg`
- `fab/Fabrication_Drawing_PRELIMINARY.pdf`
- `assembly/Pick_Place.zip`
- `assembly/BOM.csv`
- `assembly/BOM_NATIVE.csv`
- `assembly/AssemblyDrawing.pdf`
- `mechanical/EVT_SYS_CARRIER.step`
- `documentation/Schematic_Prints.pdf`
- `validation/native_drc.drc`
- `validation/altium_equivalence_result.json`
- `validation/pilot_bom_enrichment_result.json`
- `validation/native_step_export_result.json`
- `validation/ipc2581_status_report.txt`
- `validation/native_ipc2581_export_result.json`
- `PILOT_PACKAGE_STATUS.json`

The source PcbDoc SHA-256 is
`d897f5d82fe2c8de05a4588e369d4ed5114733777bc5509122cba06c749082cc`.
