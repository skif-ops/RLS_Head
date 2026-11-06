# System Carrier symbol pin contract

`SYMBOL_PIN_CONTRACT_SYS_001.csv` is the pin-level source of truth for non-standard active components used by the current carrier.

Covered parts are U2 ICM-42688-P, U4 TCAN3404DRBRQ1, U5 TPS62132RGTR, U6 and U7 TPS259470ARPWR, and U9 TPS62133RGTR. `AUX_SYMBOL_PIN_CONTRACT_SYS_001.csv` covers Y1 and D3, D4 and D8.

Every physical pin is represented, including exposed pads. The contract records the intended net, strap and no-connect policy.

Locked behaviors include ICM-42688-P SPI and dedicated VDDIO bypass, deterministic TCAN3404 normal mode, fixed 3V3 and 5V buck straps, TPS259470 FLT monitoring, and the connector-side ESD paths for host UART, CAN and external GNSS.

LAN8742A and NEO-M9N are not part of the current contract.
