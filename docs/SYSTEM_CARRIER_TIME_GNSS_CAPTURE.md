# System Carrier TIME_GNSS capture

Rev.A `TIME_GNSS` capture now contains the carrier-side GNSS timing and
antenna-entry scaffold:

- NEO-M9N-00B symbol placeholder;
- ESD0P2RF-02LS RF protection placeholder;
- GNSS antenna connector;
- local 100 nF + 10 uF supply decoupling;
- GNSS UART nets;
- P0 GNSS PPS net for TIM2 capture;
- optional active-antenna bias-T population (27 nH / 10 ohm / 100 nF).

The GNSS module and RF ESD symbols remain `SYMBOL_PENDING` until validated
KiCad symbols are introduced. The optional bias network is DNP by default.

This sheet is timing/navigation instrumentation only and contains no radar
RF or control-actuation circuitry.

USB is unused on Rev.A; V_USB is pulled to GND through 100 kΩ per the u-blox integration guidance.
