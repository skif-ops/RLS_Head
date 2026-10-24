# CI581 cold-reload schematic netlist probe

The original CI581 diagnostic Altium project was reopened from disk in Altium Designer 26.10.1 Trial on 2026-10-20. `compile_cold_reload_automatic.txt` records **33 errors and 156 warnings** after Project > Validate. This differs from the 54/169 immediate-import capture retained in the parent attempt; the cause of that difference is not proven. The executed CI581 PCB ECO and its 48-net board were not regenerated or accepted here.

Each `.NET` file was exported with Design > Netlist For Project > Protel. The paired JSON compares the native groups with the qualified CI581 KiCad 483-endpoint baseline using `tools/altium_protel_netlist_probe.py`. Protel omits the 148 intentionally unconnected baseline pins, so they are counted separately. These netlists come from the **schematic project**, not from the PCB.

| Project net identifier scope and diagnostic edit | Native groups | Assigned physical pins | Missing connected pins | Source nets split | Cross-net mergers |
| --- | ---: | ---: | ---: | ---: | ---: |
| Automatic, original project | 77 | 328 | 7 | 2 (`3V3`, `GND`) | 0 |
| Global, ports allowed to name nets | 68 | 329 | 6 | 1 (`3V3`) | 0 |
| Global, ports not allowed to name nets | 68 | 329 | 6 | 1 (`3V3`) | 0 |
| Global, ports not allowed to name nets, exact `3V3` net label placed on the MCU U1-23 child-port wire | 67 | 329 | 6 | 0 | 0 |

The six missing connected endpoints in the final diagnostic are `C115-1:/NRST`, `R10-1:/BOOT0`, `R605-1:/ETH_NRST`, `R6F-1:/SYS_EFUSE_FLT`, `R7F-1:/RADAR_EFUSE_FLT`, and `Y2-3:/ETH_50M`. Altium's compiler also reports these as one-pin nets. The exact `3V3` label was placed through Altium's schematic UI at U1-23's native wire/pin coordinate, then the child SchDoc was saved in the ignored diagnostic checkout. The pre-existing qualified CI581 snapshot in the parent directory was not modified.

The corresponding generated KiCad source change adds a local net label at each of the seven affected child hierarchy anchors. A local build of that change passed KiCad ERC with zero violations, matched all 483 original physical endpoint-to-net assignments, and passed hierarchy validation 66/66. It remains an **unqualified candidate** until a new CI artifact passes package/source binding and a fresh Altium import and native audit confirm it. This probe does not authorize routing or production.
