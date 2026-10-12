# System Carrier Review A readiness

`tools.carrier_review_a_readiness` is the hard precondition between the
generated KiCad capture scaffold and the real `CARRIER_REVIEW_A` gate.

It blocks Review A when any of the following remain:

- `SYMBOL_PENDING` placeholders;
- explicit external-document blockers;
- unparseable KiCad sheets.

Unresolved footprint locks are reported separately as warnings because some
custom footprints can be completed in parallel with schematic capture, but
they remain manufacturing blockers.

The first explicit external-document blocker is the Bel
`P01-0006-01` MagJack drawing/pinout. The part itself remains active and
appropriate for 10/100BASE-T, but its integrated magnetics/LED pin mapping
must come from the manufacturer drawing or a verified CAD model rather than
being guessed.

This gate is intentionally conservative: `READY_FOR_REVIEW_A` is only
permission to run the real schematic/ERC review, not a Review A PASS.
