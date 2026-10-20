# EVT System Carrier — Altium primary CAD

This directory is the primary PCB CAD location for the System Carrier.

## Current state

The electrical capture is ERC-clean in the retained KiCad flow. PCB implementation now targets Altium Designer. The project shell `EVT_SYS_CARRIER.PrjPcb` is committed here so the native Altium import has a fixed repository destination.

The binary native documents `native/EVT_SYS_CARRIER.SchDoc` and `native/EVT_SYS_CARRIER.PcbDoc` are intentionally **not fabricated by scripts**. They must be created/saved by Altium Designer. They are Microsoft Compound File Binary (OLE/CFB) containers; repository `.gitattributes` marks native Altium libraries/documents as binary, and `tools.altium_native_file_preflight` rejects extension-only placeholders or invalid container headers.

## Import source

Use Altium Designer with the KiCad Importer extension:

1. File → Import Wizard.
2. Select **KiCad Design Files**.
3. Import the generated `EVT_SYS_CARRIER.kicad_pro` and all seven child `*.kicad_sch` sheets.
4. Include `SystemCarrier_Local.kicad_sym` and `SystemCarrier_Local.pretty`.
5. Output the native Altium project into this directory.
6. Save the imported schematic as `native/EVT_SYS_CARRIER.SchDoc`.
7. Create/transfer the PCB into `native/EVT_SYS_CARRIER.PcbDoc`.
8. Load the constraints from `ALTIUM_RULES_SYS_001.csv` and stack definition from `ALTIUM_LAYER_STACK_SYS_001.csv`.
9. Run `tools.altium_native_file_preflight` against the saved `SchDoc/PcbDoc`; require PASS.
10. Run the equivalence checks in `docs/CAD_POLICY_ALTIUM.md` before treating Altium as the implementation authority.

## Preservation rule

Do not delete any KiCad source, generated KiCad library or footprint used to establish the electrical baseline. KiCad is retained as an independent verification and recovery path.

## Native CI phase gate

The repository CI accepts three deliberate lifecycle states: `PRE_IMPORT` while no native `SchDoc/PcbDoc` pair exists, `POST_EQUIVALENCE` after both exist and equivalence has passed, and `POST_PRODUCTION` after the production-release gate passes. `tools/altium_native_ci_gate.py` revalidates the committed equivalence/release results and tracked SHA-bound authority state, preventing native CAD or manufacturing-release PRs from bypassing the gated lifecycle. `tools.altium_routing_readiness` independently requires three-file authority consensus across `ALTIUM_NATIVE_STATUS_SYS_001.json`, `ALTIUM_STATUS_SYS_001.json` and `CAD_AUTHORITY_SYS_001.json`, so a partial tracked-status write fails closed. It also verifies that the consensus gate-result hashes match the canonical committed PASS authority-result JSON files.

## Manufacturing

All future Gerber/ODB++/IPC-2581, NC drill, pick-and-place, assembly drawings, fabrication drawings and STEP outputs for this board are to be released from the native Altium project after the equivalence gate passes.

## Native transition driver

`tools/altium_native_transition.py` is the preferred repository-side driver after Altium Designer has created the real native documents. It is idempotent after authority is established: a normal rerun of a valid `POST_EQUIVALENCE` or `POST_PRODUCTION` lifecycle returns the existing state without rewriting equivalence evidence or rebasing the approved pre-routing PCB snapshot. During an incomplete first pass it still advances only through evidence that is present and stops at the first missing external Altium/human step.

Use `--force-recheck` only for a deliberate full re-equivalence; without that flag, an already-valid lifecycle is preserved rather than rebuilt.

If the import receipt has not yet been created, `import_native_file_preflight.json` must already exist from the immediate Import Wizard output. Otherwise the driver stops at `WAITING_IMPORT_SNAPSHOT_CAPTURE` instead of retrospectively declaring the current files to be the import snapshot.

The driver does not synthesize `.SchDoc` / `.PcbDoc`, does not replace native Altium compile/audit exports and does not auto-sign the no-mmWave human review. Native compile evidence is accepted only as `compile_report.json` generated/validated against the archived raw compile/ERC report and SHA-256-bound to the exact project and native schematic; a bare zero-count JSON is not sufficient.

## Native equivalence gate

