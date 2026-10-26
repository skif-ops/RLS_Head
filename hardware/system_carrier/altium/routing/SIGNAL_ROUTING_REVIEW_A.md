# EVT System Carrier Signal Routing Review A

Date: 2026-10-26

`SIGNAL_ROUTING_REVIEW_A=PASS`

Altium Designer 26.10.1 applied the PCB-A10 routing plan to the canonical
native PCB. The resulting canonical PCB SHA-256 is
`3ea321c0c4fbbadd556fe5f07af521ee4f87a8a0db2e51e57ba262f2639fb05f`.

## Reviewed geometry

The PCB-A10 plan covers 28 target signal nets and the required `3V3` and
`GND` stitching for moved components. The plan contains 494 track primitives
and 94 vias. Its geometry validator reports no outside-board primitives and
no clearance conflicts against the immutable pre-A10 planning baseline.

The moved-pad audit covers all 22 pads on 11 moved components. The canonical
native connection audit matches all 494 planned tracks and all 94 planned
vias, reports no missing target nets, no disconnected target signal nets, no
unattached target pads and no orphan copper components.

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
- Track export: `connection_audit/track_inventory.csv`, 1637 rows
- Fill export: `connection_audit/fill_inventory.csv`, 67 rows
- Via export: `connection_audit/via_inventory.csv`, 127 rows
- Native Altium DRC: `connection_audit/connection_drc_report.drc`
- SHA-bound receipt: `connection_audit/connection_integrity_receipt.json`

## Native DRC

Altium ran DRC on the canonical PCB at 20:49:45 on 2026-10-26. The report
contains 114 accepted baseline markers:

- Generic copper clearance: 27
- Ethernet differential-pair class clearance: 27
- 10 mil clearance: 0
- 1.0 mm `NC_TIMING` to `BUCK_SW` clearance: 0
- Hole size: 9
- Hole-to-hole clearance: 1
- Component clearance: 50
- Unrouted net, routing topology, power-plane connect, net antennae and
  height: 0

The remaining clearance, hole-size, hole-to-hole and imported
component-bound markers are production cleanup items. They do not grant
production release authority.

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

PCB-A10 routing and its native connection evidence are complete. Production
release remains blocked until the documented baseline markers and all other
production qualification requirements are resolved.
