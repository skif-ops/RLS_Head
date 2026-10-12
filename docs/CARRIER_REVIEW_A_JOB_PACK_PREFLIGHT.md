# Carrier Review A preflight inside external job-pack

When `tools.external_job_pack` selects `CARRIER_REVIEW_A`, the generated
job-pack contains a self-contained non-RF CAD Review A package:

- authoritative pinmap copied from `hardware/system_carrier/PINMAP_SYS_001.csv`;
- authoritative BOM copied from `hardware/system_carrier/BOM_SYS_CARRIER_002.csv`;
- `carrier_package/carrier_review_a_manifest.json`;
- output slots for KiCad schematic and ERC JSON;
- all Review A audit slots initialized to `PENDING`;
- `preflight_config.json` and a resolved validator command.

A fresh package should be `TEMPLATE_READY` and
`READY_FOR_CAD_REVIEW_EXECUTION`, with warnings for the not-yet-generated
schematic/ERC files and pending audits.

This state is not Review A PASS and does not authorize fabrication.
