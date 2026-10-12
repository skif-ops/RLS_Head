# TPS259470A RPW0010A local footprint

U6 and U7 use the same project-local footprint for TPS259470ARPWR.

Primary source: TI RPW0010A package and example board-layout drawings in the
TPS25947 datasheet. The package is a 2 x 2 mm VQFN-HR with 10 electrical
pins and a non-generic copper topology.

The local footprint preserves the RPW topology:

- custom corner pads: 1, 4, 7, 10;
- side pads 2, 3, 8, 9: 0.60 x 0.30 mm;
- long center pads 5 and 6: 0.30 x 2.40 mm;
- split paste apertures on pads 5 and 6;
- courtyard: 2.90 x 2.90 mm.

The custom-pad geometry was independently cross-checked against KiCad
footprint MR !4677 for
`Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.475mm`, which cites the same TI
datasheet.

The footprint intentionally contains only electrical pad numbers 1 through
10. No synthetic 11-14 pads are introduced for the split corner copper.
