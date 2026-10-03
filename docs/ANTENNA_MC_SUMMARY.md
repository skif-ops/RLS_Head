# D1 manufacturing/RF Monte-Carlo summary

The Monte-Carlo summary consumes per-sample antenna simulation results and produces:

- combined-gain P05 / P50 / P95;
- sigmaAz P95;
- sigmaEl P95;
- TRACK-usable probability;
- ambiguity probability;
- mandatory-region robustness.

Input rows are grouped by frequency/Az/El. No production Tx/Rx physical coordinates are required.

## CSV schema

```csv
mc_sample_id,frequency_hz,az_deg,el_deg,combined_gain_delta_db,sigma_az_deg,sigma_el_deg,ambiguity_flag,track_usable,mandatory_region
```

## Baseline gate

The checked-in defaults are provisional evidence rules:

- at least 20 Monte-Carlo samples per cell;
- TRACK-usable probability >= 0.95;
- ambiguity probability <= 0.05.

A mandatory-region cell that fails these conditions makes the summary FAIL.

## CLI

```bash
python -m tools.antenna_mc_summary D1_MC.csv \
  --output D1_MC_SUMMARY.json
```

Output schema: `ANT-D1-MC-SUMMARY-001`.

This is simulation robustness evidence, not physical antenna validation.
