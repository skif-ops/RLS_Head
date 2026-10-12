# Generated KiCad System Carrier scaffold

The authoritative System Carrier schematic starts as a reproducible generated
hierarchical KiCad project.

Generation:

```bash
python -m tools.generate_system_carrier_schematic \
  --output-dir build-cad/system_carrier
```

The generator produces:

- `EVT_SYS_CARRIER.kicad_sch`
- `EVT_SYS_CARRIER.kicad_pro`
- seven child schematics matching the frozen schematic contract
- `cad_scaffold_manifest.json`

Current capture stage:

- POWER_INPUT: first component/passive scaffold
- MCU_CORE: STM32H753 symbol when available plus core support passives
- remaining sheets: valid child sheets with capture notes

Custom ICs not yet represented by validated KiCad symbols are explicitly
recorded as `SYMBOL_PENDING` placeholders. The scaffold is therefore
`CAD_SCAFFOLD_READY`, not `CARRIER_REVIEW_A=PASS`.

CI installs KiCad and `kicad-sch-api==0.5.6`, regenerates the project,
parses every sheet, runs real `kicad-cli sch erc`, and uploads the generated
schematics plus ERC JSON as a CAD artifact.

No mmWave routing is generated on the carrier.
