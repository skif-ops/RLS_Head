# EVT system carrier schematic layout review, 2026-10-23

This review compares the CI616 qualified KiCad source with a newly generated candidate from this branch. It addresses undersized sheet content, overlapping names and components, and text extending toward page borders. These images are KiCad renders; the candidate has not yet been imported into Altium.

| Sheet | CI616 | Candidate |
| --- | --- | --- |
| Root hierarchy | [before](before_ROOT.png) | [after](ROOT.png) |
| Power input | [before](before_POWER_INPUT.png) | [after](POWER_INPUT.png) |
| MCU core | [before](before_MCU_CORE.png) | [after](MCU_CORE.png) |
| Time/GNSS | [before](before_TIME_GNSS.png) | [after](TIME_GNSS.png) |
| IMU | [before](before_IMU.png) | [after](IMU.png) |
| Radar I/O/CAN | [before](before_RADAR_IO_CAN.png) | [after](RADAR_IO_CAN.png) |
| Ethernet | [before](before_ETHERNET.png) | [after](ETHERNET.png) |
| Debug/boot | [before](before_DEBUG_BOOT.png) | [after](DEBUG_BOOT.png) |

The [candidate PDF](all_sheets.pdf) contains all eight sheets at their intended page sizes. Child-sheet spacing, component positions, label stubs, and long visible values were revised. The IMU symbol body was widened so its contracted pin names fit. Sparse IMU and debug sheets retain A4 page frames and some blank space.

Verification of the generated candidate:

- [KiCad ERC](erc.rpt): 0 errors, 0 warnings.
- [CAD scaffold validation](scaffold_validation.json): PASS; 92 BOM MPNs and 92 footprint assignments verified; no placeholders.
- [Netlist pin-contract validation](netlist_contract_validation.json): PASS; 483 connected physical endpoints.
- [Netlist group comparison](netlist_group_comparison.json): all 67 physical connection groups retained after excluding the two deliberate GNSS pin-contract corrections. Five local net names changed with no endpoint-group change.
- U8.2 `D_SEL` is now unconnected rather than on GND; U8.4 `EXTINT` is now explicitly NC rather than on 3V3, as required by `SYMBOL_PIN_CONTRACT_SYS_001.csv`.

Native Altium visual inspection, compile, BOM, netlist, hierarchy, no-mmWave audit, and equivalence must be repeated on a qualified package built from this candidate. Until `ALTIUM_EQUIVALENCE_GATE=PASS`: `routing authority=NOT_AUTHORIZED`, `production authority=NOT_AUTHORIZED`, and `READY_FOR_ROUTING` is not asserted.
