# System Carrier IMU capture

Rev.A `IMU` capture now contains the ICM-42688-P carrier-side scaffold:

- ICM-42688-P symbol placeholder;
- SPI2 NSS/SCK/MISO/MOSI nets;
- P0 IMU_DRDY into STM32 TIM2 capture;
- 100 nF + 2.2 uF VDD decoupling;
- dedicated 10 nF VDDIO bypass;
- reserved/FSYNC pin treatment deferred to the explicit pin contract instead
  of using an arbitrary pull resistor.

The final validated ICM-42688-P KiCad symbol/pin mapping is still required
before Carrier Review A can close. This sheet is sensing/timestamp
instrumentation only.
