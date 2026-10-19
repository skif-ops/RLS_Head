# CAD authority: Altium Designer

Effective from the System Carrier Rev.A PCB implementation phase, **Altium Designer is the primary CAD environment for PCB work in this repository**.

## Authority

- New PCB layout, rules, stackup, fabrication outputs and assembly outputs are authored in Altium Designer.
- Native Altium files are authoritative for PCB implementation after the Altium equivalence gate passes.
- Existing KiCad sources are retained permanently. They are not deleted, rewritten away or treated as disposable conversion files.
- The ERC-clean KiCad System Carrier capture remains the independent electrical reference used to verify the first Altium import.

## System Carrier transition

The import baseline is the ERC-clean System Carrier generated from repository commit `f23476e94428295f080b526143dc114f68883635` or a later electrically equivalent commit.

Altium Designer officially supports importing KiCad `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_sym` and `*.kicad_mod` files through the KiCad Importer extension and Import Wizard. The import result is a native Altium PCB project.

Repository target paths:

```text
hardware/system_carrier/altium/
├── EVT_SYS_CARRIER.PrjPcb
├── ALTIUM_IMPORT_PROFILE_SYS_001.json
├── ALTIUM_LAYER_STACK_SYS_001.csv
├── ALTIUM_RULES_SYS_001.csv
└── native/
    ├── EVT_SYS_CARRIER.SchDoc
    └── EVT_SYS_CARRIER.PcbDoc
```

The native `SchDoc` and `PcbDoc` are committed when created by Altium Designer. They must not be replaced by hand-crafted files that only mimic the extension.

## Equivalence gate before layout authority changes

The first native Altium import must satisfy all of the following before PCB routing is considered authoritative:

1. Altium project compiles with zero electrical errors and zero warnings relevant to the imported design.
2. Component designators and MPN anchors match `BOM_SYS_CARRIER_003.csv`.
3. MCU pin assignments match `PINMAP_SYS_001.csv`.
4. Connector pinouts match `CONNECTOR_PINOUT_SYS_001.csv`.
5. Nets and sheet interfaces match `NETLIST_SYS_001.csv` and `HIERARCHY_INTERFACE_SYS_001.csv`.
6. Footprints match `FOOTPRINT_PLAN_SYS_001.csv`.
7. The PCB rule set implements every P0/P1 item in `PCB_LAYOUT_CONSTRAINTS_SYS_001.csv`.
8. No 76–81 GHz RF routing or antenna implementation is added to the System Carrier.
9. KiCad sources remain present and buildable as the verification baseline.

Until this gate passes, the Altium project is the **target CAD**, while the ERC-clean KiCad schematic remains the electrical comparison reference.

## Future boards

The same policy applies to every new PCB added to this repository: start the PCB implementation in Altium Designer. KiCad may be retained for independent verification, conversion provenance or historical recovery, but it is not to replace the Altium primary source once the native Altium gate is passed.

## Pre-layout mechanical status

System Carrier Rev.A currently uses a 100 x 80 x 1.6 mm `EVT_PROVISIONAL` envelope for Altium placement/routing preparation. Native placement may begin only after the Altium equivalence gate passes. Production release additionally requires enclosure/mechanical freeze; the provisional envelope must not be interpreted as that freeze.
