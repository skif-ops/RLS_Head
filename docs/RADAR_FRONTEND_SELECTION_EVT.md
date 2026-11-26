# EVT radar front-end and System Carrier architecture

The primary EVT radar front-end is the external Texas Instruments AWR2944PEVM. The STM32H753IIT6 System Carrier remains non-RF and contains no 76-81 GHz trace, antenna or RF front-end.

The carrier provides protected 12 V radar power, CAN-FD for bounded control and measurement metadata, and a hardware `RADAR_REF` input captured by STM32 TIM2. Raw radar capture stays on the vendor laboratory capture path and does not pass through the carrier MCU.

Host communication uses two independent 3.3 V UART channels on J6. Ethernet is not part of the carrier design.

GNSS is an external simpleRTK3B Pro / Septentrio mosaic-X5 module connected without solder through JST-GH J8. The carrier provides `5V_GNSS`, UART RX/TX, PPS and GND. GNSS data is optional and untrusted until integrity checks pass. Radar, CAN, UART, IMU and logging remain operational when GNSS is absent or quarantined.

The shared timing domain uses GNSS_PPS on PA0 / TIM2_CH1, RADAR_REF on PB10 / TIM2_CH3 and IMU_DRDY on PB11 / TIM2_CH4.

Altium Designer is the authoritative CAD and production-output system. Production authority remains `NOT_AUTHORIZED`.
