# External execution queue

`tools.external_execution_queue` converts a validated
`MEASUREMENT-READINESS-001` report into a deterministic queue of
external evidence actions.

The queue is deliberately narrow:

- it includes only `READY_FOR_EXTERNAL_EXECUTION` items;
- it prefers items that directly unblock more currently dependency-blocked
  evidence;
- ties are sorted by `item_id`;
- it never changes the authoritative evidence manifest;
- it never treats templates, synthetic fixtures, or generated queue entries
  as measured evidence.

Example:

```bash
python -m tools.measurement_readiness \
  evidence/project_evidence_manifest.json \
  --output measurement_readiness.json

python -m tools.external_execution_queue \
  measurement_readiness.json \
  --output external_execution_queue.json
```

The output schema is `EXTERNAL-EXECUTION-QUEUE-001`.

A queue entry contains the evidence item, its next action, measurement-pack
kind when applicable, whether measured evidence is required, and the number
of currently blocked items that it directly unlocks.

This is an evidence-workflow aid only. It does not authorize production,
freeze antenna or waveform design, or enable vehicle guidance/control.
