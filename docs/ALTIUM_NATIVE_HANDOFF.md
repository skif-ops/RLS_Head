# System Carrier native Altium handoff

This runbook is the only remaining transition between the repository-controlled Altium preparation gates and native Altium layout authority.

## Preconditions

The repository must report:

- System Carrier Review A: PASS;
- KiCad ERC: 0 errors / 0 warnings;
- Altium routing readiness: `READY_FOR_NATIVE_IMPORT`;
- production authority: NOT_AUTHORIZED.

## Verify the downloaded CI import package

Before opening any import source in Altium Designer, verify the exact extracted `system-carrier-altium-import` artifact from CI:

`python -m tools.altium_import_package_verify --package-root "<EXTRACTED_PACKAGE_ROOT>" --output hardware/system_carrier/altium/equivalence/import_package_verification.json`

Require `PASS`. The package manifest uses package-root-relative paths, so verification is independent of the CI runner's temporary `build-cad` path. The verifier checks every manifest-listed file for path safety, size and SHA-256 and validates the package's `source_bindings` inventory. Keep the generated canonical `import_package_verification.json`; the later import receipt and equivalence gate require it and bind it to the exact copied package manifest. A package that fails verification must not be imported. The package Git SHA does not have to equal the current checkout after a squash/rebase: the import receipt instead performs a byte-for-byte current-source binding check against all bound generator inputs, contracts, footprints and audit scripts. If any bound source has changed since the artifact was produced, the receipt fails and the artifact must be regenerated before import.

## Native import

1. Open Altium Designer.
2. Confirm the KiCad Importer extension is installed.
3. From File → Import Wizard, select **KiCad Design Files**.
4. Import `kicad_source/EVT_SYS_CARRIER.kicad_pro`, the root schematic and all seven child sheets from the CI Altium import package.
5. Include the supplied `SystemCarrier_Local.kicad_sym` and `SystemCarrier_Local.pretty`.
6. Save the native schematic as:
   `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc`.
7. Create/update the PCB and save as:
   `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`.
8. Validate that both immediate Import Wizard outputs are genuine non-trivial Altium CFB/OLE containers:
   `python -m tools.altium_native_file_preflight --schematic hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc --pcb hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc --output hardware/system_carrier/altium/equivalence/import_native_file_preflight.json`.
   Require `PASS`. This import-time diagnostic rejects extension-only placeholders or damaged containers; it is not the final equivalence-bound preflight.
9. Copy the exact CI Altium import-package `manifest.json` used for this import to:
   `hardware/system_carrier/altium/equivalence/import_package_manifest.json`.
   From that same package, copy `evidence/kicad_netlist_baseline.csv` to:
   `hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv`.
10. Save/export the KiCad Import Wizard log as:
   `hardware/system_carrier/altium/equivalence/import_log.txt`.
11. Generate the provenance receipt immediately after import, recording the actual Altium Designer and KiCad Importer versions:
    `python -m tools.altium_native_import_receipt --repository-root . --package-manifest hardware/system_carrier/altium/equivalence/import_package_manifest.json --package-verification hardware/system_carrier/altium/equivalence/import_package_verification.json --import-preflight hardware/system_carrier/altium/equivalence/import_native_file_preflight.json --altium-version "<ALTIUM_VERSION>" --importer-version "<IMPORTER_VERSION>" --output hardware/system_carrier/altium/equivalence/import_receipt.json`.
12. Require the command to return `PASS`. A PASS receipt now also proves that the verified package's source-binding inventory still matched the current repository checkout byte-for-byte at import time. The receipt is the immutable `POST_IMPORT_NATIVE_SNAPSHOT`: its SchDoc/PcbDoc hashes describe the immediate import outputs and are not regenerated merely because approved pre-routing stack/rule preparation later changes the native files. Do not delete or overwrite the retained KiCad source.

## Recommended orchestrated transition

After the native `SchDoc` / `PcbDoc`, immutable import-time `import_native_file_preflight.json`, verified import-package evidence (`import_package_manifest.json` + `import_package_verification.json`) and Import Wizard log are available, use the repository driver:

