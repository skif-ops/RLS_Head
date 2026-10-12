# D1 EM external preflight

`tools.ant_d1_em_external_preflight` verifies structural readiness of a
real D1 EM solver provenance package before external solver execution.

The preflight requires:

- model ID/revision and solver name/version;
- explicit non-synthetic provenance;
- a real EM evidence level;
- artifact slots for model input, material definition, solver export and
  antenna map;
- existing model/material input files inside the package root.

Before solver execution, missing solver export and antenna map are warnings,
not errors. Their final files and SHA-256 values are mandatory later in the
normal `tools.ant_em_evidence` validator.

The preflight does not encode or freeze production Tx/Rx physical
coordinates and does not claim `ANT_D1_EM_REAL=PASS`.
