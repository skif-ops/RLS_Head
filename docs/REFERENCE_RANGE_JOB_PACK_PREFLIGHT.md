# Reference-range preflight inside external job-pack

When `tools.external_job_pack` selects `REFERENCE_RANGE_MEASURED`, the
generated job-pack now contains:

- `measurement_pack/reference_range.csv`;
- `measurement_pack/run_manifests/` for real EVM run manifests;
- `preflight_config.json`;
- the reference-range preflight command in the execution checklist.

A fresh template is expected to be `TEMPLATE_READY` and
`READY_FOR_COLLECTION` with warnings that no samples or range manifests
exist yet. Invalid JSON manifests or malformed campaign inputs change the
preflight status to `BLOCKED`.

The required ladder remains 50, 100, 150, 200, 250 and 300 m. Campaign
completion and DATA_READY are evaluated only after real collection by the
normal reference-range validator and evidence-promotion pipeline.
