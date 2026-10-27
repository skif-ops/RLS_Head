# EVT_SYS_CARRIER Rev.A pilot package

Prepared: 2026-10-27

This directory is the current pilot manufacturing package assembled from the
final native Altium project and its verified equivalence evidence.

Production authority is `NOT_AUTHORIZED`.

## Verified contents

- Native Altium schematic, PCB, project and OutJob sources.
- Gerber X2 copper, mask, legend and paste files.
- Native legacy GKO board profile bundled with the X2 files.
- Legacy RS-274X Gerber set for CAM fallback.
- NC drill files and report for 172 holes across 12 tools.
- Pick-and-place CSV and text exports.
- Validated 92-designator BOM with MPN binding.
- Two-page native Altium assembly drawing. The bottom page is intentionally
  empty because the board has no bottom population.
- Eight-page schematic PDF checked for sheet-boundary and readability issues.
- Native Altium DRC report with zero violations and zero unrouted nets.
- Compile, netlist, connection-integrity and Altium-equivalence PASS evidence.
- Preliminary fabrication drawing with outline, mounting datum, stack,
  impedance start values and drill table.

## Open release holds

1. IPC-2581 is absent. Altium 26.10.1 raised an exporter access violation and
   did not produce a file.
2. STEP is absent. Both direct and OutJob export attempts failed.
3. The Rezonit order-specific 1.60 mm stack, finished copper and field-solver
   impedance values are not yet bound. Generic published process data is
   included only as a preparation baseline.
4. The fabrication drawing is preliminary and derived from native Altium
   mechanical, stack and drill evidence. It is not a released Altium Draftsman
   document.
5. The BOM has validated designators and MPNs, but manufacturer and DNP columns
   are not populated in the available native-equivalence export.

These holds prevent production release. The package can be used for internal
CAM review and for obtaining the order-specific fabricator data. It must not be
submitted as an authorized production order until the holds are closed and the
production release gate passes.

## Main files

- `fab/Gerber_X2_with_Legacy_Profile.zip`
- `fab/NC_Drill.zip`
- `fab/Fabrication_Drawing_PRELIMINARY.pdf`
- `assembly/Pick_Place.zip`
- `assembly/BOM.csv`
- `assembly/AssemblyDrawing.pdf`
- `documentation/Schematic_Prints.pdf`
- `validation/native_drc.drc`
- `validation/altium_equivalence_result.json`
- `PILOT_PACKAGE_STATUS.json`

The source PcbDoc SHA-256 is
`d897f5d82fe2c8de05a4588e369d4ed5114733777bc5509122cba06c749082cc`.
