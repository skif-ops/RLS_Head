# Evidence promotion pipeline

`tools.evidence_promotion_pipeline` connects the already separated evidence
workflow stages into one reproducible command:

`external bundle -> ingest -> evidence_promote -> candidate manifest -> readiness`

The pipeline preserves the existing safety boundary:

- the authoritative `evidence/project_evidence_manifest.json` is never
  modified in place;
- a failed ingest or promotion produces no candidate manifest;
- hashes and non-synthetic provenance are still checked by the existing
  guards;
- item-specific promotion logic remains authoritative;
- readiness is recalculated only against the returned candidate manifest.

Usage:

```bash
python -m tools.evidence_promotion_pipeline \
  --manifest evidence/project_evidence_manifest.json \
  --bundle incoming/bundle.json \
  --bundle-root incoming \
  --output-result promotion_pipeline_result.json \
  --output-manifest project_evidence_manifest.candidate.json
```

`CANDIDATE_READY` means the candidate manifest was derived reproducibly.
It does not merge the candidate, authorize production, freeze design, or
enable vehicle guidance/control. Review and repository merge remain explicit
steps.
