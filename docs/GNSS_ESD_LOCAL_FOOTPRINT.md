# ESD0P2RF-02LS local footprint

The System Carrier uses a project-local footprint for the GNSS RF protection
diode ESD0P2RF-02LS in Infineon PG-TSSLP-2-1.

The official package drawing defines:

- body: 0.62 x 0.32 mm;
- two copper lands: 0.32 x 0.24 mm;
- copper gap between the lands: 0.14 mm;
- pad-center pitch: 0.38 mm;
- stencil apertures: 0.27 x 0.19 mm.

The KiCad footprint uses 0.32 x 0.24 mm copper pads at y = +/-0.19 mm and a
-0.025 mm paste margin on each side, producing the manufacturer 0.27 x
0.19 mm stencil aperture.

Pin 1 is the lower pad and pin 2 is the upper pad in the package bottom-view
orientation used by the Infineon drawing.

The device remains subject to the PCB placement rule already in the carrier
contract: place it immediately behind the GNSS U.FL entry with the shortest
possible shunt-to-ground path.
