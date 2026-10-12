# LAN8742A controlled reset closure

Rev.A uses a dedicated STM32H753 GPIO for the LAN8742A hardware reset:

- ETH_NRST -> PE4 / LQFP176 pin 3;
- push-pull firmware output;
- external 10 kΩ pull-down at the PHY reset pin;
- startup default remains asserted low;
- firmware may drive high only after at least 25 ms of stable carrier power.

This avoids relying on an RC reset network and preserves deterministic
configuration-strap sampling before the RMII PHY becomes active.

The default LAN8742A internal straps remain:

- MODE[2:0] = 111: all-capable, auto-negotiation enabled;
- PHYAD0 = 0;
- REGOFF = 0: internal 1.2 V regulator enabled;
- nINTSEL = 1: external 50 MHz REF_CLK input mode.

The RMII receive/strap pins are MCU inputs during reset and must remain
high-impedance until the PHY reset sequence completes.
