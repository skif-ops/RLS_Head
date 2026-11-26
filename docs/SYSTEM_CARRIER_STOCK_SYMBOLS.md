# System Carrier stock KiCad symbols

The generator uses official KiCad symbols for standard devices and connectors, including STM32H753, passives, generic connectors, Micro-Fit and JST-GH.

Non-standard active devices and protection arrays are generated in `SystemCarrier_Local.kicad_sym` from the pin contracts. Generation must fail rather than silently substitute a different pin mapping.

There is no LAN8742A or NEO-M9N symbol in the current design.
