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

The ground plane must remain continuous below RMII, Ethernet MDI, timing
capture lines, CAN and GNSS RF.

## Critical routing domains

### Power

- TPS62132 input/SW/output current loops must be physically compact.
- U6/U7 eFuse programming components stay adjacent to their devices.
- RADAR_12V is sized for the 3 A EVT allocation and kept short.
- STM32 VCAP and VDD decoupling take placement priority over routing
  convenience.

### Ethernet

- PHY-to-MagJack MDI is a 100-ohm differential domain.
- ESD sits on the connector side of the MDI path.
- RMII stays over solid ground; avoid unnecessary layer changes.

### GNSS

- U.FL-to-ESD-to-NEO-M9N is a 50-ohm controlled-impedance path.
- GNSS ESD ground return must be extremely short.
- Keep buck SW, 25/50 MHz clocks, RMII and CAN away from the RF entry.

### Timing

GNSS_PPS, RADAR_REF and IMU_DRDY remain deterministic timestamp lines.
Keep them away from the buck switch node and Ethernet MDI pair.

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
