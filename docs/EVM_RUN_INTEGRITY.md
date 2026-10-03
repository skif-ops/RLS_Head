# EVM run manifest integrity gate

Each physical EVM run should carry an `EVM-RUN-MANIFEST-001`.

The validator checks:

- run/profile/target identity;
- profile SHA-256 and source commit identity;
- monotonic run-time bounds;
- positive range and RCS;
- truth status;
- time-alignment validity;
- configuration lock for qualification runs;
- environment metadata;
- file-level SHA-256 values;
- required truth/radar/diagnostics file kinds;
- raw-capture consistency.

Qualification evidence is `MEASURED_READY` only when:

- the run is not synthetic;
- evidence level is measured;
- configuration is locked;
- truth is VALID;
- time alignment is valid.

Synthetic CI fixtures receive `TEST_READY` and cannot become measured evidence.

The reference ladder helper additionally checks the complete measured 50/100/150/200/250/300 m set and rejects mixed profile or target IDs.