`python -m tools.altium_native_transition --repository-root . --altium-version "<ALTIUM_VERSION>" --importer-version "<IMPORTER_VERSION>" --output hardware/system_carrier/altium/equivalence/native_transition_result.json`

The command is intentionally re-runnable and fail-closed. It first performs a read-only CFB/OLE check of the current native pair and then inspects the tracked native lifecycle. If a valid `POST_EQUIVALENCE` or `POST_PRODUCTION` state already exists, the normal rerun is idempotent: it returns the existing authority state without rewriting equivalence evidence or moving the pre-routing baseline. Only when a genuine equivalence/re-equivalence is needed does it begin regenerating transition-owned evidence, run the repository validators, build the manifest, execute the equivalence gate and synchronize tracked status.

For a deliberate full re-equivalence of an already valid lifecycle, pass `--force-recheck`. This explicitly permits regeneration of transition-owned equivalence evidence and should be used only when the electrical baseline or equivalence evidence is intentionally being replaced.

If `import_receipt.json` does not yet exist, the driver refuses to invent import provenance from a possibly modified native file. Without the immutable import-time preflight it stops at `WAITING_IMPORT_SNAPSHOT_CAPTURE`.

When an external Altium action is still required, it stops with an explicit state such as `WAITING_COMPILE_REPORT`, `WAITING_NATIVE_AUDIT_EXPORT`, `WAITING_BOM_EXPORT`, `WAITING_NETLIST_EXPORT`, `WAITING_HIERARCHY_EXPORT` or `WAITING_NO_MMWAVE_REVIEW`. It never creates native Altium documents and never auto-approves the human no-mmWave review.

The detailed manual sequence below remains the authoritative fallback and audit trail.

## DelphiScript API compatibility gate

Before relying on the native audit exporters, run the repository static compatibility check:

`python -m tools.altium_script_api_compatibility --contract hardware/system_carrier/altium/ALTIUM_SCRIPT_API_COMPAT_SYS_001.json --repository-root . --output hardware/system_carrier/altium/equivalence/script_api_compatibility.json`

Require `PASS`. The contract records the Altium PCB, schematic and Workspace Manager API symbols used by the two read-only exporters and rejects known mutation APIs. Symbols marked `DOCUMENTED` are mapped to the official Altium Developer references; symbols marked `RUNTIME_VERIFY` still require first-run validation on the target Altium Designer installation.

A static PASS does **not** replace runtime validation. On the target Altium Designer version, both `ExportNativeAudit` and `ExportNativeHierarchy` must compile/run without script error, generate all expected CSV files and leave native CAD objects unchanged. Their execution is recorded in the explicit runtime receipt described below; the repository validators then consume the same generated files.

## Native project checks

Before routing:

1. Compile the project and resolve every compile error and warning relevant to the imported design.
2. Apply the exact EVT-routing stack baseline from `ALTIUM_EVT_ROUTING_STACK_LOCK_SYS_001.json` together with `ALTIUM_EVT_STACKUP_SYS_002.csv`, `ALTIUM_IMPEDANCE_START_SYS_001.csv` and the rule/query contracts. Validate it with `python -m tools.altium_evt_routing_stack_gate hardware/system_carrier --output hardware/system_carrier/altium/equivalence/evt_routing_stack_gate.json` and require `PASS`. Apply the minimum power-neck geometry from `ALTIUM_EVT_POWER_ROUTING_LOCK_SYS_001.json` and validate it with `python -m tools.altium_evt_power_routing_gate hardware/system_carrier --output hardware/system_carrier/altium/equivalence/evt_power_routing_gate.json`; require `PASS`. These locks constrain EVT routing only; selected-fabricator stack/field-solver binding plus final copper-weight and thermal review remain mandatory before production release.
3. Apply the repository EVT mechanical routing datum exactly: the 100×80 mm board envelope, R3 corners, four M3 NPTH mounting holes and primary edge-connector anchors are `EVT_ROUTING_LOCKED`; remaining functional placement/rooms are EVT planning data. Validate with `python -m tools.altium_evt_mechanical_datum_gate hardware/system_carrier --output hardware/system_carrier/altium/equivalence/evt_mechanical_datum_gate.json`. This routing datum is not a production enclosure/STEP freeze.
4. Run the read-only script project:
   `scripts/EVT_SYS_CARRIER_Audit.PrjScr` → `ExportNativeAudit`.
