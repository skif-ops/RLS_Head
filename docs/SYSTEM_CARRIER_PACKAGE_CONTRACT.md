# System Carrier package contract

`PACKAGE_CONTRACT_SYS_001.csv` separates package certainty from footprint
certainty before PCB layout.

Rules:

- orderable MPNs must match `BOM_SYS_CARRIER_003.csv`;
- manufacturer package and pin count are locked first;
- a KiCad footprint is used only after it is verified against the vendor
  land-pattern/package drawing;
- unusual modules/packages remain `CUSTOM_REQUIRED` rather than receiving a
  visually similar footprint.

The CAN ESD device is locked to the orderable
`ESD2CANFD24DBZRQ1` SOT-23-3 variant.

This contract is a pre-layout manufacturing gate; it does not change radar
RF performance or sensing algorithms.
