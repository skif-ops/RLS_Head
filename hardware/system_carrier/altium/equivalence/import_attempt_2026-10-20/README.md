# Issue #216: native import attempt (20 October 2026)

Status: **BLOCKED; no routing or production authority**. This directory records an actual Altium Designer 26.10.1 Trial import attempt and its failures. It is not an import receipt or equivalence approval.

## Source and import

- GitHub Actions run `39398621807`, artifact `12253611280`, `system-carrier-altium-import` (original ZIP SHA-256 `48cf32cda3594b0115dba28e1650d64dd8eb966579564075c533c70ab71a4265`). The original ZIP is retained here.
- The downloaded ZIP omitted the manifest-listed hidden file `source_binding/.github/workflows/hil-r1.yml`. The exact current-main file was copied into the extracted package; its size (59,728 bytes) and SHA-256 (`0c384369adba5085fce69a5f406632d8a1e3dfe4af07409e570e2ac44d52f532`) matched the manifest. The repaired extraction then passed package verification (83/83 files) and current-source binding (51/51). The original ZIP alone does **not** pass the verifier.
- Altium's KiCad Design Files wizard imported `EVT_SYS_CARRIER.kicad_pro`, its root schematic and seven child sheets, the local symbol library, and the four supplied local footprints. The canonical root and child `.SchDoc` files and converted `.SchLib/.PcbLib` files are retained under `altium/native/`. `EVT_SYS_CARRIER.ImportAttempt.PrjPcb` is a separate project pointing to those files; the source-bound canonical `altium/EVT_SYS_CARRIER.PrjPcb` was not changed.
- The package has no `.kicad_pcb`. The wizard therefore produced no PCB. `altium/native/EVT_SYS_CARRIER.PcbDoc` was created and saved in Altium as an **empty** PCB. Its `Components6`, `Nets6`, `Pads6`, `Tracks6`, and `Vias6` data streams are all zero bytes. It is a genuine CFB/OLE Altium document but is not an imported or equivalent board.
- The structural native-file preflight passes. That check does not assess PCB contents or equivalence.

## Blocking Altium results

- The exported Altium Message List report contains **55 errors and 255 warnings**. Examples include electrical pin-type conflicts on `3V3`, duplicate net names, and cross-reference problems. The raw report and the importer's `.LOG` files are retained here; the latter include numerous unsupported KiCad schematic properties.
- A schematic-to-PCB comparison found **162 differences**, of which Altium offered automatic ECO actions for **76**. Validation of the proposed actions failed at least for missing footprints on `J6`, `J11`, `TP2`, and `U1`. The ECO was not executed.
- The KiCad baseline contains 92 components, 483 pins, and 215 nets. The current PCB contains none of them. No native BOM, pad/net inventory, audit, or hierarchy export can support equivalence from this board.
- The repository's mechanical datum, routing-stack, and power-routing **contract files** each pass their static gate (reports here). These contracts have **not** been applied or verified in the empty PCB.
- `native_ci_gate.json` is the expected `FAIL POST_EQUIVALENCE` result for this incomplete pair. `ALTIUM_EQUIVALENCE_GATE` was not run; `READY_FOR_ROUTING` was not granted. Production authority remains `NOT_AUTHORIZED`.

## Required continuation

1. Regenerate a complete import package that includes hidden source-binding files and all required KiCad footprints, or resolve the missing footprint sources explicitly in Altium.
2. Correct the native schematic/ERC and import a populated PCB with all expected components and nets. Preserve an immediate, provenance-bound import snapshot only after the genuine PCB exists.
3. Apply the locked EVT mechanical/routing/power contracts in Altium, then run native compile, audit exporters, BOM/netlist/hierarchy/no-mmWave checks and the equivalence gate. Set `READY_FOR_ROUTING` only after the gate passes; keep production authority `NOT_AUTHORIZED`.

This attempt deliberately does not write a `PASS` receipt, manifest, or authority status.
