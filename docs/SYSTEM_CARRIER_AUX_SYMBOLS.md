# System Carrier auxiliary symbol contract

The remaining protection/clock symbols are captured by
`AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv`.

Covered references:

- Y2 — ECS-2520S33-500-FN-TR: pin 1 tri-state, pin 2 GND,
  pin 3 50 MHz output, pin 4 VDD;
- D4 — ESD2CANFD24DBZRQ1: two bidirectional CAN I/O pins plus GND;
- D3 — TPD4E05U06DQAR: two protected Ethernet differential pairs,
  two ground pins and four NC routing pins.

These three devices are generated into the same
`SystemCarrier_Local.kicad_sym` library as the core U2/U4/U5/U6/U7
symbols.

D8 ESD0P2RF-02LS is a two-terminal bidirectional TVS and uses the stock
`Device:D_TVS` symbol.

After this step the only expected schematic placeholder is the Bel
P01-0006-01 integrated MagJack, whose exact transformer/LED pinout remains
a separate contract.

The auxiliary contract does not change circuit topology. It replaces generic
capture placeholders with pin-numbered symbols derived from manufacturer pin
tables.
