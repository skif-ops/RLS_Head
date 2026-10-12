# System Carrier Review A

This gate covers the non-RF System Carrier schematic only.

It does not authorize production, an integrated radar RF PCB, vehicle
guidance, or actuator/control functions.

## Real artifact set

The real Review A package is expected to bind the generated KiCad schematic
to the authoritative Rev.A electrical inputs:

```text
hardware/system_carrier/
├── BOM_SYS_CARRIER_003.csv
├── PINMAP_SYS_001.csv
├── FOOTPRINT_PLAN_SYS_001.csv
├── PACKAGE_CONTRACT_SYS_001.csv
└── review_a/
    ├── EVT_SYS_CARRIER.kicad_sch
    ├── erc.json
    └── manifest.json
```

The generated CAD artifact may be used as the source of the real schematic
and ERC package, but the Review A manifest must contain hashes of the exact
artifacts being reviewed.

## KiCad ERC

For the pinned KiCad 9 toolchain:

```bash
kicad-cli sch erc \
  --format json \
  --severity-all \
  --output hardware/system_carrier/review_a/erc.json \
  hardware/system_carrier/review_a/EVT_SYS_CARRIER.kicad_sch
```

The Review A policy remains strict:

- ERC errors allowed: 0;
- ERC warnings allowed: 0.

The validator parses `sheets[].violations[]` itself; a successful
`kicad-cli` process is not equivalent to Review A PASS.

## Review A P0 audits

All must be explicitly PASS in the real manifest:

- power;
- clock;
- reset/boot;
- timing capture;
- IMU;
- Ethernet;
- CAN FD.

## Critical timing pinmap

| Signal | MCU pin | Timer capture |
|---|---|---|
| GNSS_PPS | PA0 | TIM2_CH1 |
| RADAR_REF | PB10 | TIM2_CH3 |
| IMU_DRDY | PB11 | TIM2_CH4 |

## Required Rev.A BOM anchors

The Review A validator checks the currently selected architecture:

- STM32H753IIT6;
- ICM-42688-P;
- LAN8742Ai-CZ-TR;
- TCAN3404DRBRQ1;
- TPS62132RGTR;
- TPS259470ARPWR;
- NEO-M9N-00B;
- SI-60182-F.

The obsolete TPS62130 and provisional P01-0006-01 are not valid Rev.A
anchors.

## Validator

```bash
python -m tools.carrier_review_a \
  hardware/system_carrier/review_a/manifest.json \
  --repository-root . \
  --output carrier_review_a_result.json
```

Result statuses:

- `TEST_READY` — synthetic CI fixture only;
- `PASS` — real CAD review evidence with `CAD_REVIEW` evidence level;
- `HOLD` — technically clean artifacts but insufficient evidence level;
- `FAIL` — ERC/audit/pinmap/BOM failure;
- `INVALID` — schema/hash/path/parse failure.

A synthetic fixture can never close the real `CARRIER_REVIEW_A` item.
