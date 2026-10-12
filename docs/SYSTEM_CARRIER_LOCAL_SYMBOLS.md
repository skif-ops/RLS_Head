# System Carrier project-local symbol library

The Rev.A carrier generates `SystemCarrier_Local.kicad_sym` directly from
the authoritative `SYMBOL_PIN_CONTRACT_SYS_001.csv`.

Project-local symbols are used for:

- ICM-42688-P;
- TCAN3404DRBRQ1;
- TPS62132RGTR;
- TPS259470ARPWR (shared by U6/U7).

LAN8742A and NEO-M9N continue to use verified stock KiCad symbols.

The generator maps electrical roles from the pin contract to KiCad pin types
and embeds a footprint only when `FOOTPRINT_PLAN_SYS_001.csv` marks that
reference `LOCKED`. Thus unresolved custom footprints remain deliberately
blank rather than guessed.

The CAD scaffold validator fails if any of U2/U4/U5/U6/U7 falls back to a
`SYMBOL_PENDING` placeholder. The real KiCad 9 CI job then regenerates the
schematic, parses it, runs ERC, and uploads the generated local symbol library
with the CAD artifact.

This reduces symbol placeholders but does not by itself close Carrier
Review A; remaining connector/protection placeholders, ERC findings and
footprint readiness remain separate gates.
