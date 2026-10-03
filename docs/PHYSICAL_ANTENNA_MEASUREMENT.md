# Physical antenna measurement evidence

This contract validates measured antenna/FOV/angle evidence after the
separate measurement prototype is built.

It does not encode or freeze production Tx/Rx physical coordinates.

## Measurement CSV

Required columns:

```csv
measurement_id,frequency_hz,az_deg,el_deg,realized_gain_db,gain_uncertainty_db,sigma_az_deg,sigma_el_deg,ambiguity_flag,track_usable,high_acc_usable,repeat_count
```

The current EVT validator checks:

- 76 / 78.5 / 81 GHz coverage;
- minimum angular point density;
- boresight presence;
- realized-gain uncertainty;
- repeat count;
- angle sigma;
- ambiguity;
- TRACK/HIGH_ACC usability.

## Manifest

```json
{
  "schema": "ANT-MEASUREMENT-MANIFEST-001",
  "measurement_id": "ANT-MEAS-001",
  "synthetic_fixture": false,
  "evidence_level": "MEASURED_EM",
  "instrument_id": "<instrument>",
  "calibration_id": "<calibration>",
  "measurement_csv": {
    "path": "evidence/antenna/pattern.csv",
    "sha256": "<sha256>"
  }
}
```

## Result

The validator emits `ANT-MEASUREMENT-001`.

Result status can be:

- `PASS`
- `CONDITIONAL`
- `FAIL`
- `INCOMPLETE`
- `HOLD`
- `TEST_READY`
- `INVALID`

Synthetic CI data can only produce `TEST_READY`; it cannot close
`PHYSICAL_ANT_MEASUREMENT`.

Run:

```bash
python -m tools.physical_antenna_measurement \
  --manifest measurement_manifest.json \
  --config config/physical_antenna_measurement_evt.json \
  --repository-root . \
  --output antenna_measurement_result.json
```
