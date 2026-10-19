# System Carrier native Altium handoff

This runbook is the only remaining transition between the repository-controlled Altium preparation gates and native Altium layout authority.

## Preconditions

The repository must report:

- System Carrier Review A: PASS;
- KiCad ERC: 0 errors / 0 warnings;
- Altium routing readiness: `READY_FOR_NATIVE_IMPORT`;
- production authority: NOT_AUTHORIZED.

## Native import

1. Open Altium Designer.
2. Confirm the KiCad Importer extension is installed.
3. From File → Import Wizard, select **KiCad Design Files**.
4. Import `kicad_source/EVT_SYS_CARRIER.kicad_pro`, the root schematic and all seven child sheets from the CI Altium import package.
5. Include the supplied `SystemCarrier_Local.kicad_sym` and `SystemCarrier_Local.pretty`.
6. Save the native schematic as:
   `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc`.
8. Create/update the PCB and save as:
   `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`.
9. Validate that both native files are genuine non-trivial Altium CFB/OLE containers:
   `python -m tools.altium_native_file_preflight --schematic hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc --pcb hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc --output hardware/system_carrier/altium/equivalence/native_file_preflight.json`.
   Require `PASS`. The check validates the Microsoft Compound File Binary signature/header geometry and rejects extension-only placeholders or damaged containers; it does not replace electrical equivalence.
10. Copy the exact CI Altium import-package `manifest.json` used for this import to:
   `hardware/system_carrier/altium/equivalence/import_package_manifest.json`.
   From that same package, copy `evidence/kicad_netlist_baseline.csv` to:
   `hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv`.
11. Save/export the KiCad Import Wizard log as:
   `hardware/system_carrier/altium/equivalence/import_log.txt`.
12. Generate the provenance receipt, recording the actual Altium Designer and KiCad Importer versions:
    `python -m tools.altium_native_import_receipt --repository-root . --package-manifest hardware/system_carrier/altium/equivalence/import_package_manifest.json --altium-version "<ALTIUM_VERSION>" --importer-version "<IMPORTER_VERSION>" --output hardware/system_carrier/altium/equivalence/import_receipt.json`.
13. Require the command to return `PASS`. Do not delete or overwrite the retained KiCad source.

## Recommended orchestrated transition

After the native `SchDoc` / `PcbDoc`, import-package manifest and Import Wizard log are available, use the repository driver:

`python -m tools.altium_native_transition --repository-root . --altium-version "<ALTIUM_VERSION>" --importer-version "<IMPORTER_VERSION>" --output hardware/system_carrier/altium/equivalence/native_transition_result.json`

The command is intentionally re-runnable and fail-closed. Its first native-document action is the CFB/OLE file preflight; it then executes every repository-controlled validator that has enough input evidence, writes the corresponding result files, builds the equivalence manifest, runs the equivalence gate when all ten checks are PASS, and synchronizes the tracked Altium status JSON to `READY_FOR_ROUTING` only after a real gate PASS.

When an external Altium action is still required, it stops with an explicit state such as `WAITING_COMPILE_REPORT`, `WAITING_NATIVE_AUDIT_EXPORT`, `WAITING_BOM_EXPORT`, `WAITING_NETLIST_EXPORT`, `WAITING_HIERARCHY_EXPORT` or `WAITING_NO_MMWAVE_REVIEW`. It never creates native Altium documents and never auto-approves the human no-mmWave review.

The detailed manual sequence below remains the authoritative fallback and audit trail.

## Native project checks

Before routing:

1. Compile the project and resolve every compile error and warning relevant to the imported design.
2. Apply the four-layer stack and the rule/query contracts supplied under `hardware/system_carrier/altium/`.
3. Apply provisional placement rooms/coordinates only as EVT planning data; they are not a production mechanical freeze.
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
14. Complete `equivalence/no_mmwave_review.json` from `no_mmwave_review.template.json` against the exact native pre-routing `PcbDoc`, then validate the review binding:
    `python -m tools.altium_no_mmwave_review_validate --review-json hardware/system_carrier/altium/equivalence/no_mmwave_review.json --pcb hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc --component-inventory hardware/system_carrier/altium/equivalence/component_inventory.csv --net-inventory hardware/system_carrier/altium/equivalence/net_inventory.csv --output hardware/system_carrier/altium/equivalence/no_mmwave_review_result.json`.
15. Build the manifest hashes deterministically:
   `python -m tools.altium_equivalence_manifest --template hardware/system_carrier/altium/equivalence/manifest.template.json --repository-root . --output hardware/system_carrier/altium/equivalence/manifest.json`.
   This automatically hashes every required artifact. It promotes `native_pcb_audit`, `pinmap_equivalence`, `rules_equivalence` and `stackup_equivalence` from a PASS native audit, `bom_designator_mpn_equivalence` from a PASS BOM validator, `footprint_equivalence` from a PASS footprint validator, `connector_pinout_equivalence` from a PASS connector validator, and `netlist_equivalence` from a PASS connectivity validator. It does not auto-approve the remaining semantic equivalence checks.
16. Run `tools.altium_native_handoff_status` if needed: with all artifacts present but any semantic check still not `PASS`, the state must remain `WAITING_EQUIVALENCE_CHECKS`; `READY_TO_RUN_EQUIVALENCE_GATE` is reserved for a complete manifest whose mandatory checks are all `PASS`.
17. The manifest builder now machine-promotes all ten mandatory semantic checks when their dedicated validators/reviews PASS. If any check remains non-PASS, resolve its evidence before proceeding.
18. Run:
    `python -m tools.altium_equivalence_gate hardware/system_carrier/altium/equivalence/manifest.json --repository-root . --output hardware/system_carrier/altium/equivalence/altium_equivalence_result.json`.

Only `ALTIUM_EQUIVALENCE_GATE = PASS` changes layout authority to Altium.

## CI phase protection

GitHub CI uses `tools.altium_native_ci_gate` to distinguish the repository phases. Before native import it requires `PRE_IMPORT` with `READY_FOR_NATIVE_IMPORT`. Once both native documents are present, CI switches to `POST_EQUIVALENCE`: it re-runs the equivalence gate from committed evidence, requires the committed result to be reproducible, verifies tracked authority hashes/status synchronization, and requires routing readiness to be `READY_FOR_ROUTING`.

A partial native pair, stale authority hash, non-reproducible equivalence result or unsynchronized status fails CI.

## Still not production release

Equivalence PASS authorizes native placement/routing work only. Production remains blocked until final mechanical lock, fabricator stack/impedance binding, native Altium DRC, return-path/SI review, DFM and manufacturing release checks all pass.

## Production lifecycle CI

The same lifecycle CI gate also recognizes `POST_PRODUCTION`. In that phase CI re-runs the production-release gate from the committed release manifest, requires the committed result to be reproducible, verifies synchronized production authority/result hashes and keeps routing authority valid. A partial or stale production-status update fails CI.

## After routing authority

After `ALTIUM_EQUIVALENCE_GATE = PASS`, native placement/routing may begin. Production remains separately blocked. The post-routing manufacturing path is defined under `hardware/system_carrier/altium/release/` and enforced by `tools.altium_production_release_gate`.

The production gate requires final native Altium DRC/unrouted-net closure, mechanical freeze, selected-fabricator stack/impedance/process binding, return-path/SI review, DFM closure and complete required OutJob outputs. All post-routing release evidence is SHA-256-bound to the same final `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`; evidence from different PCB revisions cannot be combined. A routing-authority PASS alone can never authorize production.

