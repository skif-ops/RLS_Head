# STM32H753II LQFP176 pinmap correction

The authoritative System Carrier MCU is STM32H753IIT6 in LQFP176.

A review against STMicroelectronics DS12117 Rev 10, Figure 8 (LQFP176
package top view), found that several upper-edge physical pin numbers in
PINMAP_SYS_001.csv were shifted relative to the actual STM32H753xI package.

Corrected physical pins:

- PD0 = 142
- PD1 = 143
- PD5 = 147
- PD6 = 150
- PG11 = 154
- PG13 = 156
- PG14 = 157
- PA14 = 137

The functional alternate-function choices do not change; only the package
physical-pin numbers are corrected.

The CAD generator now also validates every authoritative pinmap row against
the actual U1 KiCad symbol pin number/name before applying net labels. A
future package/symbol mismatch therefore fails generation instead of silently
connecting a net to the wrong MCU pad.
