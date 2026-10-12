# System Carrier Ethernet MagJack selection

## Rev.A selection

The System Carrier Ethernet connector is **Bel SI-60182-F**.

It replaces the provisional Bel P01-0006-01 before Review A because the
SI-60182-F manufacturer drawing is available and fully defines both the
electrical pinout and PCB hole pattern.

Selected properties:

- 1x1 integrated MagJack;
- 10/100BASE-T;
- tab down;
- through-hole;
- yellow/green LEDs;
- shield / EMI tabs;
- operating temperature -40 to +85 degC.

Bel lists P01-0006-01 as a compatible product for SI-60182-F.

## KiCad representation

KiCad already provides:

- symbol: `Connector:RJ45_Bel_SI-60062-F`;
- footprint: `Connector_RJ:RJ45_Bel_SI-60062-F`.

The stock SI-60062-F representation was cross-checked against the Bel
SI-60182-F drawing before reuse.

Electrical equivalence on the board side:

- P1 / P2 / P3 = first transformer pair and center tap;
- P4 / P5 / P6 = second transformer pair and center tap;
- P7 = no electrical connection in the published drawing;
- P8 = EMI/Bob-Smith return network.

Mechanical equivalence checked against the recommended PCB layouts:

- eight 0.89 mm signal holes;
- 1.27 mm horizontal signal pitch across seven intervals;
- 2.54 mm stagger between signal rows;
- 3.25 mm board-lock post holes;
- 1.57 mm shield holes;
- 1.02 mm LED holes;
- post spacing 11.43 mm;
- shield spacing 15.49 mm;
- identical LED-hole geometry.

The SI-60062-F itself is not selected because its rated operating
temperature is only 0 to +70 degC. Only its verified KiCad
symbol/footprint representation is reused.

## Manufacturer sources

- SI-60182-F product:
  https://www.belfuse.com/products/ethernet/magjacks-icms/si-60182-f
- SI-60182-F drawing:
  https://www.belfuse.com/media/drawings/products/magjack%20ICMs/dr-mag-si-60182-f.pdf
- SI-60062-F drawing:
  https://www.belfuse.com/media/drawings/products/magjack%20ICMs/dr-mag-si-60062-f.pdf
- P01-0006-01 product:
  https://www.belfuse.com/products/ethernet/magjacks-icms/p01-0006-01

This component decision is unrelated to the 76-81 GHz radar RF path.