5. Confirm the script generated all five CSV inventories (`component`, `net`, `rule`, `pad_net`, `layer_stack`) and copy them to:
   `hardware/system_carrier/altium/equivalence/`.
6. Run:
   `python -m tools.altium_native_audit_validate --system-root hardware/system_carrier --audit-dir hardware/system_carrier/altium/equivalence --output hardware/system_carrier/altium/equivalence/native_audit_result.json`.
7. Compile the native project with zero errors and zero warnings. Save/export the raw Altium compile/ERC report as `hardware/system_carrier/altium/equivalence/compile_report_raw.txt`, then create the provenance-bound wrapper:
   `python -m tools.altium_compile_evidence build --repository-root . --raw-report hardware/system_carrier/altium/equivalence/compile_report_raw.txt --errors 0 --warnings 0 --output hardware/system_carrier/altium/equivalence/compile_report.json`.
   Validate it with:
   `python -m tools.altium_compile_evidence validate --repository-root . --compile-report hardware/system_carrier/altium/equivalence/compile_report.json --output hardware/system_carrier/altium/equivalence/compile_validation_result.json`.
   The wrapper binds the zero-count claim to the exact raw report, `.PrjPcb` and native `.SchDoc` hashes.
8. Export the native BOM as `equivalence/bom_export.csv`, and an archival native netlist as `equivalence/netlist_export.csv`. The BOM export must contain Designator(s) and MPN/Manufacturer Part Number columns. Semantic connectivity equivalence is checked from the pad/net inventory against the retained KiCad baseline; `netlist_export.csv` is retained as native archival evidence.
9. Validate BOM equivalence:
   `python -m tools.altium_native_bom_validate --system-root hardware/system_carrier --bom-export hardware/system_carrier/altium/equivalence/bom_export.csv --output hardware/system_carrier/altium/equivalence/bom_validation_result.json`.
10. Validate native footprint patterns from the audit inventory:
   `python -m tools.altium_native_footprint_validate --system-root hardware/system_carrier --component-inventory hardware/system_carrier/altium/equivalence/component_inventory.csv --output hardware/system_carrier/altium/equivalence/footprint_report.json`.
11. Validate connector pinout equivalence from the native pad/net inventory:
    `python -m tools.altium_native_connector_validate --system-root hardware/system_carrier --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/connector_validation_result.json`.
12. Validate full native PCB connectivity against the retained KiCad baseline:
    `python -m tools.altium_native_netlist_validate --baseline-csv hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/netlist_validation_result.json`.
13. Run `scripts/EVT_SYS_CARRIER_Audit.PrjScr` → `ExportNativeHierarchy`. The read-only script compiles the focused Altium project, walks all numbered logical SchDoc child sheets and writes `equivalence/hierarchy_export.csv` from native port names/directions. Then validate the hierarchy together with native anchor connectivity:
    `python -m tools.altium_native_hierarchy_validate --system-root hardware/system_carrier --hierarchy-export hardware/system_carrier/altium/equivalence/hierarchy_export.csv --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/hierarchy_validation_result.json`.
