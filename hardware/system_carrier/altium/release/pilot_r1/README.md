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
- Five-page color PCB layer reference with the composite, top, two internal
  copper layers and bottom. All pages were rendered and visually checked.
- Rezonit published four-layer TG150 working stack, TG170 alternative,
  material properties, process limits, mask, finish and mechanical data.

## Pilot package disposition

Archive assembly has no open blockers. The package is ready for internal CAM
review, Rezonit quotation and fabricator preflight. The published 1.50 mm TG150
four-layer 35 um construction is used as the working factory baseline.

The following corrections are deferred and do not block the archive:

1. Bind the exact finished thickness, finished copper and impedance solver
   geometries supplied for the order.
2. Replace the preliminary fabrication drawing with a released drawing before
   production authorization.
3. Enclosure manufacturing and populated component 3D are outside the current
   scope. Create antenna-mount 3D only if assembly technology requires it.

Production authority remains `NOT_AUTHORIZED`. The archive must not be
submitted as an authorized production order until the production release gate
is explicitly completed.

## Main files

- `fab/Gerber_X2_with_Legacy_Profile.zip`
- `fab/NC_Drill.zip`
- `fab/EVT_SYS_CARRIER.cvg`
- `fab/Fabrication_Drawing_PRELIMINARY.pdf`
- `fab/PCB_Layer_Reference_COLOR.pdf`
- `assembly/Pick_Place.zip`
- `assembly/BOM.csv`
- `assembly/BOM_NATIVE.csv`
- `assembly/AssemblyDrawing.pdf`
- `mechanical/EVT_SYS_CARRIER.step`
- `documentation/Schematic_Prints.pdf`
- `documentation/REZONIT_FABRICATION_BASELINE.md`
- `documentation/REZONIT_PUBLISHED_STACK_4L_35UM.csv`
- `validation/native_drc.drc`
- `validation/altium_equivalence_result.json`
- `validation/pilot_bom_enrichment_result.json`
- `validation/native_step_export_result.json`
- `validation/ipc2581_status_report.txt`
- `validation/native_ipc2581_export_result.json`
- `validation/native_color_layer_pdf_result.json`
- `PILOT_PACKAGE_STATUS.json`

The source PcbDoc SHA-256 is
`d897f5d82fe2c8de05a4588e369d4ed5114733777bc5509122cba06c749082cc`.
