# System Carrier hierarchy interface contract

The System Carrier uses a real KiCad hierarchical interface rather than
relying on repeated local-label text across independent sheets.

`HIERARCHY_INTERFACE_SYS_001.csv` is authoritative for every signal that
crosses a child-sheet boundary. Each row specifies:

- child sheet;
- net name;
- child-perspective pin direction;
- one concrete anchor component/pin in that child;
- criticality.

Generation creates a sheet pin on the root schematic and a matching
hierarchical label on the child schematic at the anchor pin. Root-sheet local
labels connect equal-named sheet pins together on the root sheet.

Two gates are used:

1. `tools.carrier_hierarchy_contract` validates the CSV contract without
   KiCad dependencies.
2. `tools.validate_system_carrier_hierarchy` runs in the CAD job and asks
   kicad-sch-api to validate actual generated sheet pins against child
   hierarchical labels.

This is a prerequisite for treating ERC reduction as evidence of a connected
multi-sheet schematic. Same-named local labels on different child sheets are
not used as a substitute for hierarchy.
