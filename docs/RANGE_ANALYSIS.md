# Range analysis baseline

This module prepares the first EVM evidence for `M300_REPORT-001` and the empirical range exponent `n_hat`.

It does not claim any measured range until real EVM data are supplied.

## M300 CSV

Required columns:

```csv
range_m,detected,track_valid,fresh,detector_margin_db
```

Example invocation:

```bash
python -m tools.range_analysis run.csv --output M300_REPORT.json
```

The current provisional TRACK criteria are:

- frame detection probability >= 0.90;
- track availability >= 0.95.

False-track qualification remains a separate campaign statistic and is not silently inferred from this row-level CSV.

## Reference ladder fit

`fit_range_exponent()` fits

```text
signal_dB = A - 10*n_hat*log10(range_m)
```

and reports `n_hat` plus RMS fit residual.

Theoretical free-space radar power scaling is represented by `n = 4`, but measured `n_hat` is retained separately.
