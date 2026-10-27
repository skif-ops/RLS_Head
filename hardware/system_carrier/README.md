# EVT System Carrier

This directory contains the authoritative non-RF System Carrier
electrical design inputs.

Project-level documents:

- `../../docs/EVT_SYSTEM_CARRIER_PROJECT_DESCRIPTION.md`
- `../../docs/EVT_SYSTEM_CARRIER_TECHNICAL_SPECIFICATION.md`
- `../../docs/EVT_SYSTEM_CARRIER_ENGINEERING_PACKAGE.md`
- `../../docs/EVT_SYSTEM_CARRIER_REZONIT_REQUEST.md`

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

CAD status:

- the retained KiCad System Carrier capture is ERC-clean at 0 errors / 0 warnings;
- Altium Designer is now the primary PCB CAD target;
- all KiCad sources are retained as the independent electrical verification baseline;
- native Altium files live under `hardware/system_carrier/altium/native/` after the Altium import/equivalence gate.

Current implementation:

- native Altium import and equivalence are complete;
- `ALTIUM_EQUIVALENCE_GATE=PASS`;
- placement and EVT routing are complete;
- target signal connection audit reports no disconnected signal nets;
- routing authority is authorized;
- production authority is not authorized.

Still open:

- exact AWR2944PEVM `RADAR_REF` GPIO/header assignment after bench verification;
- order-specific Rezonit stack and controlled-impedance binding;
- closure of the 75 production DRC markers;
- compact enclosure and STEP verification;
- return-path, SI, DFM and OutJob production evidence.

Run:

`python -m tools.carrier_design_inputs hardware/system_carrier --output carrier_design_inputs.json`

and:

`python -m tools.carrier_schematic_contract hardware/system_carrier --output carrier_schematic_contract.json`

before schematic capture.

The `CARRIER_REVIEW_A` schematic gate is closed by the retained project
evidence. Synthetic files under `tests/fixtures/carrier_review_a/` must never
be used as release evidence.

## CAD authority

See `CAD_AUTHORITY_SYS_001.json` and `docs/CAD_POLICY_ALTIUM.md`. New PCB implementation work is done in Altium Designer; KiCad files are preserved and must not be deleted.
