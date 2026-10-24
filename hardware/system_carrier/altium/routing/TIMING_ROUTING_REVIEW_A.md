# EVT System Carrier Timing Routing Review A

Date: 2026-10-24

`TIMING_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 routed `GNSS_PPS`, `IMU_DRDY` and `RADAR_REF` on
the canonical native PCB. The resulting canonical PCB SHA-256 is
`3f9df31481f159d3962260687d5f039eac7c95ac19935172ba11f683871f2fa9`.

## Reviewed geometry

All three routes use 0.20 mm Top Layer tracks and no vias. A graph rebuilt
from the native track intersections and pad bounds confirms one connected
component between each required endpoint pair.

| Net | Endpoint pair | Length | Segments | Vias |
| --- | --- | ---: | ---: | ---: |
| `GNSS_PPS` | U8-3 to U1-40 | 41.986161 mm | 7 | 0 |
| `IMU_DRDY` | U2-4 to U1-80 | 44.524254 mm | 6 | 0 |
| `RADAR_REF` | U1-79 to J4-4 | 42.863590 mm | 10 | 0 |

The measured edge clearance from these routes to `BUCK_SW` and the four
Ethernet MDI nets is at least 9.519854 mm. This exceeds the 1.0 mm quiet
clearance required by the timing-route gate.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Timing routing script: `../scripts/EVT_SYS_CARRIER_TimingRouting.pas`
- Runtime audit script: `../scripts/EVT_SYS_CARRIER_RoutingAudit.pas`
- Pad export: `connection_audit/pad_geometry.csv`, 529 rows
- Track export: `connection_audit/track_inventory.csv`, 1156 rows
- Fill export: `connection_audit/fill_inventory.csv`, 67 rows
- Via export: `connection_audit/via_inventory.csv`, 34 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- Board render: `timing_routing_review_a.png`
- SHA-bound result: `timing_routing_drc_summary.json`

## Native DRC

Altium ran DRC on the canonical PCB at 21:26:20. The report has 119 markers,
the same counts as the immediate pre-route connection-integrity baseline:

- Generic copper clearance: 27
- Ethernet class clearance: 27
- 1.0 mm `NC_TIMING` to `BUCK_SW` clearance: 0
- 10 mil clearance: 0
- Hole size: 9
- Hole-to-hole clearance: 1
- Component clearance: 55
- Unrouted net, routing topology, power-plane connect and net antennae: 0

The timing routes introduced no DRC markers. The existing clearance,
hole-size, hole-to-hole and imported component-bound markers remain
production cleanup items.

## Authority and next step

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

PCB-A09 is complete. The next implementation step is PCB-A10, routing RMII,
CAN, IMU SPI, SWD and the remaining control nets while preserving the
reviewed timing and Ethernet corridors.
