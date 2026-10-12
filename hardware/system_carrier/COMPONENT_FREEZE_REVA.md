# System Carrier Rev.A component freeze

Scope: non-RF measurement carrier only. The 76-81 GHz RF path remains on the external TI AWR2944/AWR2944P EVM for EVT.

## Selected core components

| Function | Selected device | Rev.A decision |
|---|---|---|
| System MCU | STM32H753IIT6 | FREEZE |
| Radar front-end | TI AWR2944/AWR2944P EVM | FREEZE_FOR_EVT |
| IMU | ICM-42688-P | FREEZE |
| GNSS | NEO-M9N-00B | FREEZE |
| Ethernet PHY | LAN8742Ai-CZ-TR | FREEZE |
| CAN-FD PHY | TCAN3404DRBRQ1 | FREEZE |
| 3V3 regulator | TPS62132RGTR | FREEZE |
| System input eFuse | TPS259470ARPWR | FREEZE |
| Radar branch eFuse | TPS259470ARPWR | FREEZE |
| MCU oscillator | ECS-2520S33-250-FN-TR | FREEZE |
| RMII oscillator | ECS-2520S33-500-FN-TR | FREEZE |

## Architecture boundary

The carrier performs only:

- protected power distribution;
- GNSS PPS capture;
- IMU DRDY capture and SPI acquisition;
- radar frame/reference timestamp capture;
- CAN-FD control/measurement metadata exchange with the radar EVM;
- host/instrumentation Ethernet;
- logging, health monitoring and evidence export.

The carrier does not implement:

- mmWave RF generation/reception;
- production antenna geometry;
- vehicle guidance/control;
- intercept-point computation;
- actuator commands.

## EVT radar interface

Primary carrier/radar integration:

- protected 12 V branch from System Carrier to AWR2944-class EVM;
- CAN-FD for configuration/status/measurement metadata;
- one hardware RADAR_REF pulse per measurement frame into STM32 TIM2 capture domain;
- raw ADC capture remains external laboratory instrumentation, not routed through the STM32 carrier.

## Freeze conditions

Rev.A component freeze remains valid provided all of the following hold:

1. carrier 3V3 peak current remains below 2.4 A continuous with at least 20% EVT margin;
2. radar branch remains within the protected 12 V / 3.18 A budget;
3. CAN-FD is sufficient for command/status/metadata traffic;
4. raw ADC recording is performed by vendor instrumentation;
5. the exact AWR2944 EVM RADAR_REF GPIO/header assignment is bench-verified before harness freeze.

If any condition fails, open an ECO rather than silently replacing the selected device.

## RF fallback trigger

A custom RF track is considered only if measured EVT evidence shows that the external radar front-end cannot meet the sensing requirements after allowed software/profile/antenna-module configuration changes. A fallback decision must be based on measured range/angle/latency/thermal evidence, not projection alone.
