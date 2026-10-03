# HW-SENSOR-PROTOTYPE-GATE-001

This gate controls only authorization of a **measurement prototype** for radar/antenna characterization.

It consumes:

- `M300-REPORT-001`;
- `ANT-SIM-GATE-001`;
- `SYS-ERR-GATE-001`.

## Evidence rule

The gate refuses to authorize hardware from synthetic, calculated or CI-only evidence.

The 300 m mandatory anchor must have:

- `TRACK_PASS`;
- evidence level `MEASURED_EVM` or another measured level.

SYS-ERR must likewise carry measured evidence.

## Outputs

- `PASS / AUTHORIZED_FOR_MEASUREMENT`
- `CONDITIONAL / CONDITIONAL_MEASUREMENT_PROTOTYPE`
- `HOLD / NOT_AUTHORIZED`
- `FAIL / NOT_AUTHORIZED`

Even PASS does **not** authorize:

- production antenna freeze;
- integrated radar PCB production;
- production waveform freeze.

Those remain behind later gates.
