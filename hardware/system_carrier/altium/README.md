# EVT System Carrier Altium workflow

This directory is the primary CAD and production-output location for the System Carrier.

## Current ECO state

The retained KiCad capture now defines two 3.3 V host UART channels, an external simpleRTK3B Pro / mosaic-X5 GNSS connection on JST-GH J8, a fixed 5 V GNSS supply from U9 and no Ethernet or onboard GNSS RF path.

The existing files under `native/`, `equivalence/`, `routing/` and `release/` were created from the superseded Ethernet and onboard-GNSS design. They are historical evidence only. They do not authorize routing or release for the current ECO.

The current lifecycle is:

1. regenerate and validate the KiCad import source;
2. bind a qualified import package to the exact current source;
3. import all eight schematic sheets into Altium Designer;
4. save real `native/EVT_SYS_CARRIER.SchDoc` and `native/EVT_SYS_CARRIER.PcbDoc` files;
5. compile the native project and run the read-only hierarchy, BOM, footprint, pinmap, connector, netlist, rule, stack and no-mmWave audits;
6. require `ALTIUM_EQUIVALENCE_GATE=PASS` before routing is authorized;
7. implement and validate the compact board candidate in native Altium;
8. generate the complete pilot package from the Altium OutJob.

Production authority remains `NOT_AUTHORIZED` throughout this work.

## Native import

Use the qualified KiCad Importer extension and the current package identified by `ALTIUM_IMPORT_PROFILE_SYS_001.json`. The hierarchy has the root schematic plus these seven child sheets:

- `10_POWER_INPUT.kicad_sch`
- `20_MCU_CORE.kicad_sch`
- `30_TIME_GNSS.kicad_sch`
- `40_IMU.kicad_sch`
- `50_RADAR_IO_CAN.kicad_sch`
- `60_HOST_UART.kicad_sch`
- `70_DEBUG_BOOT.kicad_sch`

Include `SystemCarrier_Local.kicad_sym` and `SystemCarrier_Local.pretty`. Save the resulting native documents at the exact paths in the import profile. Do not create extension-only placeholders or synthetic Altium binaries.

Immediately after import, preserve the Import Wizard log and create the SHA-bound import receipt. A receipt created from an older source or package is invalid.

## Compact board candidate

The former 100 x 80 mm outline is the maximum envelope. `ALTIUM_BOARD_MECHANICAL_SYS_001.csv` and `ALTIUM_PLACEMENT_COORD_SYS_002.csv` define a 90 x 70 mm candidate with four M3 NPTH holes. This candidate is not locked until native placement, routing, mounting clearance, connector mating access, cable access and DRC pass.

If the candidate fails any of those checks, enlarge only the constrained dimension by the minimum justified amount and record the evidence. Do not trade power-loop integrity, connector access, return paths or assembly spacing for board area.

## Pilot stack and routing

The selected Rezonit pilot baseline is four layers, 1.60 mm board thickness and 35 um copper. L2 is continuous GND. L3 carries power and slow signals. The current design needs no controlled-impedance structure because Ethernet MDI and onboard GNSS RF are absent.

Routing priority is:

1. U5 and U9 switch-current loops;
2. protected 12 V, 3V3, 5V_GNSS and RADAR_12V distribution;
3. clock and timing nets;
4. CAN-FD;
5. host UART and external GNSS UART/PPS;
6. IMU SPI, SWD, debug and remaining signals;
7. planes, return vias and final copper balancing.

Use `ALTIUM_RULE_QUERY_SYS_001.csv`, `ALTIUM_NET_CLASSES_SYS_001.csv`, `ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv` and the routing lock files as the native rule source.

## Altium-only release outputs

Every current schematic and production document must originate in the native Altium project. The OutJob must generate:

- color compiled schematic PDF with readable sheet use and no overlaps or clipping;
- color PCB layer PDF with each copper, mask, overlay, drill and mechanical layer identified;
- color top, bottom and multilayer composite PCB views;
- BOM and pick-and-place;
- assembly drawings for both sides;
- fabrication drawing and drill table;
- Gerber X2 and NC Drill;
- IPC-2581 and ODB++ when requested;
- STEP;
- compile/ERC, DRC and netlist-equivalence reports;
- release manifest with hashes and authority state.

KiCad exports, hand-generated fabrication PDFs and superseded Altium outputs cannot be included in the current production archive.

## Release gate

The release checklist is `ALTIUM_RELEASE_CHECKLIST_SYS_001.csv`. A pilot archive is complete only when all required outputs are current, the native compile and DRC pass, the equivalence gate passes, the compact outline is validated and the release manifest states:

```text
primary CAD = Altium Designer
routing authority = authorized only by the current equivalence result
production authority = NOT_AUTHORIZED
```
