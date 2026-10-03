# D1 antenna-map validation

Before a D1 EM export is used by RAD-LB-006 Rev.B it is validated as machine-readable evidence.

The validator checks:

- required simulation cases and frequency points;
- minimum point count per case/frequency;
- boresight presence;
- duplicate angular cells;
- finite values and legal angle ranges;
- non-negative angle sigmas;
- ambiguity/TRACK consistency;
- HIGH_ACC/TRACK consistency.

The baseline frequencies are 76 / 78.5 / 81 GHz. This is an evidence-export contract, not a production antenna geometry freeze.

## CLI

```bash
python -m tools.antenna_map_validate D1_ANTENNA_MAP.csv \
  --config config/d1_map_validation_evt.json \
  --output ANT_D1_MAP_VALIDATION.json
```

Output schema: `ANT-D1-MAP-VALIDATION-001`.

A `DATA_READY` result only means the map is structurally usable as simulation evidence. It does not constitute physical antenna validation.
