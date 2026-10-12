# SYS-ERR preflight inside external job-pack

When `tools.external_job_pack` selects `SYS_ERR_MEASURED`, the generated
job-pack includes:

- `measurement_pack/sys_err_manifest.json`;
- `measurement_pack/sys_err_cells.csv`;
- `measurement_pack/timing/` for the real HIL-R2 bench PASS JSON;
- a copied `sys_err_gate_config.json`;
- `preflight_config.json`;
- a validator command matching the actual `tools.sys_err_measured_gate` CLI.

The manifest paths are rewritten for the job-pack root so no manual path
repair is required.

A fresh package is `TEMPLATE_READY` and `WAITING_FOR_HIL_R2`. Once a real
`HIL-R2-BENCH-EVIDENCE-001` with `gate_status=PASS` is placed at
`measurement_pack/timing/hil_r2_evidence.json`, the preflight can move to
`READY_FOR_COLLECTION`.

This still does not calculate or assert SYS-ERR PASS; final evaluation remains
in `tools.sys_err_measured_gate`.
