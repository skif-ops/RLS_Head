# EVT System Carrier Timing Routing Review A

Date: 2026-10-26

`TIMING_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 routed `GNSS_PPS`, `IMU_DRDY` and `RADAR_REF` on
the canonical native PCB. PCB-A10 later rerouted `GNSS_PPS` while preserving
the timing contract. The resulting canonical PCB SHA-256 is
`fc3404b281f3ca76123a8dd68b6076a4e50f5d867ed9fc9582fb6f6ef248ba44`.

## Reviewed geometry

All three routes use 0.20 mm Top Layer tracks and no vias. A graph rebuilt
from the native track intersections and pad bounds confirms one connected
component between each required endpoint pair.

| Net | Endpoint pair | Length | Segments | Vias |
| --- | --- | ---: | ---: | ---: |
| `GNSS_PPS` | U8-3 to U1-40 | 44.746448 mm | 10 | 0 |
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
- Track export: `connection_audit/track_inventory.csv`, 1640 rows
- Fill export: `connection_audit/fill_inventory.csv`, 67 rows
- Via export: `connection_audit/via_inventory.csv`, 132 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- Board render: `timing_routing_review_a.png`
- SHA-bound result: `timing_routing_drc_summary.json`

## Native DRC

Altium ran DRC on a byte-identical promotion candidate at 22:22:58 on
2026-10-26. The report has 75 accepted baseline markers:

- Generic copper clearance: 16
- Ethernet class clearance: 0
- 1.0 mm `NC_TIMING` to `BUCK_SW` clearance: 0
- 10 mil clearance: 0
- Hole size: 9
- Hole-to-hole clearance: 0
- Component clearance: 50
- Unrouted net, routing topology, power-plane connect and net antennae: 0

The timing routes introduced no DRC markers. The existing generic clearance,
hole-size and imported component-bound markers remain production cleanup
items.

## Authority and next step

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

PCB-A10 signal routing and the corrected Ethernet MDI routes are complete.
Production release remains blocked until the accepted baseline markers and
the remaining production qualification requirements are resolved.
