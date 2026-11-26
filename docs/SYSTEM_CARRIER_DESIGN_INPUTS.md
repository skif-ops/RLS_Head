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

RADAR_REF and IMU_DRDY are P0. Optional untrusted GNSS_PPS is P1. All three
share the TIM2 hardware time domain.

## Host UART mapping

The two independent 3.3 V interfaces are:

- HOST_UART1_TX: PD5 / USART2_TX
- HOST_UART1_RX: PD6 / USART2_RX
- HOST_UART2_TX: PA9 / USART1_TX
- HOST_UART2_RX: PA10 / USART1_RX

GNSS uses USART3 on PD8/PD9 and remains independent of both host UARTs.
