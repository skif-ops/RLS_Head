# NEO-M9N local footprint

The System Carrier uses a project-local footprint for u-blox NEO-M9N-00B.

Manufacturer basis:

- 24-pad LCC receiver module;
- body 12.2 x 16.0 mm;
- suggested PCB land 1.0 x 0.8 mm;
- 1.1 mm vertical pitch;
- 3.0 mm center gap between the two six-pad groups on each side;
- pin numbering follows the u-blox pin assignment.

Right side:
- pins 1..6 from y=-7.0 to -1.5 mm;
- pins 7..12 from y=+1.5 to +7.0 mm.

Left side:
- pins 13..18 from y=+7.0 to +1.5 mm;
- pins 19..24 from y=-1.5 to -7.0 mm.

The footprint is validated by `tools.validate_neo_m9n_footprint`.
The GNSS RF input, ESD placement and optional active-antenna bias network
remain separate PCB-layout constraints.
