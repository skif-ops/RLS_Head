# EVT System Carrier

This directory contains the authoritative non-RF System Carrier
electrical design inputs.

Present:

- `BOM_SYS_CARRIER_003.csv`
- `PINMAP_SYS_001.csv`
- `CLOCK_TREE_SYS_001.csv`
- `POWER_TREE_SYS_001.csv`
- `NETLIST_SYS_001.csv`
- `RADAR_INTERFACE_SYS_001.csv`
- `SCHEMATIC_BLOCKS_SYS_001.csv`
- `SCHEMATIC_COMPONENTS_SYS_001.csv`
- `CONNECTOR_PINOUT_SYS_001.csv`
- `POWER_BUDGET_SYS_001.csv`

## EVT radar architecture

The selected EVT radar front-end is an external TI AWR2944PEVM.
The System Carrier does not implement the 76-81 GHz RF path.

Carrier responsibilities are limited to:

- protected 12 V radar power branch;
- CAN-FD control/measurement-metadata transport;
- hardware `RADAR_REF` timestamp capture;
- GNSS PPS and IMU timestamp capture in the shared TIM2 domain;
- host/instrumentation Ethernet;
- logging, health monitoring and evidence export.

Raw ADC capture remains a laboratory/instrumentation path through the
radar vendor tooling/DCA1000 class interface and is not routed through
the STM32 carrier.

The selected GNSS module is u-blox NEO-M9N-00B.

## Power baseline

- external system input: 12 V nominal, source capability >= 5 A;
- U6 TPS259470A: system-level input protection, target current limit 5 A;
- U5 TPS62132: fixed 3.3 V / 3 A carrier rail;
- U7 TPS259470A: dedicated radar branch, target current limit 3.2 A;
- J_RADAR_PWR: protected 12 V output toward the radar EVM harness.

The schematic-capture contract locks the first-pass TPS25947 programming values,
TPS62132 network, MCU decoupling, Ethernet bias/termination, GNSS RF protection,
connector pinout and rail allocations. These values remain subject to ERC and
bench verification before Review A.

Still open:

- `EVT_SYS_CARRIER.kicad_pro`
- `EVT_SYS_CARRIER.kicad_sch`
- exact AWR2944PEVM `RADAR_REF` GPIO/header assignment after bench verification
- GNSS antenna connector and RF matching implementation
- `review_a/erc.json`
- `review_a/manifest.json`

Run:

`python -m tools.carrier_design_inputs hardware/system_carrier --output carrier_design_inputs.json`

and:

`python -m tools.carrier_schematic_contract hardware/system_carrier --output carrier_schematic_contract.json`

before schematic capture.

The first real schematic gate remains `CARRIER_REVIEW_A`.
Synthetic files under `tests/fixtures/carrier_review_a/` must never
be used to close that gate.
