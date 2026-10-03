# HIL-R2 bench evidence format

This executable bench format is for timing-quality evidence only.

It covers:

- Radar reference ↔ IMU DRDY residuals;
- PPS residuals;
- holdover error;
- missed capture events;
- monotonic-time failures.

It does not contain control or guidance commands.

## CSV schema

Required header:

```csv
kind,value_us,count
```

Residual rows:

```csv
radar_imu,-84.0,
radar_imu,61.0,
pps,12.0,
holdover,120.0,
```

Counter rows:

```csv
imu_drdy_missed,,1
monotonic_failure,,1
```

Supported `kind` values:

- `radar_imu`
- `pps`
- `holdover`
- `radar_ref_missed`
- `imu_drdy_missed`
- `pps_missed`
- `monotonic_failure`

## Evaluation

Run:

```bash
python -m tools.hil_host.r2_evidence capture.csv \
  --config config/hil_r2_evidence_evt.json \
  --output evidence.json
```

The output schema is `HIL-R2-BENCH-EVIDENCE-001`.

The checked-in configuration is a provisional EVT evidence profile. It must not be represented as measured performance until real bench captures exist.
