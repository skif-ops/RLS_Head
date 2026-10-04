# External evidence ingest

`tools.external_evidence_ingest` removes the manual SHA-256 assembly step
between a completed external measurement pack and
`tools.evidence_promote`.

It accepts an `EXTERNAL-EVIDENCE-BUNDLE-001` descriptor, verifies that the
referenced files remain inside the bundle root, rejects template
placeholders and fixture/synthetic markers, computes SHA-256 values, and
writes a candidate `MEASURED-EVIDENCE-CLAIM-001`.

It intentionally does **not**:

- perform the domain-specific pass/fail decision;
- update `evidence/project_evidence_manifest.json`;
- treat `CANDIDATE_READY` as measured evidence;
- authorize production or any downstream milestone.

Example bundle:

```json
{
  "schema": "EXTERNAL-EVIDENCE-BUNDLE-001",
  "kind": "hil_r2_bench",
  "item_id": "HIL_R2_BENCH_MEASURED",
  "evidence_level": "MEASURED_BENCH",
  "synthetic": false,
  "result": {
    "path": "result.json",
    "schema": "HIL-R2-BENCH-EVIDENCE-001"
  },
  "artifacts": [
    {
      "kind": "timing_capture",
      "path": "timing_capture.csv"
    }
  ]
}
```

Usage:

```bash
python -m tools.external_evidence_ingest \
  --bundle incoming/bundle.json \
  --bundle-root incoming \
  --output-result ingest_result.json \
  --output-claim evidence_claim.candidate.json
```

Required continuation after `CANDIDATE_READY`:

1. run the relevant domain validator;
2. inspect its result;
3. run `tools.evidence_promote` with the generated claim;
4. review the candidate project manifest;
5. only then merge an evidence-status change.
