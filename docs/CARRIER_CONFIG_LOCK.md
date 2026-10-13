# System Carrier configuration lock

`config_lock` provides a deterministic identity for one frozen carrier
configuration.

The module stores only:

- configuration version;
- configuration byte length;
- IEEE CRC-32;
- state: `EMPTY -> STAGED -> LOCKED`.

The configuration payload remains owned by the caller; no heap or dynamic
allocation is used.

Once committed, a configuration cannot be replaced until an explicit reset.
The locked CRC can be copied into `measurement_session`, radar metadata and
evidence-export records so all artifacts from one run are tied to the same
configuration identity.

This module has no target-state, guidance or actuation semantics.
