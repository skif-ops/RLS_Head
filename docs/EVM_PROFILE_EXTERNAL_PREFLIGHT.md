# AWR EVM profile external preflight

`tools.evm_profile_external_preflight` checks structural readiness of the
measured TRACK/LR1/LR2/LRX campaign.

It validates the profile-metrics CSV schema and any available
`EVM-RUN-MANIFEST-001` files for real, config-locked, truth-valid,
time-aligned `MEASURED_EVM` provenance.

Before collection, missing metrics rows or missing profile manifests are
warnings. Invalid input files block the campaign.

The preflight does not tune waveform/profile parameters and does not classify
TRACK/LR profiles as operational; those decisions remain in
`tools.evm_profile_gate` after real measured data exist.
