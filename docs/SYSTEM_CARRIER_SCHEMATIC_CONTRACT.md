# System Carrier schematic-capture contract

This package freezes the electrical rules required before creating the
authoritative KiCad schematic for the non-RF EVT System Carrier.

## Hierarchy

Required sheets:

1. TOP
2. POWER_INPUT
3. MCU_CORE
4. TIME_GNSS
5. IMU
6. RADAR_IO_CAN
7. ETHERNET
8. DEBUG_BOOT

The mmWave radar front-end remains external. No 76-81 GHz transmission line
is present on the System Carrier.

## 3V3 regulator choice

U5 is changed from adjustable TPS62130A to fixed 3.3 V TPS62132RGTR.
This removes the feedback divider from the first hardware revision while
keeping the same TPS6213x 3-A family and 3x3-mm QFN power-stage approach.

The locked external network is:

- L = 2.2 uH
- CIN = 10 uF plus 100 nF local bypass
- COUT = 22 uF effective minimum target
- AVIN bypass = 100 nF
- SS/TR = 3.3 nF
- PG pull-up = 100 kOhm

## eFuse programming

TPS25947 current-program relation used by the contract:

R_ILIM = 3334 / I_LIM

Locked EVT values:

- U6 system branch: 665 ohm -> about 5.0 A
- U7 radar branch: 1.05 kohm -> about 3.18 A

U7 threshold divider:

- R1 = 470 kohm
- R2 = 16.9 kohm
- R3 = 43.7 kohm

This produces approximately 10.51 V UVLO and 14.57 V OVLO using the
datasheet equations.

U6 uses a wider system window with 470 kohm / 36.0 kohm / 41.2 kohm,
approximately 8.51 V UVLO and 15.94 V OVLO.

Both use 3.3 nF dVdt capacitors as the initial EVT slew-rate choice.

## MCU core

The schematic must provide:

- one 100 nF local capacitor per VDD pin;
- two independent 2.2 uF low-ESR VCAP capacitors;
- 4.7 uF VDD bulk;
- VDDA after FB1 with 100 nF plus 1 uF;
- BOOT0 default 10 kOhm pull-down;
- NRST 100 nF to ground plus externally accessible reset/test point;
- SWDIO/SWCLK/SWO and target VREF at the programming footprint.

## GNSS

NEO-M9N-00B remains on the carrier.

The antenna path is:

U.FL -> ultra-low-capacitance ESD -> 50-ohm RF_IN.

The PCB must provide an optional active-antenna bias-T footprint using
VCC_RF, with 27 nH / 100 nF / 10 ohm reference values.

V_BCKP is populated to 3V3 through a 0-ohm option for EVT; the layout must
leave a test pad / alternate backed-rail option for a later revision.

## Ethernet

LAN8742A uses the internal 1.2-V regulator configuration:

- RBIAS = 12.1 kOhm, 1%;
- VDDCR local capacitor = 1 uF;
- reference analog filtering including 470 pF;
- 49.9-ohm MDI termination resistors;
- hardware nRST available and asserted after power-up;
- external 50-MHz RMII clock is retained.

## CAN / radar harness

CAN-FD uses TCAN3404 and the existing ESD protection.

A 120-ohm termination footprint is fitted through an option/jumper so the
carrier can be configured as a bus endpoint or non-endpoint.

RADAR_REF remains a separate P0 hardware timestamp line and must not be
reconstructed from CAN traffic.

## Next gate

Passing the schematic-contract validator does not close CARRIER_REVIEW_A.
The next step is authoritative KiCad capture followed by real ERC and Review A.
