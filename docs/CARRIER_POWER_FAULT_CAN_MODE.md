# System Carrier power-fault and CAN-mode closure

Rev.A now closes two hardware/firmware consistency gaps.

## eFuse fault monitoring

TPS259470 FLT outputs are active-low open-drain. Both protected branches are
therefore routed to the STM32 health domain:

- SYS_EFUSE_FLT -> PE2 / LQFP176 pin 1;
- RADAR_EFUSE_FLT -> PE3 / LQFP176 pin 2.

Each FLT line has an external 10 kΩ pull-up to 3V3. The firmware I/O
contract assigns both inputs to health_service as P0 fault inputs.

## TCAN3404 mode defaults

TCAN3404 STB has an internal pull-up, so leaving it floating selects standby.
Rev.A adds an external 10 kΩ pull-down so CAN starts in normal mode. SHDN
also receives an external 10 kΩ pull-down to reinforce its internal
normal-mode bias.

These are carrier health/link controls only; no vehicle-control interface is
introduced.
