# System Carrier Altium production release

This directory is the evidence boundary between native Altium routing completion and manufacturing release.

`tools.altium_production_release_gate` is the only repository tool that may return production authority for EVT System Carrier Rev.A. The gate requires SHA-256-bound native evidence for:

- Altium equivalence PASS with layout authority already authorized;
- native PCB DRC with zero blocking errors and zero unrouted nets;
- frozen board outline, mounting geometry and connector access;
- selected-fabricator stackup, copper, impedance, trace/clearance and via-rule binding;
- return-path/SI review with no open P0 findings;
- DFM closure with no open P0 items;
- complete required OutJob outputs generated from native Altium.

The gate does not infer or fabricate any of these reviews. Until every evidence file exists and passes, `production_authority` remains `NOT_AUTHORIZED`.

Start from `manifest.template.json`, populate SHA-256 hashes from the exact release evidence files, and run:

`python -m tools.altium_production_release_gate hardware/system_carrier/altium/release/manifest.json --repository-root . --output hardware/system_carrier/altium/release/production_release_result.json`
