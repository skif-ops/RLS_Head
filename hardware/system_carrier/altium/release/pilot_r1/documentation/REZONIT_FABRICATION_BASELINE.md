# Rezonit fabrication baseline

Date: 2026-10-27

This document records Rezonit as the selected candidate PCB fabricator for
the EVT System Carrier. It is a preparation baseline, not a released
fabricator stack or production authorization.

## Candidate process

- Fabricator: Rezonit
- Construction: four-layer FR-4
- Requested finished thickness: 1.60 mm
- Copper: 35 um on all four layers
- Via type: standard plated through-hole
- Controlled impedance: required for 50 ohm GNSS RF and 100 ohm Ethernet MDI
- Production binding: `PENDING_CONFIRMATION`

Rezonit's published standard four-layer construction with 35 um copper uses
a nominal 1.50 mm board. The TG150 version lists 0.115 mm outer prepregs and
a 1.13 mm core; the published actual thickness is 1.50 mm before plating,
finish and solder mask. The project retains its 1.60 mm mechanical target, so
the exact stack must be confirmed by Rezonit as an order-specific stack.

## Published baseline capabilities

For 35 um copper, the published basic values are:

- minimum conductor width: 0.20 mm
- minimum conductor spacing: 0.20 mm
- minimum plated hole: 0.30 mm
- minimum via annular ring: 0.15 mm
- minimum component-pad annular ring: 0.20 mm
- minimum non-plated hole: 0.50 mm
- minimum edge-to-edge spacing between holes: 0.20 mm
- copper clearance from a routed board contour: 0.25 mm

The current 0.20 mm general clearance and 0.30 mm via drill therefore match
the published basic process floor. They remain subject to project review and
formal order confirmation.

## Impedance hold

Rezonit's published typical 35 um, 1.50 mm TG150 construction lists starting
geometries of approximately 0.18 mm for a 50 ohm microstrip and 0.15 mm /
0.30 mm for a 100 ohm differential pair. These values differ from the EVT
provisional 0.36 mm GNSS trace and 0.26 mm / 0.20 mm Ethernet pair.

No production impedance claim is made from the website table alone. Rezonit
must confirm the 1.60 mm stack, finished copper, dielectric properties and
field-solver geometries before the PCB impedance rules or routed geometry are
changed.

## Official sources

- https://www.rezonit.ru/pcb/mnogosloynye-pechatnye-platy/
- https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/proektirovanie-elementov-konstrukcii-pechatnoj-platy-proizvodstva-v-rezonit/tipovye-sborki-i-konstruktsii-pechatnykh-plat/
- https://www.rezonit.ru/price_pcb/

The sources were reviewed on 2026-10-27. Final values must come from the
fabricator response for the actual order.