14. After **both** read-only exporters have run successfully, prepare the receipt hashes deterministically:
    `python -m tools.altium_script_runtime_receipt_prepare --repository-root . --altium-version "<ALTIUM_VERSION>" --operator "<OPERATOR>" --output hardware/system_carrier/altium/equivalence/script_runtime_receipt.json`.
    Require `READY`. The prepare tool hashes the exact `EVT_SYS_CARRIER.PrjPcb`, pre-routing `SchDoc/PcbDoc`, `EVT_SYS_CARRIER_Audit.PrjScr`, both `.pas` scripts, `ALTIUM_SCRIPT_API_COMPAT_SYS_001.json`, and all six generated CSV outputs, but intentionally leaves the receipt and both procedure records `PENDING`. It never asserts runtime success. The template `script_runtime_receipt.template.json` remains the manual fallback/reference format.
15. After verifying the actual Altium Messages/runtime outcome, edit only the attestation fields: set top-level `status=PASS`, set both procedure records to `status=PASS`, and record `runtime_errors=0` / `runtime_warnings=0` for each procedure. Do not alter the generated hashes.
16. Validate the runtime receipt:
    `python -m tools.altium_script_runtime_receipt --receipt hardware/system_carrier/altium/equivalence/script_runtime_receipt.json --repository-root . --output hardware/system_carrier/altium/equivalence/script_runtime_result.json`.
    Require `PASS`. The validator refuses changed native documents, changed scripts/API contract, changed CSV outputs, non-zero runtime errors/warnings, placeholder operator/version fields, or a non-PASS procedure. The final equivalence authority gate reruns this validator and requires `script_runtime_result.json` to be exactly reproducible, so a forged PASS wrapper cannot substitute for the underlying runtime receipt.
17. Complete `equivalence/no_mmwave_review.json` from `no_mmwave_review.template.json` against the exact native pre-routing `PcbDoc`, then validate the review binding:
    `python -m tools.altium_no_mmwave_review_validate --review-json hardware/system_carrier/altium/equivalence/no_mmwave_review.json --pcb hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc --component-inventory hardware/system_carrier/altium/equivalence/component_inventory.csv --net-inventory hardware/system_carrier/altium/equivalence/net_inventory.csv --output hardware/system_carrier/altium/equivalence/no_mmwave_review_result.json`.
18. Build the manifest hashes deterministically:
   `python -m tools.altium_equivalence_manifest --template hardware/system_carrier/altium/equivalence/manifest.template.json --repository-root . --output hardware/system_carrier/altium/equivalence/manifest.json`.
   This automatically hashes every required artifact. It promotes `native_pcb_audit`, `pinmap_equivalence`, `rules_equivalence` and `stackup_equivalence` from a PASS native audit, `bom_designator_mpn_equivalence` from a PASS BOM validator, `footprint_equivalence` from a PASS footprint validator, `connector_pinout_equivalence` from a PASS connector validator, and `netlist_equivalence` from a PASS connectivity validator. It does not auto-approve the remaining semantic equivalence checks.
19. Run `tools.altium_native_handoff_status` if needed: with all artifacts present but any semantic check still not `PASS`, the state must remain `WAITING_EQUIVALENCE_CHECKS`; `READY_TO_RUN_EQUIVALENCE_GATE` is reserved for a complete manifest whose mandatory checks are all `PASS`.
20. The manifest builder now machine-promotes all ten mandatory semantic checks when their dedicated validators/reviews PASS. If any check remains non-PASS, resolve its evidence before proceeding.
21. Run:
    `python -m tools.altium_equivalence_gate hardware/system_carrier/altium/equivalence/manifest.json --repository-root . --output hardware/system_carrier/altium/equivalence/altium_equivalence_result.json`.

