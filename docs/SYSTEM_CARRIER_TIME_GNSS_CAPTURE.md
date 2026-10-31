# System Carrier TIME_GNSS capture

Rev.A `TIME_GNSS` contains the detachable external receiver interface:

- JST-GH J8 with 5V_GNSS, UART, PPS and GND;
- TPD4E05U06 protection for UART and PPS;
- P1 optional GNSS PPS for TIM2 capture;
- no carrier-side GNSS RF path or antenna connector.

The selected external receiver is simpleRTK3B Pro based on mosaic-X5. It can
be removed or quarantined without stopping carrier operation.

This sheet is timing/navigation instrumentation only and contains no radar
RF or control-actuation circuitry.

J8 uses a detachable cable, so receiver installation and replacement require
no soldering on the System Carrier.
