# AWR EVM profile / compute gate

This tooling evaluates the operational role of measured AWR EVM
profiles without changing radar waveform parameters.

Profile classes:

- TRACK
- LR1
- LR2
- LRX

The software boundary remains radar sensing/tracking through
`TargetState`.

## Inputs

The gate consumes:

1. one `EVM-RUN-MANIFEST-001` per metric row;
2. one aggregate metrics CSV;
3. the provisional EVT gate configuration.

Each metrics row is tied to a specific `run_id` and must match the
manifest profile, range and RCS.

Required metrics include:

- Pd;
- track availability;
- fresh fraction;
- detector/track margin;
- sigma Az / sigma El;
- update rate;
- radar P99 latency;
- compute P99 utilization;
- RAM peak;
- overruns/deadline misses/EDMA errors;
- angle status.

## Current provisional operational targets

- Pd >= 0.90
- track availability >= 0.95
- update >= 20 Hz
- P99 radar latency < 50 ms preferred
- P99 compute utilization <= 80%
- RAM peak <= 80%
- no overruns, deadline misses or EDMA errors
- angle status PASS

Conditional envelope:

- P99 latency < 75 ms
- compute <= 90%
- RAM <= 90%
- angle may be RESTRICTED

A long-range profile must also demonstrate positive measured margin
relative to TRACK under the same range/RCS/dynamics/FOV condition.

LRX is always classified `RESEARCH_ONLY` when valid; it cannot enlarge
operational R_TRACK by itself.

## Evidence boundary

Synthetic CI manifests produce only `TEST_READY`.

Real qualification requires every referenced run manifest to be
`MEASURED_READY`, producing campaign status `MEASURED_READY`.

Run:

```bash
python -m tools.evm_profile_gate \
  --metrics profile_metrics.csv \
  --manifest track_run.json \
  --manifest lr1_run.json \
  --manifest lr2_run.json \
  --manifest lrx_run.json \
  --config config/evm_profile_gate_evt.json \
  --output evm_profile_result.json
```
