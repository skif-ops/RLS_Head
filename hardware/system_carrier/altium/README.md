# EVT System Carrier — Altium primary CAD

This directory is the primary PCB CAD location for the System Carrier.

## Current state

The electrical capture is ERC-clean in the retained KiCad flow. PCB implementation now targets Altium Designer. The project shell `EVT_SYS_CARRIER.PrjPcb` is committed here so the native Altium import has a fixed repository destination.

The binary native documents `native/EVT_SYS_CARRIER.SchDoc` and `native/EVT_SYS_CARRIER.PcbDoc` are intentionally **not fabricated by scripts**. They must be created/saved by Altium Designer.

## Import source

Use Altium Designer with the KiCad Importer extension:

1. File → Import Wizard.
2. Select **KiCad Design Files**.
3. Import the generated `EVT_SYS_CARRIER.kicad_pro` and all seven child `*.kicad_sch` sheets.
4. Include `SystemCarrier_Local.kicad_sym` and `SystemCarrier_Local.pretty`.
5. Output the native Altium project into this directory.
6. Save the imported schematic as `native/EVT_SYS_CARRIER.SchDoc`.
7. Create/transfer the PCB into `native/EVT_SYS_CARRIER.PcbDoc`.
8. Load the constraints from `ALTIUM_RULES_SYS_001.csv` and stack definition from `ALTIUM_LAYER_STACK_SYS_001.csv`.
9. Run the equivalence checks in `docs/CAD_POLICY_ALTIUM.md` before treating Altium as the implementation authority.

## Preservation rule

Do not delete any KiCad source, generated KiCad library or footprint used to establish the electrical baseline. KiCad is retained as an independent verification and recovery path.

## Manufacturing

All future Gerber/ODB++/IPC-2581, NC drill, pick-and-place, assembly drawings, fabrication drawings and STEP outputs for this board are to be released from the native Altium project after the equivalence gate passes.
