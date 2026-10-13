# Carrier GNSS service

`gnss_service` tracks only the health and timing quality of the carrier's
own GNSS receiver.

It records:

- UART activity freshness;
- PPS freshness;
- fix-valid flag;
- time-valid flag;
- jamming indication;
- spoofing indication.

The service deliberately does not store routes, target coordinates or
vehicle-control commands. Position/navigation payload parsing remains outside
this small deterministic health layer.

The result can be included in carrier health and evidence telemetry so a
measurement session can be rejected or flagged when GNSS timing integrity is
not trustworthy.
