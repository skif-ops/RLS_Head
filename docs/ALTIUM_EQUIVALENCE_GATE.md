# System Carrier Altium equivalence gate

The System Carrier electrical Review A is closed with a real CAD evidence package and zero ERC violations. The next mandatory gate is the native Altium equivalence review.

## Purpose

The gate prevents a KiCad-to-Altium translation error from becoming PCB layout authority. Altium Designer is the primary PCB CAD, but native `SchDoc` / `PcbDoc` files are authoritative only after equivalence is demonstrated.

## Required native evidence

The gate consumes:

- `hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb`;
- `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc`;
- `hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc`;
- Altium compile report with zero errors and zero warnings;
- BOM export;
- netlist/pin export;
- footprint assignment report;
- completed equivalence manifest.

Use `hardware/system_carrier/altium/equivalence/manifest.template.json` as the starting manifest.

## Mandatory checks

All must be PASS:

1. BOM designator/MPN equivalence.
2. STM32 pinmap equivalence.
3. Connector pinout equivalence.
4. Netlist equivalence.
5. Footprint equivalence.
6. Hierarchy/port equivalence.
7. Altium PCB-rule equivalence.
8. Four-layer stack equivalence.
9. No 76–81 GHz RF routing or antenna on the System Carrier.
10. Native Altium compile: zero errors and zero warnings.

## Gate command

```bash
python -m tools.altium_equivalence_gate \
  hardware/system_carrier/altium/equivalence/manifest.json \
  --repository-root . \
  --output altium_equivalence_result.json
```

`PASS` changes PCB layout authority to Altium. It still does **not** authorize production; native PCB DRC, return-path/SI review, DFM and manufacturing-release gates remain separate.

KiCad files are retained permanently for independent comparison and recovery.
