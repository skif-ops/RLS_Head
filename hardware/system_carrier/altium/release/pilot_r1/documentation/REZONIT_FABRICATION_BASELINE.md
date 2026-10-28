# Rezonit fabrication baseline

Date: 2026-10-28

This document captures the Rezonit data available from the fabricator's
published technical pages for preparation of the EVT System Carrier pilot
package. It is not an order-specific stack approval and does not authorize
production.

## Working factory baseline

- Fabricator: Rezonit
- Construction: standard four-layer FR-4 with plated through holes
- Working material: FR-4 TG150, IPC-4101/99
- Working published thickness: 1.50 mm, excluding plating, finish and solder mask
- Copper: 35 um on all four layers
- Controlled impedance: required for 50 ohm GNSS RF and 100 ohm Ethernet MDI
- Package use: pilot quotation, CAM preflight and order-specific correction
- Production authority: `NOT_AUTHORIZED`

The published TG150 four-layer stack is the working factory baseline because
it is the closest fully described Rezonit construction to the project target.
The project 1.60 mm mechanical target remains recorded. The 0.10 mm difference
and the order-specific finished thickness are deferred for Rezonit CAM review.
They do not block assembly of the pilot archive.

## Published four-layer stacks

| Variant | Layer sequence from top | Published construction | Published actual thickness |
| --- | --- | --- | --- |
| TG150 | Cu / prepreg / Cu / core / Cu / prepreg / Cu | 35 um / 2116 0.115 mm / 35 um / FR-4 core 1.13 mm / 35 um / 2116 0.115 mm / 35 um | 1.50 mm |
| TG170 | Cu / prepreg / Cu / core / Cu / prepreg / Cu | 35 um / 2116 0.125 mm / 35 um / FR-4 core 1.13 mm / 35 um / 2116 0.125 mm / 35 um | 1.52 mm |

Rezonit also publishes four-layer 35 um TG150 actual thicknesses of 0.88,
1.50 and 1.886 mm for nominal 1.0, 1.5 and 2.0 mm constructions. For TG170,
the corresponding published actual values include 0.90 and 1.52 mm for the
nominal 1.0 and 1.5 mm constructions.

Published material properties used for this record:

- TG150 2116 prepreg: 0.115 mm, Dk 4.2 at 1 MHz, marked available.
- TG150 1.13 mm core with 35 um foil: total 1.20 +/- 0.075 mm, Dk 4.6 at 1 MHz, marked available.
- TG170 2116 prepreg: 0.125 mm, Dk 5.1 at 1 MHz, marked available.
- TG170 1.13 mm core with 35 um foil: total 1.20 +/- 0.075 mm, Dk 4.7 at 1 MHz, marked available.

The machine-readable copy is `REZONIT_PUBLISHED_STACK_4L_35UM.csv`.

## Published 35 um process limits

| Parameter | Basic | Advanced |
| --- | ---: | ---: |
| Conductor width | 0.20 mm | 0.15 mm |
| Conductor spacing | 0.20 mm | 0.15 mm |
| Plated hole | 0.30 mm | not separately stated |
| Via annular ring | 0.15 mm | 0.10 mm |
| Component-pad annular ring | 0.20 mm | 0.15 mm |
| Inter-via diameter range | 0.30 to 0.50 mm | 0.20 to 0.50 mm |

Additional published limits:

- mesh polygon width and gap: 0.20 mm
- polygon clearance: 0.20 mm
- inner copper to plated hole: 0.25 mm
- edge-to-edge spacing between holes: 0.20 mm
- minimum non-plated hole: 0.50 mm
- topology to non-plated hole: 0.20 mm
- copper to routed external or internal contour: 0.25 mm
- minimum silkscreen line: 0.15 mm
- minimum silkscreen text height: 1.0 mm

The current project 0.20 mm general clearance and 0.30 mm via drill meet the
published basic values. This is a comparison with generic published limits,
not an order acceptance statement.

## Solder mask, finishes and mechanics

- Green solder-mask bridge for 18 or 35 um copper: 0.10 mm.
- Published solder-mask expansion: 0.025 mm.
- Published solder-mask Dk: 3.5.
- Rezonit states mask conformance to GOST R 54849-2011 (IPC-SM-840E:2010).
- Immersion silver: 0.2 to 0.3 um.
- ENIG: gold 0.075 to 0.125 um over nickel 3 to 6 um.
- Immersion tin: 1.0 um.
- Default routing cutter: 2 mm. Slots below 2 mm use a 1 mm cutter.
- Published routing positioning tolerance: +/- 0.20 mm.

Surface finish remains an order selection. The available finishes are listed
here so CAM and procurement can bind one without reopening the source-data
search.

## Published impedance starting values

For the published four-layer, 35 um, 1.50 mm TG150 construction, Rezonit lists:

- 50 ohm microstrip starting width: 0.18 mm
- 100 ohm differential starting geometry: 0.15 mm width and 0.30 mm gap

The routed EVT provisional values are 0.36 mm for GNSS and 0.26 mm width with
0.20 mm gap for Ethernet. The values do not match. No production impedance
claim is made from the website table. The routed PcbDoc and locked EVT
contracts remain unchanged until Rezonit supplies an order-specific stack,
finished copper and solver result.

## Deferred order corrections

The following items are intentionally deferred and are not pilot-archive
blockers:

1. Final 1.60 mm or nearest accepted finished thickness.
2. Finished copper after plating.
3. Exact dielectric thicknesses and production tolerances.
4. Order-bound 50 ohm and 100 ohm solver geometries.
5. Surface finish and any associated pad or mask correction.

They remain production-release inputs. Production authority stays
`NOT_AUTHORIZED` until the final fabrication drawing and order-bound values are
accepted.

## Official sources

- https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/proektirovanie-elementov-konstrukcii-pechatnoj-platy-proizvodstva-v-rezonit/tipovye-sborki-i-konstruktsii-pechatnykh-plat/
- https://www.rezonit.ru/pcb/mnogosloynye-pechatnye-platy/
- https://www.rezonit.ru/pcb/mnogosloynye-pechatnye-platy/serial/
- https://www.rezonit.ru/price_pcb/
- https://www.rezonit.ru/account/

The sources were reviewed on 2026-10-28. Exact order values take precedence
when they become available.
