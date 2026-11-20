# POWER_INPUT source layout review, 2026-10-22

The KiCad 10 [source render](power_input_source.png) shows the `10_POWER_INPUT`
page after a second readability pass. The A4 drawing is spread across the
page. Long IC values and net names remain inside the frame. Vertical passive
parts now have short wire stubs so their net labels clear component values.
The J1 input and GND labels are separated from its pin numbers, and U6/U7
DVDT labels are outside the symbol bodies.

The generated source passed KiCad ERC with zero violations and the CAD
scaffold validator. Its physical endpoint CSV is byte identical to the
previous 483-row baseline, SHA-256
`7882e48a47a904e4fa075aa09a44e9628915f9291d5411d5f98896391e435ca8`.
The checks are retained beside the render.

This is a source render, not an Altium SchDoc export. The saved CI614 native
import predates this pass and remains diagnostic. A new qualified package,
native import, compile, BOM, audit, and equivalence are required for the
revised source. `READY_FOR_ROUTING=false`; routing and production authority
remain `NOT_AUTHORIZED`.
