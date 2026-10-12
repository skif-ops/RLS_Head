# System Carrier footprint readiness

Rev.A now separates package selection from footprint freeze.

A component may be:

- `LOCKED` — exact footprint ID is accepted for Rev.A;
- `VERIFY_REQUIRED` — a stock/project candidate may exist but must be compared
  against the manufacturer land pattern;
- `CUSTOM_REQUIRED` — project-local footprint is required.

The PCB placement gate must not be treated as frozen while
`unresolved_refs` is non-empty.

Current conservative decisions include:

- STM32H753 LQFP176 — locked existing stock footprint;
- TCAN3404 DRB0008A — locked manufacturer-specific KiCad footprint;
- CAN ESD DBZ/SOT-23 — locked stock footprint;
- TPS259470 RPW, ICM-42688-P LGA and NEO-M9N module — project-local footprint
  path until their land patterns are verified.

This gate intentionally prefers an unresolved status over guessing a pad
geometry.
