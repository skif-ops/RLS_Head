# Compact enclosure target

Date: 2026-10-27

There is no existing enclosure or STEP model. The mechanical objective is a
custom enclosure with the smallest practical external envelope around the
validated PCB, while preserving connector access, cable bend space, mounting
hardware and GNSS operation.

## Current PCB envelope

- Board: 100 x 80 x 1.60 mm
- Corner radius: 3 mm
- Mounting holes: four M3 NPTH holes at (5,5), (95,5), (5,75) and (95,75) mm
- Exported component bounds: X 1.043 to 95.819 mm, Y 0.803 to 71.994 mm
- Component-bound footprint: 94.776 x 71.190 mm

The current board already uses nearly the full width and height. The left and
right edge connectors, top GNSS region and four mounting holes prevent a
smaller outline without moving EVT-routing-locked datums and rerouting the
board. The compact approach is therefore to fit the enclosure closely around
the validated 100 x 80 mm PCB, not to crop the board outline blindly.

## Required mechanical work

1. Build or obtain verified 3D bodies for the tallest components and all
   externally accessed connectors.
2. Define mating-plug and cable bend keepouts for J1, J4, J5, J6 and J8.
3. Choose the enclosure construction and wall thickness.
4. Determine the minimum internal Z clearance and lid clearance.
5. Create a STEP assembly and verify board, connector, fastener and harness
   access.

Until those checks are complete, the final enclosure dimensions and
production mechanical freeze remain open.

## Authority

- PCB routing authority: `AUTHORIZED`
- Mechanical review: `PENDING`
- Production authority: `NOT_AUTHORIZED`
