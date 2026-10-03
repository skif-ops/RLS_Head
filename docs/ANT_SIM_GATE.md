# ANT-SIM-GATE-001

This gate combines three simulation-evidence artifacts:

1. `ANT-D1-MAP-VALIDATION-001`
2. `ANT-D1-MC-SUMMARY-001`
3. `RAD-LB-006-REVB`

The mandatory range cell is:

- RCS 0.01 m²
- range 300 m

The gate returns:

- `PASS`
- `CONDITIONAL`
- `FAIL`
- `HOLD`

Baseline rules:

- structural map validation must be DATA_READY;
- MC mandatory-region robustness must PASS;
- Rev.B must be PROJECTED;
- at least one mandatory 300 m map point must have positive empirical TRACK projection;
- HIGH_ACC remains separate and can make the result CONDITIONAL rather than silently upgrading TRACK quality.

This is a simulation gate only. Physical antenna measurement, FOV correlation and field-range verification remain open evidence after PASS.
