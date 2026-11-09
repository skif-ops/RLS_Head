# System Carrier Review A

This gate covers the current non-RF System Carrier electrical design. It does not authorize production or a 76-81 GHz RF implementation.

The retained KiCad project is the import and independent comparison baseline. The Altium project becomes the PCB implementation authority only after the current UART and external-GNSS ECO is imported, compiled, audited and passes `ALTIUM_EQUIVALENCE_GATE`.

Review A requires zero ERC errors and zero ERC warnings plus explicit PASS results for:

- power, including U5 3V3 and U9 5V_GNSS;
- clock, reset and boot;
- GNSS PPS, RADAR_REF and IMU_DRDY timing capture;
- IMU;
- dual 3.3 V host UART;
- external GNSS UART, PPS and connector power;
- CAN-FD;
- no Ethernet, onboard GNSS RF or 76-81 GHz carrier implementation.

Critical capture pins are GNSS_PPS on PA0 / TIM2_CH1, RADAR_REF on PB10 / TIM2_CH3 and IMU_DRDY on PB11 / TIM2_CH4.

Required BOM anchors are STM32H753IIT6, ICM-42688-P, TCAN3404DRBRQ1, TPS62132RGTR, TPS62133RGTR, TPS259470ARPWR, TPD4E05U06DQAR, Molex 43045-0600 and JST SM06B-GHS-TB(LF)(SN).

All current schematic review and production PDFs must be compiled from the native Altium project. KiCad exports are not release documents.

Production authority remains `NOT_AUTHORIZED`.
