# EVM reference campaign assembler

The campaign assembler combines validated per-run `EVM-RUN-MANIFEST-001` files into one `EVM-REFERENCE-CAMPAIGN-001` index.

Reference ladder:

- 50 m
- 100 m
- 150 m
- 200 m
- 250 m
- 300 m

A real campaign reaches `MEASURED_READY` only when all six distances have valid measured EVM manifests with a single profile ID and a single target ID.

A complete synthetic fixture campaign is only `TEST_READY`.

## CLI

```bash
python -m tools.evm_campaign \
  --manifest R050/manifest.json \
  --manifest R100/manifest.json \
  --manifest R150/manifest.json \
  --manifest R200/manifest.json \
  --manifest R250/manifest.json \
  --manifest R300/manifest.json \
  --output EVM_REFERENCE_CAMPAIGN.json
```

The assembler does not replace per-run hashes, truth metadata, or time validity. Those remain authoritative in the individual run manifests.
