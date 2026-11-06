# System Carrier Review A readiness

`tools.carrier_review_a_readiness` checks the generated import baseline before native Altium work. It rejects symbol placeholders, unresolved external-document blockers and unparseable KiCad sheets. Footprint issues remain manufacturing blockers even if schematic parsing succeeds.

For the current ECO, the exact JST-GH J8 footprint and external simpleRTK3B Pro pinout are bound in the source contracts. Their native Altium footprint, 3D and connector-access checks are completed during the compact-board mechanical audit.

`READY_FOR_REVIEW_A` permits the native review to run. It is not a Review A PASS, routing authority or production authority.
