# Native Altium audit script

This read-only DelphiScript package is used after the KiCad-to-Altium import and before the Altium equivalence gate.

Altium Designer's scripting system supports DelphiScript projects (`.PrjScr`) with `.pas` units, and the PCB API exposes the current board through `PCBServer.GetCurrentPCBBoard` plus board iterators for components, nets and rules. The script intentionally uses only read operations.

## Run

1. Open the native `EVT_SYS_CARRIER.PcbDoc` in Altium Designer.
2. Open `EVT_SYS_CARRIER_Audit.PrjScr`.
3. Run procedure `ExportNativeAudit`.
4. The script creates an `equivalence` directory beside the PcbDoc and writes:
   - `component_inventory.csv`;
   - `net_inventory.csv`;
   - `rule_inventory.csv`;
   - `pad_net_inventory.csv`;
   - `layer_stack_inventory.csv`.
5. Commit/copy those reports into the repository equivalence evidence directory and run `python -m tools.altium_native_audit_validate`.

The exporter does not create, delete or modify PCB objects.

## Purpose

The audit is an independent machine-readable cross-check of the imported native PcbDoc. It verifies component and P0/P1 net presence, native rule name/family/scope/enabled state, MCU physical-pin-to-net assignments, direct `SYMBOL_PIN_CONTRACT` connections and copper layer order. `altium_native_audit_validate` records SHA-256 hashes of all five raw inventories: components, nets, rules, pad-to-net connectivity and copper layer stack. The equivalence gate requires those same raw files in the manifest and verifies that their current hashes match the hashes embedded in `native_audit_result.json`. It supplements, but does not replace, the full Altium equivalence manifest and native compile/DRC evidence.
