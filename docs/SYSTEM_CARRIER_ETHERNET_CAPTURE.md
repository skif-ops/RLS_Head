# System Carrier Ethernet capture

Rev.A `ETHERNET` capture now contains the instrumentation Ethernet scaffold:

- LAN8742Ai-CZ-TR PHY placeholder;
- ECS 50 MHz oscillator placeholder;
- P01-0006-01 MagJack placeholder;
- TPD4E05U06 ESD placeholder;
- 12.1 kΩ RBIAS;
- four 49.9 Ω MDI termination resistors;
- 1 µF VDDCR capacitor;
- 470 pF analog filter capacitor;
- local 100 nF bypass;
- RMII/MDIO/MDC and MDI net labels.

This link is for host instrumentation, logging and evidence export. It is not
a vehicle-control or actuation interface.

Validated KiCad symbols/footprints for the PHY, oscillator, ESD and MagJack
remain required before Carrier Review A closes.
