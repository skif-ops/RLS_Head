# Carrier Ethernet reset service

`ethernet_reset` implements the deterministic LAN8742A reset timing
contract without depending on a board-specific GPIO HAL.

At boot the required output level is always low. Once the carrier firmware
marks 3V3/power initialization complete, the service keeps `ETH_NRST`
asserted for at least 25 ms and only then requests a push-pull high level.

Properties:

- fixed state only; no heap;
- single-shot power-ready timestamp;
- non-monotonic timestamps never release reset;
- once released, reset remains deasserted until a full carrier restart.

The board-specific STM32 BSP must apply the returned level to PE4.

This module only manages the Ethernet instrumentation PHY reset.
