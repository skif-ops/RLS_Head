# System Carrier input TVS topology correction

The Rev.A input TVS is a shunt transient clamp.

Correct topology:

`12V_IN / VIN_RAW -> system eFuse U6 -> VIN_PROTECTED`

with `SMAJ15CA` connected from `VIN_RAW` to `GND`.

The previous power-tree notation represented the TVS as a series transition
`VIN_RAW -> VIN_TVS`. That notation was electrically misleading and is now
removed. No separate `VIN_TVS` rail exists.

This correction aligns the power tree with the existing netlist and with the
physical use of a bidirectional TVS clamp.
