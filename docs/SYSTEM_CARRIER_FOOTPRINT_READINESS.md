# System Carrier footprint readiness

Rev.A separates package selection from footprint freeze.

A component may be:

- `LOCKED` — exact footprint ID is accepted for Rev.A;
- `VERIFY_REQUIRED` — a candidate exists but still requires manufacturer
  land-pattern verification;
- `CUSTOM_REQUIRED` — a project-local footprint is still required.

## Rev.A footprint freeze

The current authoritative plan is expected to be
`FOOTPRINT_FREEZE_READY`: every device tracked by
`FOOTPRINT_PLAN_SYS_001.csv` is `LOCKED`.

Project-local verified footprints include:

- ICM-42688-P LGA14;
- NEO-M9N LCC24;
- ESD0P2RF-02LS PG-TSSLP-2-1;
- TPS259470A RPW0010A, shared by U6 and U7.

The RPW0010A footprint deliberately preserves the manufacturer's non-generic
VQFN-HR topology with four custom corner pads, side pads and two long center
pads. It is not substituted with a generic 2×2 mm QFN.

Stock footprints remain locked where the manufacturer package matches the
KiCad library geometry, including STM32H753 LQFP176, LAN8742A SQFN24-EP,
TCAN3404 DRB0008A, TPS62132 RGT0016C and the selected ESD packages.

## Validation

The footprint readiness gate verifies that every project-local `LOCKED`
library ID resolves to an actual `.kicad_mod` file.

The dedicated CAD CI job additionally copies the generated
`SystemCarrier_Local.pretty` library and runs KiCad 9
`kicad-cli fp upgrade --force` on a disposable copy. This makes malformed
local footprint syntax a CI failure before Review A or PCB placement.

Footprint freeze does not close schematic Review A. The separate MagJack
manufacturer drawing/pinout blocker and any remaining schematic placeholders
must still be resolved independently.
