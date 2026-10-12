# EVM profile preflight inside external job-pack

When `tools.external_job_pack` selects `AWR_EVM_PROFILE_MEASURED`, the
generated job-pack includes:

- `measurement_pack/profile_metrics.csv`;
- `measurement_pack/run_manifests/` for TRACK/LR1/LR2/LRX manifests;
- a copied `evm_profile_gate_config.json`;
- `preflight_config.json`;
- a validator command matching the actual `tools.evm_profile_gate` CLI.

Canonical manifest names are `TRACK.json`, `LR1.json`, `LR2.json`, and
`LRX.json`.

A fresh template is `TEMPLATE_READY` and `READY_FOR_COLLECTION` with
warnings that metrics and profile manifests have not yet been collected.
Malformed manifests block the preflight.

This job-pack does not tune profile or waveform parameters and does not
classify any profile as operational before real measured evidence exists.
