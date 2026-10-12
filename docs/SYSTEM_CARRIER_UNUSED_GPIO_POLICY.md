# STM32H753 unused GPIO no-connect policy

The System Carrier generator derives the assigned STM32 GPIO set directly
from `PINMAP_SYS_001.csv`.

For the STM32H753 symbol, every pin whose symbol name matches a GPIO name
(`PA0` through `PKn`) and is not present in the authoritative pin map
receives an explicit KiCad no-connect marker.

This makes unused GPIO intentional rather than ambiguous ERC errors. Any pin
that later becomes assigned automatically stops receiving a no-connect as
soon as it appears in the authoritative pin map.

The policy deliberately does not no-connect power, VCAP, reset, boot,
oscillator, or other non-GPIO pins. Those remain subject to explicit
electrical treatment and ERC.

This is a non-RF schematic-completeness policy only.
