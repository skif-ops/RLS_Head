# External execution matrix

`tools.external_execution_matrix` materializes and validates a job-pack for
every evidence item that is currently `READY_FOR_EXTERNAL_EXECUTION`.

It derives the queue from the authoritative evidence manifest, then creates
one directory per priority and records:

- job-pack template status;
- preflight status;
- preflight errors/warnings;
- direct dependency-unlock value;
- measurement-pack kind when applicable.

Example:

```bash
python -m tools.external_execution_matrix \
  --manifest evidence/project_evidence_manifest.json \
  --output-root outgoing/external_jobs \
  --output external_execution_matrix.json
```

The matrix and generated job-packs are workflow artifacts only. They do not
modify the authoritative evidence manifest and do not count as measured
evidence.
