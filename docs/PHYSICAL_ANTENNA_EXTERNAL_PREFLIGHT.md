# Physical antenna external preflight

`tools.physical_antenna_external_preflight` validates structural readiness
of a real physical antenna measurement package.

It checks:

- non-synthetic measured provenance;
- measurement, instrument and calibration identifiers;
- the measurement CSV path and schema;
- the physical-antenna gate configuration;
- basic measurement-ID/frequency consistency for any rows already present.

An empty CSV with the correct header is allowed before collection and returns
`READY_FOR_COLLECTION` with a warning.

This preflight does not modify antenna geometry and does not evaluate gain,
FOV, angular accuracy or ambiguity performance. Final evaluation remains in
`tools.physical_antenna_measurement`.
