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
7. Create/update the PCB and save as:
   `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`.
8. Copy the exact CI Altium import-package `manifest.json` used for this import to:
   `hardware/system_carrier/altium/equivalence/import_package_manifest.json`.
   From that same package, copy `evidence/kicad_netlist_baseline.csv` to:
   `hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv`.
9. Save/export the KiCad Import Wizard log as:
   `hardware/system_carrier/altium/equivalence/import_log.txt`.
10. Generate the provenance receipt, recording the actual Altium Designer and KiCad Importer versions:
    `python -m tools.altium_native_import_receipt --repository-root . --package-manifest hardware/system_carrier/altium/equivalence/import_package_manifest.json --altium-version "<ALTIUM_VERSION>" --importer-version "<IMPORTER_VERSION>" --output hardware/system_carrier/altium/equivalence/import_receipt.json`.
11. Require the command to return `PASS`. Do not delete or overwrite the retained KiCad source.

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
7. Export the Altium compile report and native BOM as `equivalence/bom_export.csv`. The BOM export must contain Designator(s) and MPN/Manufacturer Part Number columns.
8. Validate BOM equivalence:
   `python -m tools.altium_native_bom_validate --system-root hardware/system_carrier --bom-export hardware/system_carrier/altium/equivalence/bom_export.csv --output hardware/system_carrier/altium/equivalence/bom_validation_result.json`.
9. Validate native footprint patterns from the audit inventory:
   `python -m tools.altium_native_footprint_validate --system-root hardware/system_carrier --component-inventory hardware/system_carrier/altium/equivalence/component_inventory.csv --output hardware/system_carrier/altium/equivalence/footprint_report.json`.
10. Validate connector pinout equivalence from the native pad/net inventory:
    `python -m tools.altium_native_connector_validate --system-root hardware/system_carrier --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/connector_validation_result.json`.
11. Validate full native PCB connectivity against the retained KiCad baseline:
    `python -m tools.altium_native_netlist_validate --baseline-csv hardware/system_carrier/altium/equivalence/kicad_netlist_baseline.csv --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/netlist_validation_result.json`.
12. Run `scripts/EVT_SYS_CARRIER_Audit.PrjScr` → `ExportNativeHierarchy`. The read-only script compiles the focused Altium project, walks all numbered logical SchDoc child sheets and writes `equivalence/hierarchy_export.csv` from native port names/directions. Then validate the hierarchy together with native anchor connectivity:
    `python -m tools.altium_native_hierarchy_validate --system-root hardware/system_carrier --hierarchy-export hardware/system_carrier/altium/equivalence/hierarchy_export.csv --pad-net-inventory hardware/system_carrier/altium/equivalence/pad_net_inventory.csv --output hardware/system_carrier/altium/equivalence/hierarchy_validation_result.json`.
13. Complete `equivalence/no_mmwave_review.json` from `no_mmwave_review.template.json` against the exact native pre-routing `PcbDoc`, then validate the review binding:
    `python -m tools.altium_no_mmwave_review_validate --review-json hardware/system_carrier/altium/equivalence/no_mmwave_review.json --pcb hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc --component-inventory hardware/system_carrier/altium/equivalence/component_inventory.csv --net-inventory hardware/system_carrier/altium/equivalence/net_inventory.csv --output hardware/system_carrier/altium/equivalence/no_mmwave_review_result.json`.
14. Build the manifest hashes deterministically:
   `python -m tools.altium_equivalence_manifest --template hardware/system_carrier/altium/equivalence/manifest.template.json --repository-root . --output hardware/system_carrier/altium/equivalence/manifest.json`.
   This automatically hashes every required artifact. It promotes `native_pcb_audit`, `pinmap_equivalence`, `rules_equivalence` and `stackup_equivalence` from a PASS native audit, `bom_designator_mpn_equivalence` from a PASS BOM validator, `footprint_equivalence` from a PASS footprint validator, `connector_pinout_equivalence` from a PASS connector validator, and `netlist_equivalence` from a PASS connectivity validator. It does not auto-approve the remaining semantic equivalence checks.
15. Run `tools.altium_native_handoff_status` if needed: with all artifacts present but any semantic check still not `PASS`, the state must remain `WAITING_EQUIVALENCE_CHECKS`; `READY_TO_RUN_EQUIVALENCE_GATE` is reserved for a complete manifest whose mandatory checks are all `PASS`.
16. The manifest builder now machine-promotes all ten mandatory semantic checks when their dedicated validators/reviews PASS. If any check remains non-PASS, resolve its evidence before proceeding.
17. Run:
    `python -m tools.altium_equivalence_gate hardware/system_carrier/altium/equivalence/manifest.json --repository-root . --output altium_equivalence_result.json`.

Only `ALTIUM_EQUIVALENCE_GATE = PASS` changes layout authority to Altium.

## Still not production release

Equivalence PASS authorizes native placement/routing work only. Production remains blocked until final mechanical lock, fabricator stack/impedance binding, native Altium DRC, return-path/SI review, DFM and manufacturing release checks all pass.
