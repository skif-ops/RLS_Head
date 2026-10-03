# Reference-range EVM ingest

This contract prepares the reference ladder used to estimate the empirical range exponent `n_hat`.

It does **not** claim AWR2944PEVM performance until actual EVM data are supplied.

## Required ladder

The baseline ladder is:

- 50 m
- 100 m
- 150 m
- 200 m
- 250 m
- 300 m

## CSV schema

Required columns:

```csv
run_id,range_m,signal_db,detector_margin_db,detected,track_valid
```

Each row is one frame/sample.

`signal_db` must be a consistently defined calibrated signal metric across all ladder points. The analysis does not silently mix SNR, detector margin, and raw signal power.

## CLI

```bash
python -m tools.reference_range reference_range.csv \
  --output REFERENCE_RANGE_RESULT.json
```

Optional controls:

```text
--min-samples 20
--max-fit-rms-db 2.0
```

## Output

The output schema is `REFERENCE-RANGE-RESULT-001`.

It contains:

- one aggregate point per ladder distance;
- missing and underfilled distances;
- empirical `n_hat`;
- RMS residual of the empirical fit;
- RMS residual against theoretical `R^-4` scaling;
- source run IDs;
- status `DATA_READY`, `INCOMPLETE`, or `FIT_POOR`.

The fit is evidence preparation only. A `DATA_READY` result is not a system range PASS.
