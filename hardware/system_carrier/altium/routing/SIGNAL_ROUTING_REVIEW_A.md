# EVT System Carrier Signal Routing Review A

Date: 2026-10-26

`SIGNAL_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 applied the PCB-A10 routing plan to the canonical
native PCB. The resulting canonical PCB SHA-256 is
`fc3404b281f3ca76123a8dd68b6076a4e50f5d867ed9fc9582fb6f6ef248ba44`.

## Reviewed geometry

The PCB-A10 plan covers 28 target signal nets and the required `3V3` and
`GND` stitching for moved components. The reviewed geometry contains 562
planned track primitives and 109 planned vias after replacing the four MDI
routes for the final J6 placement. Its geometry validator reports no
outside-board primitives and no route-induced clearance conflicts.

The moved-pad audit covers all 22 pads on 11 moved components. The canonical
native connection audit matches all 562 planned tracks and all 109 planned
vias. It reports no missing target nets, no disconnected target signal nets,
no unattached target pads and no orphan copper components.

## Reviewed evidence

- Native PCB: `../native/EVT_SYS_CARRIER.PcbDoc`
- Routing application script: `../native/EVT_SYS_CARRIER_SignalRoutingCandidate.pas`
- Runtime audit script: `../native/EVT_SYS_CARRIER_RoutingAuditCandidate.pas`
- Canonical export script: `../native/EVT_SYS_CARRIER_ConnectionAudit.pas`
- Immutable planning input: `a10_planning_baseline/`
- Planner result: `../../../../build-cad/pcb_a10_plan.json`
- Planner validation: `../../../../build-cad/pcb_a10_validation.json`
- Moved-pad audit: `../../../../build-cad/pcb_a10_moved_pad_audit.json`
- Canonical native audit: `connection_audit/native_connection_audit.json`
- Native file preflight: `connection_audit/canonical_native_file_preflight.json`
- Pad export: `connection_audit/pad_geometry.csv`, 529 rows
- Track export: `connection_audit/track_inventory.csv`, 1640 rows
- Fill export: `connection_audit/fill_inventory.csv`, 67 rows
- Via export: `connection_audit/via_inventory.csv`, 132 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- SHA-bound receipt: `connection_audit/connection_integrity_receipt.json`
- MDI promotion receipt: `mdi_drc_candidate/promotion_receipt.json`

## Native DRC

Altium ran DRC on a byte-identical promotion candidate at 22:22:58 on
2026-10-26. The report contains 75 accepted baseline markers:

- Generic copper clearance: 16
- Ethernet differential-pair class clearance: 0
- 10 mil clearance: 0
- 1.0 mm `NC_TIMING` to `BUCK_SW` clearance: 0
- Hole size: 9
- Hole-to-hole clearance: 0
- Component clearance: 50
- Unrouted net, routing topology, power-plane connect, net antennae and
  height: 0

The remaining generic clearance, hole-size and imported component-bound
markers are production cleanup items. They do not grant production release
authority.

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

PCB-A10 routing and its native connection evidence are complete. Production
release remains blocked until the documented baseline markers and all other
production qualification requirements are resolved.
