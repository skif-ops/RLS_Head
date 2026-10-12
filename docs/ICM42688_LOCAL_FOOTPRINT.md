# ICM-42688-P local footprint

The Rev.A System Carrier uses a project-local footprint for the
TDK InvenSense ICM-42688-P.

Manufacturer basis:

- package: 14-lead LGA;
- body: 2.5 x 3.0 mm;
- nominal lead/pad width: 0.25 mm;
- nominal lead/pad length: 0.475 mm;
- pitch: 0.5 mm;
- edge pin center-to-center: 1.5 mm / 1.0 mm.

TDK AN-000393 recommends the PCB land length/width equal the LGA solder-pad
length/width, with the solder-mask opening 0.10 mm larger in both dimensions.

The local footprint therefore uses 0.475 x 0.25 mm copper lands and
+0.05 mm solder-mask expansion on every side.

The pin arrangement follows the manufacturer package drawing:
1-4 left, 5-7 bottom, 8-11 right, 12-14 top.

The footprint is validated by
`tools.validate_icm42688_footprint` so that pad numbering, coordinates,
orientation and land dimensions cannot drift silently.
