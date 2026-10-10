# M300 external preflight

`tools.m300_external_preflight` checks whether an M300 job-pack has been
filled sufficiently to begin a real qualification collection.

It requires, among other things:

- QUALIFY mode;
- 300 m nominal range;
- 0.01 m² RCS target declaration;
- valid truth;
- valid time alignment;
- locked configuration;
- MEASURED_EVM evidence level;
- explicit non-synthetic provenance;
- a valid measurement time window;
- environment metadata;
- the expected range-sample CSV structure.

The preflight deliberately permits an empty data CSV and reports that as a
warning, because it is intended to run before collection.

`READY_FOR_COLLECTION` is not evidence and is not an M300 PASS. After
collection, the data still must pass the normal M300 validator, external
evidence ingest, and promotion pipeline.