Only `ALTIUM_EQUIVALENCE_GATE = PASS` changes layout authority to Altium. After any subsequent CAD edit, `python -m tools.altium_authority_reconcile --repository-root . --output hardware/system_carrier/altium/equivalence/authority_reconcile.json` may be used as a dry-run guard. It never grants authority: `UNCHANGED` means all tracked authority surfaces agree and still match gate evidence; `REVOCATION_REQUIRED` means stale evidence or disagreement between `ALTIUM_NATIVE_STATUS`, `ALTIUM_STATUS.routing_readiness` and `CAD_AUTHORITY` must be explicitly revoked with `--apply` before further work. A missing `AUTHORIZED` flag is never filled in by reconciliation. Immediately before tracked `layout_authority=AUTHORIZED` is written, the transition requires the on-disk equivalence PASS-result JSON to still equal the gate result in memory, then re-hashes the canonical `SchDoc/PcbDoc` and requires them to still match the exact files approved by the gate, closing both result-file and native-file gate-to-status TOCTOU windows. That PASS binds the electrical `SchDoc` and the pre-routing `PcbDoc` snapshot. After layout authority is granted, `PcbDoc` is expected to evolve during placement/routing; lifecycle CI therefore keeps the approved SchDoc immutable while allowing the routed PCB to diverge from its pre-routing equivalence hash. A SchDoc change still requires a fresh equivalence PASS. After revoke-only reconciliation, the repository may enter the explicit safe `EQUIVALENCE_STALE` / `REEQUIVALENCE_REQUIRED` phase: native documents remain committed for rework, but routing and production authority are both false. This phase is CI-valid so the corrected schematic can be reviewed and committed before external Altium evidence is regenerated. Resume routing only after `altium_native_transition --force-recheck` completes a fresh equivalence PASS.

## CI phase protection

GitHub CI uses `tools.altium_native_ci_gate` to distinguish the repository phases. Before native import it requires `PRE_IMPORT` with `READY_FOR_NATIVE_IMPORT`. Once both native documents are present, CI switches to `POST_EQUIVALENCE`: it re-runs the equivalence gate from committed evidence, requires the committed result to be reproducible, verifies tracked authority hashes/status synchronization, and requires routing readiness to be `READY_FOR_ROUTING`.

A partial native pair, stale authority hash, non-reproducible equivalence result or unsynchronized status fails CI. Effective routing/production authority also requires consensus across `ALTIUM_NATIVE_STATUS_SYS_001.json`, `ALTIUM_STATUS_SYS_001.json` and `CAD_AUTHORITY_SYS_001.json`; no single tracked status file is authoritative by itself. The consensus gate additionally hashes and parses the canonical committed equivalence/production result files, so matching tracked hashes cannot authorize a missing, changed or non-PASS result.

## Still not production release

Equivalence PASS authorizes native placement/routing work only. The `EVT_ROUTING_LOCKED` board/mount/connector datum, EVT routing-stack lock and EVT power-routing lock constrain that layout but do not authorize manufacturing. Production remains blocked until the native-PcbDoc-bound final mechanical review (including enclosure/STEP fit and connector access), selected-fabricator stack/impedance binding with final field-solver/control evidence, native Altium DRC, return-path/SI review, DFM and manufacturing release checks all pass.

## Production lifecycle CI

The same lifecycle CI gate also recognizes `POST_PRODUCTION`. In that phase CI re-runs the production-release gate from the committed release manifest, requires the committed result to be reproducible, verifies synchronized production authority/result hashes and keeps routing authority valid. A partial or stale production-status update fails CI.

## After routing authority

After `ALTIUM_EQUIVALENCE_GATE = PASS`, native placement/routing may begin. Production remains separately blocked. The post-routing manufacturing path is defined under `hardware/system_carrier/altium/release/` and enforced by `tools.altium_production_release_gate`.

The production gate first requires the current canonical `SchDoc` to match the exact schematic hash approved by the equivalence gate; an electrical schematic change invalidates routing/production authority until equivalence is rerun. It then requires final native Altium DRC/unrouted-net closure, mechanical freeze, selected-fabricator stack/impedance/process binding, return-path/SI review, DFM closure and complete required OutJob outputs. All post-routing release evidence is SHA-256-bound to the same final `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`; evidence from different PCB revisions cannot be combined. `altium_production_release_status` validates this source binding before it can report `READY_TO_RUN_PRODUCTION_RELEASE_GATE`. A routing-authority PASS alone can never authorize production. After production gate PASS, the transition rechecks both canonical native document hashes before writing tracked production authority, closing the final SchDoc/PcbDoc TOCTOU window.

