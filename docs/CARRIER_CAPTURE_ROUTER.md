# Carrier capture router

`capture_router` is the small deterministic handoff layer between STM32H753
TIM2 capture ISRs and the higher-level carrier services.

It accepts only three event sources:

- GNSS PPS;
- radar frame/reference pulse;
- IMU data-ready.

Properties:

- fixed 32-entry ring buffer;
- no dynamic allocation;
- per-source sequence counters;
- explicit overflow/drop counter;
- FIFO ordering across all capture sources;
- no blocking I/O and no timestamp reinterpretation.

The capture router stores the hardware-domain timestamp exactly as observed.
Time discipline is applied later by `time_service`; freshness/fault policy
is applied by `carrier_health`.

This module carries no target-state, guidance or actuation semantics.
