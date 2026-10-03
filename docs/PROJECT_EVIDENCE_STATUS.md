# Project evidence status

The authoritative status manifest is:

`evidence/project_evidence_manifest.json`

Its purpose is to prevent CI fixtures, analytical models, or cross-build success from being confused with physical measured evidence.

Current rules include:

- synthetic artifacts cannot carry a measured evidence level;
- PASS must identify a non-empty evidence level;
- milestone PASS requires all required evidence items to PASS;
- measured-evidence items remain explicitly OPEN until real measurements exist.

The current manifest intentionally keeps the following physical evidence open:

- reference-range ladder;
- M300;
- HIL-R2 bench timing;
- measured SYS-ERR;
- actual D1 EM solver evidence;
- System Carrier Review A;
- AWR EVM profile measurements;
- physical antenna measurement.

CI fixture success does not close these items.

## CLI

```bash
python -m tools.evidence_status \
  evidence/project_evidence_manifest.json \
  --output project_evidence_status.json
```

Output schema: `PROJECT-EVIDENCE-STATUS-001`.
