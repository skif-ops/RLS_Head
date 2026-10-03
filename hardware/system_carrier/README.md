# EVT System Carrier

This directory is reserved for the real non-RF System Carrier CAD
package.

The repository currently contains Review A tooling and CI fixtures, not
an authoritative production schematic.

Expected real files:

```text
EVT_SYS_CARRIER.kicad_pro
EVT_SYS_CARRIER.kicad_sch
BOM_SYS_CARRIER_002.csv
PINMAP_SYS_001.csv
review_a/erc.json
review_a/manifest.json
```

The first real schematic gate is `CARRIER_REVIEW_A`.
Do not mark it PASS from the synthetic files under
`tests/fixtures/carrier_review_a/`.
