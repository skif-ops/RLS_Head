# System Carrier symbol pin contract

`SYMBOL_PIN_CONTRACT_SYS_001.csv` is the pin-level source of truth for
non-standard active components that still require verified KiCad symbols.

Covered parts:

- U2 ICM-42688-P;
- U3 LAN8742Ai-CZ-TR;
- U4 TCAN3404DRBRQ1;
- U5 TPS62132RGTR;
- U6/U7 TPS259470ARPWR;
- U8 NEO-M9N-00B.

Every physical pin is represented, including exposed pads where applicable.
The contract records the intended net/strap/NC policy rather than relying on
a generic connector placeholder.

Key locked behaviors include:

- ICM-42688-P SPI and dedicated VDDIO bypass;
- LAN8742A external 50 MHz REF_CLK mode, MODE=111, PHY address 0 and controlled
  ETH_NRST;
- TCAN3404 deterministic normal mode;
- TPS62132 fixed 3.3 V straps;
- TPS259470 FLT monitoring and unused AUXOFF/ITIMER policy;
- NEO-M9N UART + TIMEPULSE configuration and optional active-antenna bias.

This contract is the input to the project-local KiCad symbol library. A
symbol must not replace a `SYMBOL_PENDING` placeholder until its pins match
this file.
