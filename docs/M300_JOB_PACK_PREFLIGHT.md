# M300 preflight inside external job-pack

When `tools.external_job_pack` selects `M300_MEASURED`, the generated
job-pack now contains `preflight_config.json` and an explicit M300 preflight
step in the execution checklist.

A freshly generated template remains:

- job-pack validation: `TEMPLATE_READY`;
- M300 collection preflight: `BLOCKED`.

That is intentional because the template still contains field placeholders
and no real timing/environment metadata.

After the operator fills the actual run ID, profile/config identifiers,
source commit, target ID, time window and environmental metadata, rerun:

```bash
python -m tools.external_job_pack validate outgoing/m300
```

The validation result will expose `preflight_status`. Qualification
collection should begin only when that status is
`READY_FOR_COLLECTION`.

This status is still not M300 evidence or M300 PASS.
