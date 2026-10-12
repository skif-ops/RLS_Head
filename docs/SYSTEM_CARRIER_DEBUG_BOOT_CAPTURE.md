# System Carrier DEBUG_BOOT capture

Rev.A `DEBUG_BOOT` now explicitly captures the service/debug portion of the
carrier:

- NRST pushbutton;
- DNP boot/service override resistor;
- SWDIO, SWCLK and SWO nets;
- NRST and BOOT0 nets;
- explicit 3V3/GND references.

The primary Tag-Connect SWD connector remains on the MCU_CORE sheet in the
current hierarchy. This sheet adds only service/reset access and contains no
vehicle actuation/control interface.
