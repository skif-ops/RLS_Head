# System Carrier design inputs

This directory now contains the authoritative electrical inputs for
capturing the non-RF EVT System Carrier schematic.

The files are design inputs, not a Review A PASS.

## Inputs

- `BOM_SYS_CARRIER_002.csv`
- `PINMAP_SYS_001.csv`
- `CLOCK_TREE_SYS_001.csv`
- `POWER_TREE_SYS_001.csv`
- `NETLIST_SYS_001.csv`

Run:

```bash
python -m tools.carrier_design_inputs \
  hardware/system_carrier \
  --output carrier_design_inputs.json
```

A successful result is:

```text
DESIGN_INPUT_READY
```

This means the selected parts, critical pin mappings, timing tree,
power chain and logical nets are internally consistent enough for
schematic capture.

It does not mean:

- a KiCad schematic exists;
- ERC has run;
- Review A is closed;
- fabrication is authorized.

## Critical timing capture

The authoritative capture assignments are:

- GNSS_PPS -> PA0 / TIM2_CH1
- RADAR_REF -> PB10 / TIM2_CH3
- IMU_DRDY -> PB11 / TIM2_CH4

All three are P0 and intentionally share the TIM2 hardware time domain.

## Ethernet RMII mapping

The selected alternate mapping avoids PB10/PB11 because those pins are
reserved for timing capture:

- REF_CLK PA1
- MDIO PA2
- MDC PC1
- CRS_DV PA7
- RXD0 PC4
- RXD1 PC5
- TX_EN PG11
- TXD0 PG13
- TXD1 PG14

The 50 MHz oscillator is a star source to the MCU RMII REF_CLK input
and the PHY reference-clock input.
