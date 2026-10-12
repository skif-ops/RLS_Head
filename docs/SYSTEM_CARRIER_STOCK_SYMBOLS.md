# System Carrier stock KiCad symbols

The System Carrier generator now prefers official KiCad symbols for:

- `Interface_Ethernet:LAN8742A`
- `RF_GPS:NEO-M9N`

If either symbol is unavailable in the CI/runtime library set, generation
falls back to the existing `SYMBOL_PENDING` placeholder instead of silently
changing pin mappings.

This reduces custom-symbol scope while keeping the project reproducible.
The remaining custom-symbol candidates are validated through the local
pin/package contracts before Carrier Review A.
