# HIL-R2 preflight inside external job-pack

When `tools.external_job_pack` selects
`HIL_R2_BENCH_MEASURED`, the generated job-pack now includes:

- `measurement_pack/timing_capture.csv`;
- a copied, self-contained `hil_r2_gate_config.json`;
- `preflight_config.json`;
- the HIL-R2 preflight command in the execution checklist.

A fresh HIL-R2 template is expected to be `TEMPLATE_READY` and
`READY_FOR_COLLECTION` with a warning that the timing CSV has no samples.
That means the bench job is structurally ready to begin collection.

It does not mean the HIL-R2 evidence gate has passed. After collection, the
normal `tools.hil_host.r2_evidence` evaluator still applies the required
sample counts and timing/error thresholds.
