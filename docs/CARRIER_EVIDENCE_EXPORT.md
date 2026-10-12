# Carrier evidence export record

`evidence_export` provides a fixed-size binary record for one measurement
session.

The record binds:

- session ID;
- frozen configuration CRC32;
- measurement-session state;
- time-service state;
- carrier health/fault flags;
- radar/IMU/GNSS/drop counters;
- session start/close timestamps;
- local export timestamp.

Wire format version 1 is fixed at 56 bytes and uses little-endian integer
encoding.

The record intentionally contains no target coordinates, intercept solution,
guidance or actuation commands. It exists only to make measurement evidence
traceable to one frozen configuration/session.
