# D1 EM external preflight

`tools.ant_d1_em_external_preflight` checks whether the provenance package
for a real D1 EM solver run is structurally ready before the solver is run.

It validates:

- `ANT-D1-EM-MANIFEST-001` identity fields;
- explicit non-synthetic provenance;
- a real EM evidence level;
- required artifact entries;
- safe relative artifact paths;
- presence of model and material input files;
- presence and JSON parseability of the antenna-map validation config.

The raw solver export and antenna-map output files may be absent at preflight
time; those are reported as warnings because they are produced by the solver.

`READY_FOR_SOLVER_EXECUTION` is not `ANT_D1_EM_REAL=PASS`. After the
solver run, hashes must be finalized and the normal `tools.ant_em_evidence`
validator plus evidence-promotion pipeline must still pass.

This contract intentionally does not encode or freeze production Tx/Rx
physical coordinates.
