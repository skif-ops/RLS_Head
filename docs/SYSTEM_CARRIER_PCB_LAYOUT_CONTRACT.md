# System Carrier PCB Layout Contract Rev.A

This contract is the pre-routing constraint set for the **non-RF** EVT
System Carrier.

## Baseline stackup

Use a four-layer EVT board unless fabrication constraints require a reviewed
ECO:

- L1: components + critical/high-speed signals;
- L2: continuous solid ground plane;
- L3: power distribution + slow signals;
- L4: secondary signals.

The ground plane must remain continuous below UART, timing capture lines,
CAN and the external GNSS connector interface.

## Critical routing domains

### Power

- TPS62132 input/SW/output current loops must be physically compact.
- TPS62133 input/SW/output current loops must be physically compact.
- U6/U7 eFuse programming components stay adjacent to their devices.
- RADAR_12V is sized for the 3 A EVT allocation and kept short.
- STM32 VCAP and VDD decoupling take placement priority over routing
  convenience.

### Host UART

- Route both UART pairs over continuous ground.
- Place D3 directly behind J6 and keep the connector-side stubs short.
- Keep the four 33-ohm series resistors close to the MCU-side source path.

### GNSS

- Place JST-GH J8 at an accessible board edge.
- Place D8 directly behind J8 with a short ground return.
- Route 5V_GNSS, UART and PPS only; there is no carrier GNSS RF trace.
- Keep PPS and UART away from BUCK_SW and BUCK5_SW.

### Timing

GNSS_PPS, RADAR_REF and IMU_DRDY remain deterministic timestamp lines.
Keep them away from both buck switch nodes and high-current paths.

### IMU

The ICM-42688-P should be located on a mechanically stiff region, separated
from the inductor, large connectors and likely enclosure flex points.

## Explicit scope boundary

The System Carrier contains **no 76–81 GHz RF routing or antenna structure**.
The mmWave front-end remains the external AWR2944-class EVM for EVT.

## Gate

Before routing starts, placement review must confirm every P0 rule can be
satisfied. Any rule that cannot be met requires an explicit ECO; it must not
be silently relaxed during routing.
