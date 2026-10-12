# System Carrier symbol-library table

The generated KiCad Carrier project is self-contained at the project
configuration level.

The generator writes a project-local `sym-lib-table` that explicitly binds
every symbol library used by the generated schematic:

- SystemCarrier_Local;
- Device;
- Connector_Generic;
- Connector;
- RF_GPS;
- Switch;
- MCU_ST_STM32H7;
- Interface_Ethernet.

Stock libraries resolve through KiCad 9's `${KICAD9_SYMBOL_DIR}` path
variable. The project-local library resolves through `${KIPRJMOD}`.

This eliminates headless/ERC dependence on a user's global KiCad symbol
library table. It changes no electrical connectivity and therefore must not
be interpreted as Review A closure by itself.