After Altium Designer creates `native/EVT_SYS_CARRIER.SchDoc` and `native/EVT_SYS_CARRIER.PcbDoc`, copy the exact CI import-package `manifest.json` to `equivalence/import_package_manifest.json`, save/export the KiCad Import Wizard log as `equivalence/import_log.txt`, and generate `equivalence/import_receipt.json` with `tools.altium_native_import_receipt` immediately after import. That receipt is an immutable import-time snapshot. After applying the approved native stack/rule preparation, regenerate `equivalence/native_file_preflight.json` against the prepared files, run the read-only native audit, then build `equivalence/manifest.json` with `tools.altium_equivalence_manifest`. The manifest builder can machine-promote eight checks from validated native evidence: `native_pcb_audit`, `pinmap_equivalence`, `rules_equivalence`, `stackup_equivalence`, `bom_designator_mpn_equivalence`, `footprint_equivalence`, `connector_pinout_equivalence` and `netlist_equivalence`. Hierarchy/port semantics and the no-76–81 GHz design review remain separate. `tools.altium_native_handoff_status` reports `WAITING_EQUIVALENCE_CHECKS` while any mandatory manifest check is not `PASS`; it reports `READY_TO_RUN_EQUIVALENCE_GATE` only when evidence and semantic checks are complete. Routing/layout authority remains blocked until `tools.altium_equivalence_gate` itself returns `PASS`; the transition then rechecks the canonical native document hashes before synchronizing tracked layout authority, so a file change between gate PASS and status update cannot inherit authorization.

## EVT pre-layout baseline

The current placement baseline uses a **100 x 80 x 1.6 mm** rectangular board envelope with four M3 NPTH mounting holes. This is marked `EVT_PROVISIONAL`: it is sufficient to begin native Altium placement after the equivalence gate, but it is not a production mechanical freeze.

Authoritative pre-layout inputs:

- `../BOM_SYS_CARRIER_LAYOUT_004.csv` — one row per physical/PCB-only reference;
- `../FOOTPRINT_ASSIGNMENT_SYS_002.csv` — complete footprint assignment;
- `ALTIUM_BOARD_MECHANICAL_SYS_001.csv` — provisional outline, holes and keepouts;
- `ALTIUM_PLACEMENT_COORD_SYS_002.csv` — hard placement anchors and local placement directives;
- `ALTIUM_ROUTING_SEQUENCE_SYS_001.csv` — required routing order;
- `ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv` — numerical EVT defaults.

The pre-layout validator requires the generated schematic, layout BOM and footprint reference sets to match exactly and rejects duplicate designators.

## EVT provisional impedance start

For routing preparation, `ALTIUM_EVT_STACKUP_SYS_002.csv` defines a provisional 1.60 mm four-layer stack with a nominal 0.18 mm L1-to-L2 FR-4 dielectric. `ALTIUM_IMPEDANCE_START_SYS_001.csv` provides initial analytical geometries: GNSS RF 50 Ω at 0.36 mm top-layer width and Ethernet MDI 100 Ω at 0.26 mm width / 0.20 mm pair gap. These are routing-start values only; the selected fabricator must rebind them with its field solver before production release.

## EVT provisional power widths

`ALTIUM_POWER_WIDTH_SYS_001.csv` screens the high-current external-layer routes using a 35 µm copper / 10 °C rise IPC-2221 calculation. Routing-start minimum necks are 3.0 mm for VIN_RAW and VIN_PROTECTED, 1.5 mm for RADAR_12V, and 1.5 mm for the 3V3 trunk. Use pours/polygons where practical; final production widths remain subject to the selected fabricator copper stack and thermal review.

## Native rule scopes

`ALTIUM_DIFF_PAIRS_SYS_001.csv` defines the Ethernet MDI and CAN differential-pair objects/classes. `ALTIUM_RULE_QUERY_SYS_001.csv` contains the concrete Altium PCB query scopes to instantiate after native import, including `InNet(...)`, `InNetClass(...)`, and `InDifferentialPairClass(...)` expressions. These rules inherit the provisional impedance and power-width values and remain subject to native Altium DRC and final fabricator binding.

## Routing readiness gate

`ALTIUM_ROOMS_SYS_001.csv` defines seven provisional placement rooms aligned with the existing functional zones. `tools/altium_routing_readiness.py` consolidates the CAD-policy, pre-layout, placement, room, impedance, power-width and native-rule-scope gates. With the current repository state it is expected to report `READY_FOR_NATIVE_IMPORT`, not `READY_FOR_ROUTING`. Native routing authority is granted only after real Altium `SchDoc` / `PcbDoc` files exist and the Altium equivalence gate passes. After that PASS, the approved SchDoc remains the electrical baseline while PcbDoc is allowed to evolve through placement/routing; CI does not replay the pre-routing PCB hash gate against a legitimately routed board.
