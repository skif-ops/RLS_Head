# Real ANT-SIM gate external preflight

`tools.ant_sim_real_external_preflight` checks whether the three existing
simulation-evidence results needed by `tools.ant_sim_gate` are available
and structurally ready:

1. `ANT-D1-MAP-VALIDATION-001`;
2. `ANT-D1-MC-SUMMARY-001`;
3. `RAD-LB-006-REVB`.

States:

- `WAITING_FOR_UPSTREAM` — one or more result artifacts do not exist yet or
  have a non-final readiness state;
- `BLOCKED` — malformed/wrong-schema inputs or explicit failure states;
- `READY_FOR_GATE_ASSEMBLY` — map validation is `DATA_READY`, MC summary is
  `PASS`, and Rev.B is `PROJECTED`.

The preflight does not run or assert `ANT-SIM-GATE-001` PASS. That gate
remains simulation-only; physical antenna and field-range evidence remain
separate. No production Tx/Rx physical coordinates are encoded.
