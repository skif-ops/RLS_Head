# Compact enclosure target

Date: 2026-10-30

There is no existing enclosure or STEP model. The mechanical objective is a
custom enclosure with the smallest practical external envelope around the
validated PCB, while preserving connector access, cable bend space, mounting
hardware and GNSS operation.

## Current PCB envelope

- Board: 90 x 70 x 1.60 mm
- Corner radius: 3 mm
- Mounting holes: four M3 NPTH holes at (5,5), (85,5), (5,65) and (85,65) mm
- Component and connector clearance must be taken from the current native Altium PCB and assembly data.

The validated board has already been reduced to 90 x 70 mm. Any further outline
change would move EVT-routing-locked datums and require a controlled PCB ECO,
rerouting, DRC and connection-integrity validation. Enclosure manufacture is
outside the current pilot scope and is not a pilot-package blocker.

## Required mechanical work

1. If enclosure work enters scope, build or obtain verified 3D bodies for the
   tallest components and all externally accessed connectors.
2. Define mating-plug and cable bend keepouts for J1, J4, J5, J6 and J8.
3. Choose the enclosure construction and wall thickness.
4. Determine the minimum internal Z clearance and lid clearance.
5. Create a STEP assembly and verify board, connector, fastener and harness
   access. Create antenna mounts only when assembly technology requires them.

Until those checks are complete, the final enclosure dimensions and
production mechanical freeze remain open.

## Authority

- PCB routing authority: `AUTHORIZED`
- Mechanical review: `DEFERRED_NOT_BLOCKING_PILOT`
- Production authority: `NOT_AUTHORIZED`
