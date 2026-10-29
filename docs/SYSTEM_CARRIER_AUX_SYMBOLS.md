# System Carrier auxiliary symbol contract

The remaining protection/clock symbols are captured by
`AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv`.

Covered references:

- D4 — ESD2CANFD24DBZRQ1: two bidirectional CAN I/O pins plus GND;
- D3 — TPD4E05U06DQAR: four protected host UART signals;
- D8 — TPD4E05U06DQAR: external GNSS UART and PPS protection.

These three devices are generated into the same
`SystemCarrier_Local.kicad_sym` library as the core U2/U4/U5/U6/U7/U9
symbols.

The generated schematic contains no placeholders.

The auxiliary contract does not change circuit topology. It replaces generic
capture placeholders with pin-numbered symbols derived from manufacturer pin
tables.
