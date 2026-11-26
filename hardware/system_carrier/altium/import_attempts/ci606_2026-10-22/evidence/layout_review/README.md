# POWER_INPUT layout correction, 2026-10-22

The imported CI606 `10_POWER_INPUT.SchDoc` remains a diagnostic snapshot. In
Altium Designer 26.10.1 Trial, its components and labels occupied a small
part of the A4 page, and several names overlapped. Altium's automatic cross
references appended long sheet lists to ports. The project option was turned
off in the active Altium project; the two relevant settings were mirrored in
`native_snapshot/EVT_SYS_CARRIER.PrjPcb`. This display change does not alter
connections. The saved SchDoc hashes remain the same as the CI606 receipt.

The source generator now spreads the power circuit across the A4 page,
enlarges the U5/U6/U7 symbol bodies for their internal pin names, moves long
net labels outside those bodies, and separates the U6/U7 output ports from
their local labels. The source preview is
[power_input_source_eco.png](power_input_source_eco.png). It is a KiCad 10
render of the new source, not a native Altium export.

Local checks on the regenerated hierarchy:

- KiCad ERC: 0 errors, 0 warnings.
- Physical endpoint baseline: 483 rows, byte identical to the CI606 baseline
  (`7882e48a47a904e4fa075aa09a44e9628915f9291d5411d5f98896391e435ca8`).
- Hierarchy interface: 66/66 PASS.
- CAD scaffold validation: PASS.

Changing the source generator and local symbols makes the CI606 import
artifact stale. The revised source requires a newly qualified import package,
fresh Altium import, native compile/audit and equivalence before promotion.
The CI606 native SchDoc still shows the earlier placement. `READY_FOR_ROUTING`
remains false; routing and production authority remain `NOT_AUTHORIZED`.
