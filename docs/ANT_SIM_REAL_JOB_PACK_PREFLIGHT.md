# Real ANT-SIM preflight inside external job-pack

When `tools.external_job_pack` selects `ANT_D1_SIM_GATE_REAL`, the
generated job-pack contains an `ant_sim_inputs/` directory for three
upstream simulation-evidence results:

- `map_validation.json` — `ANT-D1-MAP-VALIDATION-001`;
- `mc_summary.json` — `ANT-D1-MC-SUMMARY-001`;
- `rad_lb_revb.json` — `RAD-LB-006-REVB`.

A fresh package is `TEMPLATE_READY` and `WAITING_FOR_UPSTREAM`. Once map
validation is `DATA_READY`, MC summary is `PASS`, and Rev.B is
`PROJECTED`, the preflight changes to `READY_FOR_GATE_ASSEMBLY`.

The validator command is already resolved to the three canonical input
paths. The preflight does not run or assert `ANT-SIM-GATE-001` PASS, does
not substitute physical antenna/field evidence, and does not encode
production Tx/Rx coordinates.
