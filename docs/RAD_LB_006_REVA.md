# RAD-LB-006 Rev.A

Rev.A combines two measured-input artifacts:

- `REFERENCE-RANGE-RESULT-001` — reference ladder and empirical `n_hat`;
- `M300-REPORT-001` — the 300 m / 0.01 m² anchor.

The output schema is `RAD-LB-006-REVA`.

Rev.A intentionally contains **no custom antenna correction**. Antenna/FOV/angle terms belong to later revisions after D1 EM evidence exists.

## Grid

The current output grid contains:

- RCS: 0.01 / 0.03 / 0.10 m²;
- range: 300 / 400 / 500 / 600 m.

For every cell it reports both:

- empirical range scaling using measured `n_hat`;
- theoretical `n = 4` scaling.

## Evidence semantics

A positive projected margin is not a verified range result.

`TRACK_PASS` at the measured 300 m anchor is preserved separately from projected cells. Any later measured cell supersedes the projection for that cell.

## CLI

```bash
python -m tools.rad_lb006 \
  --reference REFERENCE_RANGE_RESULT.json \
  --m300 M300_REPORT.json \
  --output RAD_LB_006_REVA.json
```
