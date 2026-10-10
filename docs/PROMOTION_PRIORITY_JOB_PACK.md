# Priority job-pack from promotion pipeline

The evidence promotion pipeline can optionally materialize the next external
evidence job-pack after a candidate promotion.

Example:

```bash
python -m tools.evidence_promotion_pipeline \
  --manifest evidence/project_evidence_manifest.json \
  --bundle incoming/bundle.json \
  --bundle-root incoming \
  --output-result promotion_pipeline_result.json \
  --output-manifest project_evidence_manifest.candidate.json \
  --output-job-pack-dir outgoing/next_job
```

Use `--job-pack-priority N` to select another READY queue entry.

The job-pack is generated only after ingest and promotion guards succeed.
It is validated immediately as a template pack and remains non-evidence
until real external measurements are collected and passed back through the
domain validator and promotion pipeline.
