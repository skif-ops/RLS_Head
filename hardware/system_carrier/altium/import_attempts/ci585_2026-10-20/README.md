# Issue #216: CI585 native Altium import diagnostic

The `system-carrier-altium-import` artifact from CI run 39481063118 (artifact
12292565291, digest `sha256:8592c5fe1c1c3cbeb6a34b05f467152450c74becab3d799853125862f46a870c`)
passed package verification (112/112 files) and current-source binding (52/52)
before import. Altium Designer 26.10.1 Trial with KiCad Importer imported the
root and seven child schematics. The previously imported native PcbLib was
attached because all 29 source `.kicad_mod` files were byte-identical to the
prior qualified artifact. Altium created the PcbDoc and executed the schematic
to PCB ECO. `native_snapshot/` contains the genuine saved Altium files.

With `Net Identifier Scope = Global` and `Allow Ports to Name Nets` disabled,
the project Protel netlist has 67 groups and all 335 connected physical pins.
The diagnostic comparison found no missing connected pins, extra pins,
cross-source-net mergers or source-net splits. The other 148 KiCad pins are
intentionally unconnected and omitted from Protel output. This is a **schematic
netlist** result, not PCB or equivalence authority.

The ECO added 92 components, 67 nets, seven component classes and 337 pin-net
operations. Its log assigns 333 distinct connected pins; the two missing
source endpoints are `U4-EP` and `U5-EP`, both on GND. The package footprints
number those exposed pads `9` and `17`, respectively. The committed source
contract and generator were corrected after this attempt. The corrected source
is undergoing fresh qualification; the CI585 package is now stale against the
checkout. Native compilation under the same Global scope reported **6 errors
and 157 warnings**; the raw Altium Messages export is retained. Five errors
are floating input pins on intentionally unconnected D3/J6 pins; one is a
power-pin/output-port conflict on `RADAR_12V`. Most warnings are importer
geometry and pin/port classification issues, including objects outside A4
sheets. The generated source now uses A2 paper for all sheets, to be assessed
in the next qualified import.

`native_file_preflight.json` passes the CFB/OLE container checks on the exact
saved SchDoc/PcbDoc hashes. The Import Wizard did not leave an exportable raw
wizard log for this run, so this is an **attempt record**, not the canonical
`import_receipt.json`. The mechanical datum, routing stack, power rules,
read-only native audit, BOM, PCB pad-net inventory, hierarchy, no-mmWave review
and `ALTIUM_EQUIVALENCE_GATE` remain incomplete. The canonical native pair is
not committed, `READY_FOR_ROUTING` is not claimed, and production authority
remains `NOT_AUTHORIZED`.
