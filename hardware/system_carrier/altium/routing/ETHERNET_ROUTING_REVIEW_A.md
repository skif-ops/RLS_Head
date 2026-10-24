# EVT System Carrier Ethernet MDI Routing Review A

Date: 2026-10-24

`ETHERNET_ROUTING_REVIEW_A=PASS`

This PASS covers the native EVT routing baseline, connectivity, differential
start geometry, pair length matching and Altium DRC. It does not authorize
production fabrication. The saved candidate and canonical PCB files matched
byte for byte at promotion. The resulting canonical native PCB SHA-256 is
`4217bdc4caf00ead347d41246ce13576166f6deabafc94e74183ef9debdbb494`.

## Reviewed geometry

- Nets: `ETH_TXP`, `ETH_TXN`, `ETH_RXP`, `ETH_RXN`
- Path domain: U3 PHY, R601-R604 terminations, D3 ESD and J6 MagJack
- Trace width: 0.26 mm
- Pair center spacing on the primary parallel corridors: 0.46 mm
- Pair edge gap on the primary parallel corridors: 0.20 mm
- Via geometry: 0.60 mm pad, 0.30 mm drill
- Routed Ethernet segments: 65
- Routed Ethernet vias: 11

The native geometry export and a graph rebuilt at every same-layer segment
intersection confirm that all four U3 pads, termination pads, D3 pads and J6
pads are connected on their intended nets.

| Net | U3 to J6 length | Routed-tree length | Segments | Vias |
| --- | ---: | ---: | ---: | ---: |
| ETH_TXP | 38.703926 mm | 64.527804 mm | 25 | 3 |
| ETH_TXN | 38.663045 mm | 52.868046 mm | 11 | 1 |
| ETH_RXP | 40.933074 mm | 66.838102 mm | 19 | 4 |
| ETH_RXN | 40.933050 mm | 58.529361 mm | 10 | 3 |

The resulting U3-to-J6 intra-pair skew is 0.040881 mm for TX and 0.000024 mm
for RX.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Ethernet routing script: `../scripts/EVT_SYS_CARRIER_EthernetRouting.pas`
- Runtime audit script: `../scripts/EVT_SYS_CARRIER_RoutingAudit.pas`
- Pad export: `pad_geometry.csv`, 529 rows
- Track export: `track_inventory.csv`, 1127 rows
- Fill export: `fill_inventory.csv`, 67 rows
- Via export: `via_inventory.csv`, 34 rows
- Native Altium DRC: `ethernet_routing_drc_2026-10-24.drc`
- Board and corridor render: `ethernet_routing_review_a.png`

## Native DRC

Altium Designer 26.10.1 ran DRC at 18:20:29 with Verify Shorting Copper
enabled. The report has 77 markers, matching the reviewed power and GNSS
routing baseline:

- Copper clearance: 13, all internal to D8, U6 and U7 footprints
- Copper clearance caused by the Ethernet route: 0
- Hole size: 9, from the generic 100 mil maximum rule
- Component clearance: 55, from imported component bounds
- Unrouted net, routing topology, hole-to-hole, antenna and height: 0

The Ethernet route introduced no DRC markers. The documented footprint,
hole-size and component-bound markers remain production cleanup items.

## EVT limitations

The 0.26 mm width and 0.20 mm pair gap are the locked analytical EVT start
geometry for the provisional 0.18 mm L1-to-L2 dielectric. A fabricator field
solver must bind the final copper and dielectric values before production.

Some ESD, termination and connector escape segments use Bottom Layer and the
main TXN and RXP paths have one layer transition each while their partners
remain on Top Layer. Production review must rework or validate these
transitions with a continuous reference and paired return-path treatment. This
EVT review does not accept the current transitions as production SI signoff.

## Authority and next step

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

The next implementation step is PCB-A09, routing `GNSS_PPS`, `RADAR_REF` and
`IMU_DRDY` with quiet return paths and no parallel coupling to the Ethernet
MDI corridor.
