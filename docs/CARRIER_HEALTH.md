# System Carrier health layer

`carrier_health` is a deterministic firmware-side health contract for the
non-RF System Carrier.

Inputs:

- hardware-captured `RADAR_REF` timestamps;
- hardware-captured GNSS PPS timestamps;
- hardware-captured IMU DRDY timestamps;
- board/eFuse power-fault flags.

Outputs:

- stale-source flags;
- power-fault summary;
- current source ages;
- aggregate healthy/not-healthy state.

The module has no target state, no guidance output and no vehicle-control
interface. It is intended for watchdog policy, telemetry and evidence logs.

Hardware-specific ISR/HAL glue remains a separate next step; the pure logic
is host-tested and retained in the STM32H753 cross-build.
