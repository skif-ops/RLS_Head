# Project evidence promotion guard

Physical/measured project evidence must not be promoted by editing
`evidence/project_evidence_manifest.json` directly from a CI fixture.

The promotion guard accepts a hash-verified claim and derives the
project item status from the referenced result.

## Claim schema

```json
{
  "schema": "MEASURED-EVIDENCE-CLAIM-001",
  "item_id": "M300_MEASURED",
  "result": {
    "path": "evidence/M300_REPORT.json",
    "sha256": "<sha256>",
    "schema": "M300-REPORT-001"
  },
  "provenance": {
    "evidence_level": "MEASURED_EVM",
    "synthetic": false,
    "artifacts": [
      {
        "kind": "evm_run_manifest",
        "path": "runs/EVM-E3-A300/manifest.json",
        "sha256": "<sha256>"
      }
    ]
  }
}
```

## Guard properties

The guard rejects:

- an absent or non-explicit `synthetic: false` declaration;
- unsupported evidence levels;
- missing files;
- SHA-256 mismatches;
- `synthetic_fixture: true` anywhere in JSON provenance;
- checked-in CI files carrying `fixture_note`;
- result-schema mismatches;
- EVM manifests that do not validate as `MEASURED_READY`;
- M300 claims without a measured 300 m / 0.01 m² run;
- profile claims whose TRACK profile is not operational;
- CAD Review A claims without `CAD_REVIEW` evidence.

The checked-in file
`tests/fixtures/m300_measured_gate_pass.json` intentionally looks like
a measured result for logic testing but contains a fixture marker. The
promotion guard has a regression test that explicitly rejects it.

## Supported project items

Current promotion rules exist for:

- `REFERENCE_RANGE_MEASURED`
- `M300_MEASURED`
- `ANT_D1_EM_REAL`
- `ANT_D1_SIM_GATE_REAL`
- `HIL_R2_BENCH_MEASURED`
- `SYS_ERR_MEASURED`
- `CARRIER_REVIEW_A`
- `AWR_EVM_PROFILE_MEASURED`

`PHYSICAL_ANT_MEASUREMENT` is deliberately unsupported until a
physical antenna-measurement result schema is defined.

## Usage

```bash
python -m tools.evidence_promote \
  --manifest evidence/project_evidence_manifest.json \
  --claim claim.json \
  --repository-root . \
  --output-manifest project_evidence_manifest.promoted.json \
  --output-result evidence_promotion_result.json
```

The tool writes a candidate manifest. It does not silently modify the
authoritative manifest in place.

A successful promotion does not bypass the downstream milestone/gate
logic; it only changes the evidence item based on verified provenance.
