# System Carrier power-budget gate

`tools.carrier_power_budget` evaluates the authoritative
`POWER_BUDGET_SYS_001.csv` before PCB freeze.

It separates:

- allocated non-reserve load;
- explicit engineering reserve;
- total rail allocation;
- remaining current headroom.

Current Rev.A interpretation:

- the 3V3 rail has large headroom against the current non-reserve allocation;
- the protected RADAR_12V branch is intentionally close to its programmed
  current limit and is therefore expected to report a low-headroom warning.

A warning does not imply electrical failure. It means the branch requires
bench inrush/current and thermal verification before hardware freeze.

The gate does not estimate radar sensing performance and does not alter any
RF configuration.
