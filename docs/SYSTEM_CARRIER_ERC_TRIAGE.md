# System Carrier ERC triage

`tools.carrier_erc_triage` converts KiCad ERC JSON into a stable,
machine-readable summary:

- total violations;
- severity counts;
- violation-type counts;
- sheet counts;
- reference-designator counts when available;
- per-sheet/per-type rows.

With `--baseline`, it also reports deltas. This lets schematic changes show
whether they actually reduce ERC and whether a fix in one sheet creates new
findings elsewhere.

The tool is diagnostic only. It never suppresses, waives, or reclassifies
KiCad ERC violations.
