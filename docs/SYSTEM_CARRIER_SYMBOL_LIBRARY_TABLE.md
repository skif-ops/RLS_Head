# System Carrier symbol-library table

The generated KiCad import project is self-contained at project configuration level. Its project-local `sym-lib-table` binds every library used by the current hierarchy:

- `SystemCarrier_Local`
- `Device`
- `Connector_Generic`
- `Connector`
- `Switch`
- `MCU_ST_STM32H7`

Stock libraries resolve through the installed KiCad symbol directory. The local library resolves through `${KIPRJMOD}`. The current table has no RF_GPS or Interface_Ethernet dependency.

This table supports reproducible import and comparison. Production schematics are generated from Altium.
