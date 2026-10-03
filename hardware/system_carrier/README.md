# EVT System Carrier

This directory contains the authoritative non-RF System Carrier
electrical design inputs.

Present:

- `BOM_SYS_CARRIER_002.csv`
- `PINMAP_SYS_001.csv`
- `CLOCK_TREE_SYS_001.csv`
- `POWER_TREE_SYS_001.csv`
- `NETLIST_SYS_001.csv`

Still open:

- `EVT_SYS_CARRIER.kicad_pro`
- `EVT_SYS_CARRIER.kicad_sch`
- `review_a/erc.json`
- `review_a/manifest.json`

Run `python -m tools.carrier_design_inputs hardware/system_carrier
--output carrier_design_inputs.json` before schematic capture.

The first real schematic gate remains `CARRIER_REVIEW_A`.
Synthetic files under `tests/fixtures/carrier_review_a/` must never
be used to close that gate.
