# RLS_Head

Radar sensing/tracking project. The implemented software boundary in this repository ends at `TargetState`.

## Current executable baseline

- HIL-R1 host-native golden suite and TargetStateV1 wire contract
- HIL-R2 deterministic timing/host-state math
- disciplined PPS Time Service with holdover logic
- SYS-ERR covariance propagation and TargetState uncertainty ledger
- STM32H753 Cortex-M7 cross-link/memory-layout gate
- HIL-R2 bench evidence ingest
- reference-range / M300 analysis
- RAD-LB-006 Rev.A / Rev.B projected evidence pipeline
- D1 antenna-map validation and Monte-Carlo robustness tooling
- ANT-SIM-GATE and HW sensor measurement-prototype gate logic
- System Carrier authoritative design inputs and Review A tooling (real CAD/ERC evidence still open)

- hash-verified measured-evidence promotion guard
- physical antenna measurement evidence tooling

## Evidence status

The authoritative evidence state is tracked in:

`evidence/project_evidence_manifest.json`

CI fixtures and software/cross-build success are intentionally kept separate from physical measured evidence.

At the current baseline, real M300, reference-range, HIL-R2 bench timing, measured SYS-ERR, actual D1 EM solver evidence, System Carrier Review A, AWR EVM profile results, and physical antenna measurements remain open.

Run:

```bash
python -m tools.evidence_status \
  evidence/project_evidence_manifest.json \
  --output project_evidence_status.json
```
