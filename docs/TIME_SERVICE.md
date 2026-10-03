# Disciplined Time Service

This module provides a sensing-side monotonic time mapping for
RadarMeasurement/HostState alignment.

It does not contain vehicle-control or guidance logic.

## States

- `UNINITIALIZED`
- `PHASE_ONLY`
- `LOCKED`
- `HOLDOVER`

The first PPS establishes phase. A second monotonic PPS observation
estimates affine rate correction in ppb. Implausible rate steps are
rejected.

## Holdover uncertainty

The current deterministic baseline uses a conservative first-order
bound:

```text
sigma_holdover_us =
  phase_sigma_us +
  drift_sigma_ppm * elapsed_seconds
```

For the 2 ppm golden vector this gives:

- 1 s -> 2 us
- 10 s -> 20 us
- 30 s -> 60 us
- 60 s -> 120 us
- 300 s -> 600 us

These are deterministic software vectors, not measured oscillator
performance.

## Evidence boundary

`TIME_SERVICE_LOGIC=PASS` means:

- host-native deterministic tests pass;
- Cortex-M7 cross-link retains the code path.

It does not close:

- real PPS residual;
- real Radar↔IMU residual;
- oscillator/temperature holdover performance.

Those remain under `HIL_R2_BENCH_MEASURED` and
`SYS_ERR_MEASURED`.
