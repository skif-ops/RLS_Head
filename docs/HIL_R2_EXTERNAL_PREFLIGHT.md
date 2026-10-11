# HIL-R2 external preflight

`tools.hil_r2_external_preflight` checks whether a HIL-R2 bench timing job
is structurally ready before real collection starts.

It verifies:

- the expected `kind,value_us,count` CSV structure;
- basic row parseability;
- presence of the complete HIL-R2 gate configuration;
- the distinction between collection readiness and gate PASS.

An empty timing CSV with the correct header is allowed and produces
`READY_FOR_COLLECTION` with a warning, because the preflight runs before
data collection.

After collection, the normal `tools.hil_host.r2_evidence` evaluator still
enforces sample counts, timing residuals, missed-event limits, holdover and
monotonic-time criteria.
