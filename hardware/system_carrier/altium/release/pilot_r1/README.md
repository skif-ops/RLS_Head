# EVT_SYS_CARRIER Rev.A pilot package

Prepared: 2026-10-30

This directory is the current pilot manufacturing package assembled from the
native Altium project and evidence bound to the same schematic and PCB files.

Production authority is `NOT_AUTHORIZED`.

## Verified contents

- Native Altium schematic, PCB, project and OutJob sources.
- Gerber X2 and legacy RS-274X files for four copper layers, mask, legend,
  paste, board profile and drill plots.
- NC drill files for 146 holes across 9 tools.
- Native Altium IPC-2581 Revision B export. Structural checks confirm 83
  components, 30 packages, 21 layers, 146 holes and 55 named nets.
- Pick-and-place data for 83 top-side components and no bottom-side parts.
- Validated 83-designator BOM. The `PILOT_BASE_REV_A` variant contains 78
  fitted parts, 2 DNP parts and 3 PCB-only features.
- Two-page native Altium assembly drawing. The bottom view is intentionally
  empty because the board has no bottom population.
- Eight-page native schematic PDF visually checked for sheet-boundary and
  readability problems.
- Native Altium DRC with zero violations, zero unrouted nets, zero routing
  topology violations and zero net-antenna violations.
- Compile, netlist, footprint, hierarchy, connection-integrity,
  no-mmWave and Altium-equivalence PASS evidence.
- Native STEP for the current 90.00 x 70.00 mm board. The direct export uses
  all pad holes and disables `Export Folded Board` for this rigid PCB.
- Five-page native color fabrication plot set with the multilayer composite,
  top, two internal copper layers and bottom.
- Rezonit published four-layer TG150 working stack, TG170 alternative,
  material properties, process limits, mask, finish and mechanical data.

The canonical external interfaces are two 3.3 V UART channels and a
connectorized external GNSS module. Ethernet is not part of this revision.

## Pilot package disposition

The package is ready for internal CAM review, Rezonit quotation and pilot
preflight. The published Rezonit four-layer TG150 construction is the working
factory baseline until order-specific data is available.

The following items remain production-release holds, but do not block pilot
archive review:

1. Bind exact finished thickness, finished copper and any order-specific
   process values supplied for the order.
2. Replace the native plot set with a released Draftsman fabrication drawing
   before production authorization.
3. Complete enclosure and connector-access verification if enclosure work
   enters scope. Only antenna-mount 3D is required when assembly technology
   makes it necessary.

Production authority remains `NOT_AUTHORIZED`. This package must not be used
as an authorized production order until the production release gate passes.

## Main files

- `fab/Gerber_X2_with_Legacy_Profile.zip`
- `fab/NC_Drill.zip`
- `fab/EVT_SYS_CARRIER.cvg`
- `fab/Fabrication_Drawing_PILOT_R1.pdf`
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
- `validation/connection_integrity_result.json`
- `validation/footprint_comparison.html`
- `validation/altium_equivalence_result.json`
- `validation/pilot_bom_enrichment_result.json`
- `validation/native_step_export_result.json`
- `validation/native_ipc2581_export_result.json`
- `validation/native_color_layer_pdf_result.json`
- `PILOT_PACKAGE_STATUS.json`

The source schematic SHA-256 is
`85b458cc95d32704a9a9dced80f2f8514bf2f9d3065e0f91c18ab57091dc9166`.

The source PcbDoc SHA-256 is
`35f59c07ddb145f5cc46692d40d5f17ac8899e21b2412f1a75bb75427504797d`.
