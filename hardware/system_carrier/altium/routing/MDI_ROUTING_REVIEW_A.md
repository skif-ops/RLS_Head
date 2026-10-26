# EVT System Carrier Ethernet MDI Routing Review A

Date: 2026-10-26

`MDI_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 replaced the four Ethernet MDI routes on an isolated
copy of the final PCB-A10 geometry. The candidate passed native DRC and
connection audit before byte-identical promotion to the canonical
`EVT_SYS_CARRIER.PcbDoc`. The promoted PCB SHA-256 is
`fc3404b281f3ca76123a8dd68b6076a4e50f5d867ed9fc9582fb6f6ef248ba44`.

## Reviewed geometry

| Net | Primary length | Segments | Vias |
| --- | ---: | ---: | ---: |
| `ETH_TXP` | 33.744012 mm | 16 | 2 |
| `ETH_TXN` | 33.743961 mm | 18 | 2 |
| `ETH_RXP` | 35.855206 mm | 23 | 7 |
| `ETH_RXN` | 35.855193 mm | 17 | 5 |

TX skew is 0.000051 mm and RX skew is 0.000013 mm. The exact offline
clearance validator reports zero conflicts. The native audit finds all 74
planned MDI segments and all 16 planned MDI vias, with all 16 endpoint pads
connected.

## Native validation

- MDI differential-pair class clearance: 0
- Unrouted nets: 0
- Routing topology violations: 0
- Hole-to-hole violations: 0
- Net antennae: 0
- Route-induced timing markers: 0
- Copper primitives outside the 100 x 80 mm board: 0
- Missing planned tracks or vias: 0
- Disconnected target signal nets: 0
- Unattached target pads: 0
- Orphan copper components: 0

The native report contains 75 pre-existing generic, hole-size and component
clearance markers. They are not caused by the MDI routes and remain production
cleanup items.

## Reviewed evidence

- Exact route plan: `mdi_drc_candidate/mdi_routing_plan.json`
- Native DRC: `mdi_drc_candidate/native_drc_report.drc`
- Native connection audit: `mdi_drc_candidate/native_connection_audit.json`
- Structural equivalence: `mdi_drc_candidate/structural_equivalence.json`
- Native file preflight: `mdi_drc_candidate/native_file_preflight.json`
- Promotion receipt: `mdi_drc_candidate/promotion_receipt.json`
- Canonical connection receipt: `connection_audit/connection_integrity_receipt.json`

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

The MDI routing correction is complete. This review does not grant production
release authority.
