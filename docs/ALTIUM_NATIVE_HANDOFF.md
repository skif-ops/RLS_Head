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
5. Copy the generated CSV inventories to:
   `hardware/system_carrier/altium/equivalence/`.
6. Run:
   `python -m tools.altium_native_audit_validate --system-root hardware/system_carrier --audit-dir hardware/system_carrier/altium/equivalence --output hardware/system_carrier/altium/equivalence/native_audit_result.json`.
7. Export the Altium compile report, BOM, netlist/pin evidence and footprint report required by the equivalence manifest.
8. Build the manifest hashes deterministically:
   `python -m tools.altium_equivalence_manifest --template hardware/system_carrier/altium/equivalence/manifest.template.json --repository-root . --output hardware/system_carrier/altium/equivalence/manifest.json`.
   This automatically hashes every required artifact and marks `native_pcb_audit=PASS` only when the validated native audit result is PASS. It does not auto-approve the remaining semantic equivalence checks.
9. Resolve the remaining semantic checks in `equivalence/manifest.json` from the native evidence.
10. Run:
    `python -m tools.altium_equivalence_gate hardware/system_carrier/altium/equivalence/manifest.json --repository-root . --output altium_equivalence_result.json`.

Only `ALTIUM_EQUIVALENCE_GATE = PASS` changes layout authority to Altium.

## Still not production release

Equivalence PASS authorizes native placement/routing work only. Production remains blocked until final mechanical lock, fabricator stack/impedance binding, native Altium DRC, return-path/SI review, DFM and manufacturing release checks all pass.
