# SYS-ERR external preflight

`tools.sys_err_external_preflight` preserves the explicit dependency between
measured HIL-R2 timing evidence and `SYS_ERR_MEASURED`.

States:

- `BLOCKED` — malformed manifest/config/cells or non-PASS timing evidence;
- `WAITING_FOR_HIL_R2` — package structure is valid but real HIL-R2 PASS
  evidence is not present yet;
- `READY_FOR_COLLECTION` — HIL-R2 PASS is present and the SYS-ERR cells
  package is structurally ready to complete.

The preflight never computes or asserts `SYS-ERR-GATE-001` PASS. Final
uncertainty calculation remains in `tools.sys_err_measured_gate`.
