# System Carrier Altium production release

This directory is the evidence boundary between native Altium routing completion and manufacturing release.

`tools.altium_production_release_gate` is the only repository tool that may return production authority for EVT System Carrier Rev.A. The current canonical `native/EVT_SYS_CARRIER.SchDoc` and final routed `native/EVT_SYS_CARRIER.PcbDoc` are both required release artifacts. The SchDoc hash must still match the schematic hash recorded by the equivalence PASS; any electrical schematic change requires a fresh equivalence run. Every post-routing DRC/review/DFM/OutJob evidence file must carry `source_pcb` and `source_pcb_sha256` matching the exact final PcbDoc, so evidence from different board revisions cannot be mixed.

The gate requires SHA-256-bound native evidence for:

- Altium equivalence PASS with layout authority already authorized;
- native PCB DRC with zero blocking errors and zero unrouted nets;
- frozen board outline, mounting geometry and connector access;
- selected-fabricator stackup, copper, impedance, trace/clearance and via-rule binding;
- return-path/SI review with no open P0 findings;
- DFM closure with no open P0 items;
- complete required OutJob outputs generated from native Altium.

The gate does not infer or fabricate any of these reviews. After a gate PASS, the production transition re-hashes both the equivalence-approved canonical `SchDoc` and the final canonical `PcbDoc` immediately before synchronizing `AUTHORIZED`; any change in that race window aborts authority synchronization. Until every evidence file exists and passes, `production_authority` remains `NOT_AUTHORIZED`. After a gate PASS, the transition driver re-hashes the current final `PcbDoc` before synchronizing tracked production authority; if the board changes between gate evaluation and status synchronization, the transition fails closed and does not mark the current workspace production-authorized. On later CI/readiness runs, the current `PcbDoc` is compared again with the recorded production-release source hash; any subsequent edit keeps layout/routing authority but withdraws effective production authorization until the production release gate is rerun.

Start from `manifest.template.json`, populate SHA-256 hashes from the exact release evidence files, and run:

`python -m tools.altium_production_release_gate hardware/system_carrier/altium/release/manifest.json --repository-root . --output hardware/system_carrier/altium/release/production_release_result.json`

## Recommended release transition

After all post-routing evidence files are complete and PASS, use:

`python -m tools.altium_production_release_transition --repository-root . --output hardware/system_carrier/altium/release/production_transition_result.json`

The driver is fail-closed. It builds the release manifest when that is the only missing stage, evaluates release readiness, runs `ALTIUM_PRODUCTION_RELEASE_GATE`, writes the authoritative result and synchronizes `ALTIUM_NATIVE_STATUS_SYS_001.json`, `ALTIUM_STATUS_SYS_001.json` and `CAD_AUTHORITY_SYS_001.json` to `PRODUCTION_RELEASED` only after a real PASS.

## Release state machine

Use `python -m tools.altium_production_release_status --repository-root . --output hardware/system_carrier/altium/release/production_release_status.json` to identify the next unresolved release stage.

The normal state progression is:

`WAITING_EQUIVALENCE_PASS` → `WAITING_RELEASE_EVIDENCE` → (`INVALID_RELEASE_SOURCE_BINDING` if any review points at a different final PcbDoc) → `WAITING_RELEASE_REVIEWS` → `WAITING_RELEASE_MANIFEST` → `READY_TO_RUN_PRODUCTION_RELEASE_GATE`.

Build the final manifest hashes with:

`python -m tools.altium_production_release_manifest --template hardware/system_carrier/altium/release/manifest.template.json --repository-root . --output hardware/system_carrier/altium/release/manifest.json`

The six evidence `*.template.json` files plus `manifest.template.json` are intentionally PENDING/false or unhashed by default. Copy them to their non-template release filenames only when the corresponding native or review evidence is available.
