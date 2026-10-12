# EVT radar/front-end and System Carrier architecture

## Decision

Primary EVT radar front-end: **Texas Instruments AWR2944PEVM**.

The board-level System Carrier remains non-RF and is based on
**STM32H753IIT6**. A custom 76-81 GHz RF path is not part of EVT-A.

The reason for this split is to isolate the main unknowns:

1. prove the real range/measurement envelope first;
2. validate time alignment and system error on real hardware;
3. validate carrier power, communications, logging and EMC;
4. move to a custom RF/antenna module only if measured evidence shows that
   the vendor front-end/antenna is the limiting factor.

## Selected radar-front-end path

AWR2944PEVM is used as a removable external assembly.

EVT carrier/radar interfaces:

- 12 V protected radar supply;
- CAN-FD for configuration, health and measurement metadata;
- one hardware `RADAR_REF` pulse captured by STM32 TIM2;
- optional radar Ethernet directly to instrumentation/host;
- raw ADC laboratory capture via vendor capture hardware, not through STM32.

The carrier does not carry mmWave traces.

## Carrier component baseline

- MCU: STM32H753IIT6
- IMU: ICM-42688-P
- GNSS: u-blox NEO-M9N-00B
- Ethernet PHY: LAN8742Ai-CZ-TR
- CAN-FD PHY: TCAN3404DRBRQ1
- 3V3 regulator: TPS62130ARGTR
- system/radar eFuse: TPS259470ARPWR
- radar power connector: Molex 43650-0200
- radar I/O connector: Molex 43045-0600

## Time architecture

The carrier keeps one hardware time domain:

- GNSS_PPS -> PA0 / TIM2_CH1
- RADAR_REF -> PB10 / TIM2_CH3
- IMU_DRDY -> PB11 / TIM2_CH4

No software timestamp substitutes for these P0 capture signals.

## Data split

CAN-FD carries only bounded control/status/measurement metadata.
Ethernet is the carrier host/instrumentation link.

Large raw radar captures stay outside the carrier and are collected by the
radar vendor capture path during qualification.

## Fallback trigger for a custom RF path

A custom RF/antenna module is considered only after real EVT evidence shows
one of the following while the rest of the chain is healthy:

- required range cannot be reached with acceptable detection/track evidence;
- antenna field-of-view or ambiguity measurements fail the physical antenna gate;
- vendor front-end interface/latency prevents the required measurement cadence;
- packaging/thermal constraints cannot be solved with the EVM/module form factor.

Any fallback begins as a stand-alone measurement RF module and must repeat
the EM provenance, reference-range, M300, physical-antenna and SYS-ERR gates
before integration.

## Explicit non-goals

This architecture document does not define vehicle actuation, intercept
logic, guidance commands or a weapon-control interface.
