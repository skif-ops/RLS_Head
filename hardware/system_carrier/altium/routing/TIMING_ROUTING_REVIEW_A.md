# EVT System Carrier Timing Routing Review A

Date: 2026-10-30

`TIMING_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 contains the routed `GNSS_PPS`, `IMU_DRDY` and
`RADAR_REF` nets on the canonical native PCB. The final routes retain the
locked 0.20 mm trace width. `GNSS_PPS` and `IMU_DRDY` stay on L1.
`RADAR_REF` uses L1 and L3 with one through via. The resulting canonical PCB
SHA-256 is
`4c547f8a5a327ec0ebd99c394de4c13a4de0d6f4aac3042bb3d1ddfc74e785a5`.

## Reviewed geometry

The audit rebuilds a graph from native track intersections, via spans and pad
bounds. Each required endpoint pair belongs to one connected component, and
all track primitives assigned to each timing net are part of that component.

| Net | Endpoint pair | Length | Segments | Vias | Layers |
| --- | --- | ---: | ---: | ---: | --- |
| `GNSS_PPS` | J8-4 to U1-40 | 69.353082 mm | 22 | 0 | L1 |
| `IMU_DRDY` | U2-4 to U1-80 | 44.524254 mm | 6 | 0 | L1 |
| `RADAR_REF` | U1-79 to J4-4 | 23.428538 mm | 6 | 1 | L1, L3 |

The measured edge clearance from these routes to `BUCK_SW` and `BUCK5_SW` is
at least 2.525014 mm. This exceeds the 1.0 mm quiet-clearance contract.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Timing routing gate: `../../../../tools/altium_timing_routing_gate.py`
- Runtime connection audit: `../scripts/EVT_SYS_CARRIER_ConnectionAudit.pas`
- Pad export: `connection_audit/pad_geometry.csv`, 483 rows
- Track export: `connection_audit/track_inventory.csv`, 1500 rows
- Fill export: `connection_audit/fill_inventory.csv`, 60 rows
- Via export: `connection_audit/via_inventory.csv`, 114 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- SHA-bound result: `timing_routing_drc_summary.json`

## Native DRC

Altium ran DRC on the canonical native PCB at 14:13:17 on 2026-10-30.
The report contains zero violations and zero warnings. In particular, the
timing-to-`BUCK_SW` clearance, unrouted-net, routing-topology, power-plane,
hole-size, hole-to-hole, net-antennae and component-clearance checks are all
zero.

The independent connection-integrity gate also reports zero copper or pad
primitives outside the 90 by 70 mm board and confirms the complete endpoint
baseline.

## Authority

- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

This review authorizes routing work only. Production release remains blocked
until the separate production-qualification requirements are completed.
