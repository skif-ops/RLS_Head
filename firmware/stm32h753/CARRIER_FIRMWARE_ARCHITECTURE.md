# STM32H753 Carrier Firmware Architecture — EVT

This firmware is for the non-RF measurement carrier.

## Runtime responsibilities

1. **Time service**
   - TIM2 free-running capture domain.
   - GNSS PPS on TIM2_CH1.
   - RADAR_REF on TIM2_CH3.
   - IMU_DRDY on TIM2_CH4.
   - monotonic timestamp API and holdover state.

2. **IMU acquisition**
   - SPI2 burst acquisition on DRDY.
   - timestamp captured in hardware domain before SPI transaction.
   - fixed-size ring buffer; no dynamic allocation in ISR path.

3. **Radar interface**
   - FDCAN1 for EVM control/status/measurement metadata.
   - RADAR_REF capture is the authoritative local radar frame timestamp.
   - no raw ADC transport through STM32.

4. **GNSS interface**
   - USART3 for the detachable external mosaic-X5 receiver.
   - TIMEPULSE/PPS captured independently of UART parsing.
   - GNSS is optional and is never a boot or measurement dependency.
   - navigation and PPS remain untrusted until integrity checks pass.
   - expose receiver jamming and spoofing indicators.
   - constellation groups and their use in PVT are configurable.

5. **Host telemetry**
   - two independent 3.3 V UART links: USART2 and USART1.
   - binary framed telemetry with sequence number and monotonic timestamp.
   - loss counters and backpressure accounting.
   - no Ethernet hardware or firmware dependency.

6. **Health manager**
   - rail-good, watchdog, link-state, CAN error-state, GNSS validity, PPS age, IMU age, radar-ref age.
   - faults are latched with timestamp and exported.

## Scheduling model

- interrupt handlers: capture timestamp / enqueue minimal event only;
- high-priority task: radar/GNSS/IMU event correlation;
- medium-priority task: CAN RX/TX, IMU SPI completion, UART telemetry packing;
- low-priority task: health report, statistics, non-critical diagnostics.

No blocking I/O inside capture ISRs.

## Static memory policy

- no heap use after startup;
- fixed ring buffers;
- explicit overflow counters;
- buffer ownership encoded by state;
- all telemetry structures versioned.

## Initial firmware modules

- time_service
- capture_router
- imu_service
- gnss_service
- radar_can_service
- radar_ref_service
- health_service
- telemetry_service
- config_lock
- evidence_export

## Bring-up order

1. clock/reset/watchdog;
2. GPIO and rail-good inputs;
3. TIM2 timestamp domain;
4. host UART1 and UART2;
5. optional GNSS UART + PPS;
6. IMU SPI + DRDY;
7. CAN-FD radar link;
8. health manager;
9. integrated evidence logger.

## EVT exit criteria

Firmware is ready for carrier Review A / bench when:

- all three timestamp inputs are observed in one monotonic domain;
- timestamp wrap handling is tested;
- GNSS loss, spoofing quarantine and PPS holdover are reported without stopping radar, CAN, UART or logging;
- IMU overrun and CAN bus-off recovery are tested;
- UART telemetry loss counters are exposed independently for both links;
- watchdog recovery is demonstrated;
- configuration hash is exported with every measurement session.
