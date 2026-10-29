# EVT System Carrier Timing Routing Review A

Date: 2026-10-29

`TIMING_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 routed `GNSS_PPS`, `IMU_DRDY` and `RADAR_REF` on
the canonical native PCB. The compact-board routing uses the available copper
layers and through vias while retaining the locked 0.20 mm trace width. The
resulting canonical PCB SHA-256 is
`0dacc26bbba8b95c0c1bc591546ef879edb8815cb134b4c30d1742d85fdcc1fd`.

## Reviewed geometry

The audit rebuilds a graph from native track intersections, via spans and pad
bounds. Each required endpoint pair belongs to one connected component, and
all track primitives assigned to each timing net are part of that component.

| Net | Endpoint pair | Length | Segments | Vias | Layers |
| --- | --- | ---: | ---: | ---: | --- |
| `GNSS_PPS` | J8-4 to U1-40, with D8-4 branch | 49.962051 mm | 9 | 3 | L1, L2, L32 |
| `IMU_DRDY` | U2-4 to U1-80 | 44.524254 mm | 6 | 0 | L1 |
| `RADAR_REF` | U1-79 to J4-4 | 23.178526 mm | 4 | 1 | L1, L2 |

The measured edge clearance from these routes to `BUCK_SW` is at least
5.203308 mm. This exceeds the 1.0 mm quiet-clearance contract.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Timing routing script: `../scripts/EVT_SYS_CARRIER_TimingRouting.pas`
- Runtime audit script: `../scripts/EVT_SYS_CARRIER_RoutingAudit.pas`
- Pad export: `connection_audit/pad_geometry.csv`, 483 rows
- Track export: `connection_audit/track_inventory.csv`, 1378 rows
- Fill export: `connection_audit/fill_inventory.csv`, 60 rows
- Via export: `connection_audit/via_inventory.csv`, 115 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- Multilayer review render: `timing_routing_review_a.png`
- SHA-bound result: `timing_routing_drc_summary.json`

## Native DRC

Altium ran DRC on the canonical native PCB at 14:22:30 on 2026-10-28.
The report contains zero violations and zero warnings. In particular, the
timing-to-`BUCK_SW` clearance, unrouted-net, routing-topology, power-plane,
hole-size, hole-to-hole, net-antennae and component-clearance checks are all
zero.

The independent connection-integrity gate also reports zero copper or pad
primitives outside the 90 by 70 mm board and confirms the complete endpoint
baseline.

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

This review authorizes routing work only. Production release remains blocked
until the separate production-qualification requirements are completed.
