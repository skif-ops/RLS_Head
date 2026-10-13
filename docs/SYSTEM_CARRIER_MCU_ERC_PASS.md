# System Carrier MCU_CORE ERC connectivity pass

This pass changes the generated Rev.A schematic from a placement-only MCU
sheet into an electrically connected capture sheet.

It binds all assigned STM32H753 pins to the authoritative net names in
`PINMAP_SYS_001.csv`, connects the VCAP capacitors, BOOT0 strap, VDDA
ferrite/decoupling network and SWD connector, and adds explicit 3V3/GND
power flags for ERC.

Unused GPIO continue to receive explicit no-connect markers. GPIO aliases
with the `_C` suffix are normalized when deciding whether they are unused.

The CAD CI now also emits `erc_triage.json` so every subsequent remediation
pass can be measured against the real KiCad ERC output.

This pass is limited to the non-RF System Carrier measurement electronics.
