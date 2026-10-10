# Project execution snapshot

`tools.project_execution_snapshot` provides one read-only command for the
current evidence/execution state.

It derives:

`authoritative evidence -> readiness -> execution queue -> execution recipes`

Optionally it also materializes the selected priority external job-pack.

Example:

```bash
python -m tools.project_execution_snapshot \
  --manifest evidence/project_evidence_manifest.json \
  --output project_execution_snapshot.json \
  --output-job-pack-dir outgoing/next_job
```

The snapshot does not edit the authoritative evidence manifest. Generated
queues, recipes, and job-packs are workflow artifacts only and never count as
measured evidence.
