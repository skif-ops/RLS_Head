# System Carrier Altium equivalence gate

The System Carrier electrical Review A is closed with a real CAD evidence package and zero ERC violations. The next mandatory gate is the native Altium equivalence review.

## Purpose

The gate prevents a KiCad-to-Altium translation error from becoming PCB layout authority. Altium Designer is the primary PCB CAD, but native `SchDoc` / `PcbDoc` files are authoritative only after equivalence is demonstrated.

## Required native evidence

The gate consumes:

- `hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb`;
- `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc`;
- `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`;
- SHA-bound `equivalence/native_file_preflight.json`, proving both native documents have valid Microsoft Compound File Binary container headers;
- exact CI import-package manifest copied to `equivalence/import_package_manifest.json`;
- immutable import-time provenance receipt `equivalence/import_receipt.json` (`POST_IMPORT_NATIVE_SNAPSHOT`); its SchDoc/PcbDoc hashes describe the immediate Import Wizard outputs and may differ from the later prepared pre-routing snapshot;
- saved/exported KiCad Import Wizard log `equivalence/import_log.txt`;
- final `equivalence/native_file_preflight.json` whose SchDoc/PcbDoc hashes must match the actual prepared pre-routing files consumed by this gate;
- raw Altium compile/ERC report plus `compile_report.json` with zero errors/warnings, SHA-256-bound to that raw report, the exact `.PrjPcb` and native `.SchDoc`;
- BOM export plus `equivalence/bom_validation_result.json`;
- connector validation result derived from native pad/net inventory;
- retained KiCad connectivity baseline copied from the exact CI import package plus native netlist validation result;
- schematic netlist/port export for the remaining hierarchy check;
- footprint assignment result generated from the native component inventory;
- read-only native PCB audit inventories (components, nets, rules, pad-to-net connectivity and copper layer stack), each SHA-256-bound in the equivalence manifest;
- validated native audit result `equivalence/native_audit_result.json`, containing SHA-256 hashes of all five raw inventory CSV inputs;
- explicit Altium Designer runtime receipt `equivalence/script_runtime_receipt.json` plus validated `equivalence/script_runtime_result.json`, SHA-256-bound to the exact pre-routing native documents, both read-only audit scripts, `ALTIUM_SCRIPT_API_COMPAT_SYS_001.json` and all six generated audit/hierarchy CSV outputs; the authority gate independently reruns the runtime-receipt validator and requires the committed result to be exactly reproducible;
- completed equivalence manifest.

Use `hardware/system_carrier/altium/equivalence/manifest.template.json` as the starting manifest. The gate independently re-runs the CFB/OLE preflight against the exact committed `SchDoc/PcbDoc`; a forged PASS JSON cannot substitute for valid native containers.

The authority gate also requires the core project, schematic and PCB artifacts at their canonical repository paths. Alternate `.PrjPcb`, `.SchDoc` or `.PcbDoc` paths are rejected even when their hashes and extensions are otherwise valid.

## Mandatory checks

All must be PASS:

1. BOM designator/MPN equivalence, machine-validated against `BOM_SYS_CARRIER_LAYOUT_004.csv`.
2. STM32 pinmap equivalence.
3. Connector pinout equivalence, machine-validated through the logical-to-native connector map and native pad/net inventory.
4. Full PCB connectivity equivalence, machine-validated as physical endpoint partitions against the retained KiCad CI baseline.
5. Footprint equivalence, machine-validated from native `IPCB_Component.Pattern` inventory against `FOOTPRINT_ASSIGNMENT_SYS_002.csv`.
6. Hierarchy/port equivalence from compiled native hierarchy export, with each contract anchor ref/pin independently checked against native pad-to-net evidence.
7. Altium PCB-rule equivalence: all 10 instantiated rule-query rules must have the required family, scope and enabled state; the 24-row layout constraint contract remains the broader design-policy source.
8. Four-layer stack equivalence.
9. PcbDoc-bound human review confirming no 76–81 GHz components, nets, routing or antenna on the System Carrier.
10. Native Altium compile: zero errors and zero warnings with validated raw-report/project/schematic provenance.
11. Native PCB audit: component, P0/P1 net, required rule family, MCU/direct-symbol pin-to-net and four-layer copper-stack inventory PASS.

## Gate command

```bash
python -m tools.altium_equivalence_gate \
  hardware/system_carrier/altium/equivalence/manifest.json \
  --repository-root . \
  --output altium_equivalence_result.json
```

`PASS` changes PCB layout authority to Altium. It still does **not** authorize production; native PCB DRC, return-path/SI review, DFM and manufacturing-release gates remain separate.

KiCad files are retained permanently for independent comparison and recovery.
