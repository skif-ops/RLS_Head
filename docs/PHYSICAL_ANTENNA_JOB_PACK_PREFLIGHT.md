# Physical antenna preflight inside external job-pack

When `tools.external_job_pack` selects `PHYSICAL_ANT_MEASUREMENT`, the
generated job-pack includes:

- `measurement_pack/antenna_measurement_manifest.json`;
- `measurement_pack/antenna_measurement.csv`;
- a copied `physical_antenna_measurement_config.json`;
- `preflight_config.json`;
- a validator command matching the actual
  `tools.physical_antenna_measurement` CLI.

The manifest CSV path is rewritten relative to the job-pack root, so no
manual path repair is required.

A fresh template remains `TEMPLATE_READY` but preflight `BLOCKED` until
real measurement, instrument and calibration identifiers are supplied.
After those identifiers are filled, an empty correctly structured CSV is
`READY_FOR_COLLECTION` with a warning that samples do not yet exist.

This workflow does not modify antenna geometry and does not evaluate gain,
FOV, angular accuracy or ambiguity performance before real measurements are
collected.
