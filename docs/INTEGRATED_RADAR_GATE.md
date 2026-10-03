# INTEGRATED-RADAR-GATE-001

This gate controls only the transition to an **integrated sensing
measurement prototype**.

It does not authorize production.

Required authoritative project-evidence items:

- `AWR_EVM_PROFILE_MEASURED`
- `PHYSICAL_ANT_MEASUREMENT`
- `SYS_ERR_MEASURED`

All three must be non-synthetic.

Decision:

- any FAIL -> FAIL;
- any OPEN/HOLD -> HOLD;
- any CONDITIONAL with no failure -> CONDITIONAL;
- all PASS -> PASS.

PASS authorizes only:

- integrated sensing prototype design;
- integrated RF/antenna correlation measurement;
- integrated timing / TargetState verification.

Explicitly not authorized:

- production release;
- production antenna freeze;
- production waveform freeze;
- vehicle-control or guidance functionality.

Run:

```bash
python -m tools.integrated_radar_gate \
  evidence/project_evidence_manifest.json \
  --output integrated_radar_gate.json
```

At the current project baseline this gate is expected to remain HOLD
because its required physical/measured evidence items are still open.
