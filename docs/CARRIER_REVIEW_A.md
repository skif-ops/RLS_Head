# System Carrier Review A

This gate covers the non-RF System Carrier schematic only.

It does not authorize production or an integrated radar PCB.

## Real artifact set

The real Review A package is expected to contain:

```text
hardware/system_carrier/
├── EVT_SYS_CARRIER.kicad_pro
├── EVT_SYS_CARRIER.kicad_sch
├── BOM_SYS_CARRIER_002.csv
├── PINMAP_SYS_001.csv
└── review_a/
    ├── erc.json
    └── manifest.json
```

Until those real CAD artifacts exist, project evidence must keep
`CARRIER_REVIEW_A` open.

## KiCad ERC

For the pinned KiCad toolchain, generate structured ERC output:

```bash
kicad-cli sch erc \
  --format json \
  --severity-all \
  --output hardware/system_carrier/review_a/erc.json \
  hardware/system_carrier/EVT_SYS_CARRIER.kicad_sch
```

For a strict no-violation shell gate, `--exit-code-violations` can be
added. The project validator still parses the JSON itself and treats
`sheets[].violations[]` as authoritative structured findings.

## Review A P0 audits

All of the following must be explicitly PASS in the real manifest:

- power;
- clock;
- reset/boot;
- timing capture;
- IMU;
- Ethernet;
- CAN FD.

## Critical timing pinmap

The Review A validator requires:

| Signal | MCU pin | Timer capture |
|---|---|---|
| GNSS_PPS | PA0 | TIM2_CH1 |
| RADAR_REF | PB10 | TIM2_CH3 |
| IMU_DRDY | PB11 | TIM2_CH4 |

## Required electrical BOM anchors

The current Review A contract checks for these already-selected
System Carrier parts:

- STM32H753IIT6;
- ICM-42688-P;
- LAN8742Ai-CZ-TR;
- TCAN3404DRBRQ1;
- TPS62130ARGTR;
- TPS259470ARPWR.

This is an electrical baseline check, not a complete manufacturing BOM
freeze.

## Validator

```bash
python -m tools.carrier_review_a \
  hardware/system_carrier/review_a/manifest.json \
  --repository-root . \
  --output carrier_review_a_result.json
```

Result statuses:

- `TEST_READY` — synthetic CI fixture only;
- `PASS` — real CAD review evidence with evidence level `CAD_REVIEW`;
- `HOLD` — technically clean artifacts but insufficient evidence level;
- `FAIL` — ERC/audit/pinmap/BOM gate failure;
- `INVALID` — schema, hash, path, or parse failure.

A synthetic fixture can never produce real Review A PASS.
