# External execution recipes

`tools.external_execution_recipe` converts the current
`EXTERNAL-EXECUTION-QUEUE-001` into explicit evidence-execution recipes.

Each recipe identifies:

- the evidence item and its queue priority;
- the files or manifests to collect;
- the existing domain validator command;
- the expected result schema;
- the required continuation through ingest and candidate promotion.

The report does not generate or substitute physical measurements and does
not alter the authoritative evidence manifest.

Usage:

```bash
python -m tools.external_execution_recipe \
  external_execution_queue.json \
  --output external_execution_recipes.json
```

After a real measurement is complete, use the resulting domain result and
source artifacts to build an `EXTERNAL-EVIDENCE-BUNDLE-001`, then pass it
through `tools.external_evidence_ingest` and
`tools.evidence_promotion_pipeline`.
