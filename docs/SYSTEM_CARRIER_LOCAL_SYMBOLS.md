# System Carrier project-local symbol library

`SystemCarrier_Local.kicad_sym` is generated from the authoritative pin contracts.

The library contains verified symbols for ICM-42688-P, TCAN3404DRBRQ1, TPS62132RGTR, TPS62133RGTR, TPS259470ARPWR, the Y1 oscillator and the D3, D4 and D8 protection arrays.

The generator maps electrical roles from the pin contracts to KiCad pin types and embeds only locked footprints. The CAD scaffold validator fails if any required local device falls back to a placeholder.

These symbols are the Altium import source. Current release schematics are compiled from the imported native Altium project.
