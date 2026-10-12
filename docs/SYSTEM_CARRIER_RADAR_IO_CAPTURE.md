# System Carrier RADAR_IO_CAN capture

Rev.A `RADAR_IO_CAN` schematic capture now includes the carrier-side
external radar interface scaffold:

- TCAN3404DRBRQ1 transceiver placeholder;
- ESD2CANFD24-Q1 protection placeholder;
- 6-pin radar I/O harness connector;
- 2-pin protected radar-power connector;
- selectable 120 ohm CAN termination;
- local CAN-transceiver decoupling;
- named CAN TX/RX, CANH/CANL, RADAR_REF and RADAR_12V nets.

The transceiver and ESD symbols remain `SYMBOL_PENDING` until validated
KiCad symbols are introduced. The sheet therefore advances capture but does
not close Carrier Review A.

No 76-81 GHz RF nets or antenna routing are present on the System Carrier.
