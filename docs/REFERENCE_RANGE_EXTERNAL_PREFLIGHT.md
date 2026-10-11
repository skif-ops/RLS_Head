# Reference-range external preflight

`tools.reference_range_external_preflight` checks structural readiness of
the 50/100/150/200/250/300 m reference-range campaign before field
collection.

It verifies the reference CSV schema and the EVM run-manifest directory.
Each available run manifest must be a non-synthetic, config-locked,
time-aligned, truth-valid `MEASURED_EVM` qualification manifest.

Missing samples or missing range manifests are warnings before collection,
not hard errors. Invalid files or malformed campaign inputs block collection.

`READY_FOR_COLLECTION` is not `REFERENCE_RANGE_MEASURED=PASS`; the normal
reference-range validator and evidence promotion pipeline remain required
after the campaign is complete.
