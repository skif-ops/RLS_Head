# D1 EM preflight inside external job-pack

When `tools.external_job_pack` selects `ANT_D1_EM_REAL`, the job-pack is
self-contained for external EM execution without encoding production Tx/Rx
coordinates.

It includes:

- `em_package/d1_em_manifest.json` template;
- `em_package/model/` for the real model input and material definition;
- `em_package/output/` for solver export and antenna map;
- `d1_map_validation_config.json`;
- `preflight_config.json`;
- a validator command with the local map-config path resolved.

A fresh template remains `TEMPLATE_READY` but preflight `BLOCKED` until
real model/material inputs and solver/model identifiers are supplied. At that
point preflight may report `READY_FOR_SOLVER_EXECUTION` while solver output
and antenna-map absence remain warnings.

Final hashes, map validation and `ANT_D1_EM_REAL` evidence promotion still
occur only after the actual external solver execution.
