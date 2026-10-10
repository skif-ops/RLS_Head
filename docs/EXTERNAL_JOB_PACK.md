# External evidence job pack

`tools.external_job_pack` materializes one prioritized execution recipe into
a self-contained external job-pack.

For a measurement-backed item such as `M300_MEASURED`, the job-pack contains:

- the selected `EXTERNAL-EXECUTION-RECIPE-001` row;
- the existing measurement-pack template;
- an execution checklist;
- a machine-readable `EXTERNAL-EVIDENCE-JOB-PACK-001` manifest.

Example:

```bash
python -m tools.external_job_pack build \
  external_execution_queue.json \
  --output-dir outgoing/m300 \
  --priority 1

python -m tools.external_job_pack validate outgoing/m300
```

The generated directory is scaffolding only. It intentionally keeps
measurement templates marked as templates and does not generate any measured
values, pass/fail outcomes, or promotable evidence.

After real collection, follow the validator command in
`execution_recipe.json`, then create an `EXTERNAL-EVIDENCE-BUNDLE-001`
and pass it through the ingest/promotion pipeline.
