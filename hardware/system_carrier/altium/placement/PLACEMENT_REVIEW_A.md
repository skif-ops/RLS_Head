# EVT System Carrier Placement Review A

Date: 2026-10-24

`PLACEMENT_REVIEW_A=PASS`

The native Altium PCB contains the complete provisional EVT placement. The
placement is suitable for routing under the existing Altium equivalence and
EVT routing authority. It is not a production release.

## Reviewed files

- Native PCB: `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`
- Placement plan: `EVT_SYS_CARRIER_PLACEMENT_SYS_001.csv`
- Altium runtime inventory: `placement_runtime_inventory.csv`
- Placement script: `../scripts/EVT_SYS_CARRIER_Placement.pas`
- Focused Altium DRC source: `focused_drc_2026-10-24.drc`

The reviewed PCB SHA-256 is
`3ec2e0eef94b8ef4763f60129f1928bcbb785cb196d6e7d60c40fc907525abab`.

## Placement result

- Plan rows: 92
- Native runtime rows: 92
- Missing or extra designators: 0
- Coordinate or rotation mismatches: 0
- Component centers outside the 100 x 80 mm board: 0
- Locked mounting holes changed: 0
- Locked connector datums changed: 0

The runtime primitive bounds cross the board outline for J4, J5, J6 and SW1.
J4, J5 and J6 are locked edge connectors whose mating geometry is intended to
cross the edge. The SW1 bound includes imported legend/designator geometry;
its placement origin remains at the planned 70.0 x 5.5 mm service position.

## Focused native DRC

Altium Designer 26.10.1 ran the focused placement DRC with Verify Shorting
Copper enabled at 16:28:39 on 2026-10-24, then repeated it after the reviewed
power routing at 16:33:14. Both reports contain the same 77 markers:

- Copper clearance: 13, all internal to the imported D8, U6 and U7 footprints
- Copper clearance between different components: 0
- Hole size: 9, covering the four M3 mounting holes and five connector stakes
  against the generic 100 mil maximum rule
- Component clearance: 55
- Height: 0

The refined placement moves MCU decoupling parts away from adjacent copper,
rotates U5 so its VIN and BUCK_SW sides face the intended power chain, and
separates the dense Ethernet support parts. The component-clearance markers
use imported component bounds that include legend and designator geometry.
The dense functional groups were therefore
reviewed against copper clearance as well as the placed origins and runtime
bounds. No copper collision remains between different components. The 13
internal footprint clearances and the generic hole-size markers remain open
for footprint and rule-scope cleanup before production release.

## Authority

- `ALTIUM_EQUIVALENCE_GATE=PASS`
- Project state: `READY_FOR_ROUTING`
- Routing authority: `AUTHORIZED`
- Production authority: `NOT_AUTHORIZED`

Final enclosure fit, fabricator stack binding, routed-board DRC, thermal and
power review, return-path review, manufacturing outputs and production release
remain gated by the existing production-release workflow.
