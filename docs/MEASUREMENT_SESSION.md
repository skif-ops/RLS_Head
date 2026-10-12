# Measurement session

`measurement_session` records immutable configuration identity and bounded
runtime counters for one measurement/evidence run.

State machine:

`IDLE -> ARMED -> ACTIVE -> CLOSED`

The configuration CRC is fixed at arm time and is never changed during the
session. Runtime counters record radar reference events, IMU events, GNSS
events and dropped capture events.

The module contains no target-state or control semantics. Its purpose is to
make bench/field evidence reproducible and to bind exported measurements to
one frozen configuration.
