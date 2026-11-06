# EVT System Carrier GNSS RF Routing Review A

Date: 2026-10-24

`GNSS_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 routed the GNSS RF corridor from J8-1 through D8-1
and L80-2 to U8-11. The candidate PCB was promoted only after its saved file
matched the canonical PCB byte for byte. The resulting canonical native PCB
SHA-256 is
`cd3a115b8bb27d1f827e21a805a0a9a49749b5d61ce0a563cc954bef9cfe1d89`.

## Reviewed geometry

- Signal path: J8-1 to D8-1 to L80-2 to U8-11
- Layer: Top Layer
- Reference plane: L2 GND
- Trace width: 0.36 mm
- Routed length: 28.543 mm
- Track segments: 4
- Vias: 0

The route follows the locked EVT 50 ohm start geometry. Its entry into D8 is
offset toward the free side of the pad so that the existing internal D8
clearance condition is preserved without creating a new clearance marker.
The final fabricator stack and field-solver geometry remain required before
production release.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- GNSS routing script: `../scripts/EVT_SYS_CARRIER_GnssRouting.pas`
- Runtime audit script: `../scripts/EVT_SYS_CARRIER_RoutingAudit.pas`
- Pad export: `pad_geometry.csv`, 529 rows
- Track export: `track_inventory.csv`, 1062 rows
- Fill export: `fill_inventory.csv`, 67 rows
- Via export: `via_inventory.csv`, 23 rows
- Native Altium DRC: `gnss_routing_drc_2026-10-24.drc`
- Board and corridor render: `gnss_routing_review_a.png`

## Native DRC

Altium ran DRC at 17:21:28 with Verify Shorting Copper enabled. The report has
77 markers, matching the reviewed power-routing baseline:

- Copper clearance: 13, all internal to D8, U6 and U7 footprints
- Copper clearance caused by the GNSS route: 0
- Hole size: 9, from the generic 100 mil maximum rule
- Component clearance: 55, from imported component bounds
- Unrouted net, routing topology, hole-to-hole, antenna and height: 0

The GNSS route introduced no DRC markers. The documented footprint, hole-size
and component-bound markers remain production cleanup items.

## Authority and next step

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

The next implementation step is PCB-A08, routing the Ethernet PHY, ESD and
MagJack MDI differential pairs using the locked EVT 100 ohm start geometry.
