# Measured SYS-ERR gate

This tooling builds `SYS-ERR-GATE-001` from real sensing-side timing and spatial uncertainty evidence.

It does not contain vehicle-control or guidance logic.

## Inputs

A manifest references:

1. `HIL-R2-BENCH-EVIDENCE-001`
2. a CSV of measured/derived sensing uncertainty cells.

Cell CSV fields:

```csv
cell_id,range_m,sigma_range_m,sigma_az_deg,sigma_el_deg,host_attitude_sigma_deg,extrinsic_sigma_deg,angular_rate_deg_s
```

The Radar↔IMU timing sigma is taken from measured HIL-R2 residual RMS and propagated into position error as a first-order sensing term.

For the current boresight budget:

```text
range variance       = sigma_R^2
horizontal angle var = R^2 * (sigma_Az^2 + sigma_att^2 + sigma_ext^2)
vertical angle var   = R^2 * (sigma_El^2 + sigma_att^2 + sigma_ext^2)
timing variance      = (R * omega * sigma_t)^2
```

The reported 3D RMS is the square root of the sum of these variance contributions.

## Current provisional EVT gate

The checked-in configuration requires:

- mandatory cell at 300 m;
- mandatory 300 m position RMS <= 2.10 m;
- Radar↔IMU RMS residual <= 200 us;
- Radar↔IMU max absolute residual <= 250 us;
- at least three evaluated cells.

These are provisional EVT thresholds, not measured performance.

## Evidence boundary

- synthetic fixture -> `TEST_READY`
- non-synthetic but non-measured evidence -> `HOLD`
- real measured evidence -> `PASS` or `FAIL`

Run:

```bash
python -m tools.sys_err_measured_gate \
  --manifest sys_err_manifest.json \
  --config config/sys_err_measured_evt.json \
  --repository-root . \
  --output sys_err_gate.json
```

A resulting real `SYS-ERR-GATE-001` must still pass the project evidence-promotion guard before `SYS_ERR_MEASURED` changes state.
