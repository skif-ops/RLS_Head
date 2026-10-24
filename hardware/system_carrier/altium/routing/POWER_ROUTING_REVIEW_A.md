# EVT System Carrier Power Routing Review A

Date: 2026-10-24

`POWER_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 applied the reviewed EVT power routing to the refined
92-component placement. The result contains 67 copper fills and 23 vias for
VIN_RAW, VIN_PROTECTED, BUCK_SW, 3V3, RADAR_12V and GND. The canonical native
PCB SHA-256 is
`3ec2e0eef94b8ef4763f60129f1928bcbb785cb196d6e7d60c40fc907525abab`.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Power routing script: `../scripts/EVT_SYS_CARRIER_PowerRouting.pas`
- Runtime audit script: `../scripts/EVT_SYS_CARRIER_RoutingAudit.pas`
- Pad export: `pad_geometry.csv`, 529 rows
- Existing track export: `track_inventory.csv`, 1058 rows
- Power fill export: `fill_inventory.csv`, 67 rows
- Power via export: `via_inventory.csv`, 23 rows
- Native Altium DRC: `power_routing_drc_2026-10-24.drc`
- Four-layer review render: `power_routing_review_a.png`

The routing uses the locked EVT stack and power contracts. Wide trunks use
fills on the selected signal layers. Narrow sections occur at component pins,
where the EVT power contract permits local necks. Final copper weight,
fabricator dielectric data and thermal review remain production inputs.

## Native DRC

Altium ran DRC at 16:33:14 with Verify Shorting Copper enabled. The report has
77 markers, matching the reviewed placement baseline:

- Copper clearance: 13, all internal to D8, U6 and U7 footprints
- Copper clearance caused by the reviewed power routing: 0
- Hole size: 9, from the generic 100 mil maximum rule
- Component clearance: 55, from imported component bounds
- Unrouted net, routing topology, hole-to-hole, antenna and height: 0

The power routing introduced no new DRC markers. The 13 internal footprint
clearances, 9 generic hole-size markers and 55 imported component-bound
markers remain recorded for production cleanup.

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

This review authorizes continued native routing work. It does not authorize
manufacturing or production release.
