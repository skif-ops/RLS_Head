# System Carrier Rev.A schematic/PCB capture gate

The authoritative inputs for Rev.A are:

- BOM_SYS_CARRIER_003.csv
- PINMAP_SYS_001.csv
- CLOCK_TREE_SYS_001.csv
- POWER_TREE_SYS_001.csv
- NETLIST_SYS_001.csv
- RADAR_INTERFACE_SYS_001.csv
- SCHEMATIC_BLOCKS_SYS_001.csv
- SCHEMATIC_COMPONENTS_SYS_001.csv
- CONNECTOR_PINOUT_SYS_001.csv
- POWER_BUDGET_SYS_001.csv

## Schematic capture sequence

1. POWER_INPUT
2. MCU_CORE
3. TIME_GNSS
4. IMU
5. RADAR_IO_CAN
6. ETHERNET
7. DEBUG_BOOT
8. TOP hierarchy

## Rev.A mandatory checks

- TPS62132 fixed 3.3 V variant only; do not substitute adjustable TPS62130.
- U6/U7 TPS259470 programming networks match the authoritative component table.
- every STM32 VDD pin receives local 100 nF decoupling;
- VCAP1/VCAP2 each receive dedicated 2.2 uF capacitors;
- RMII 50 MHz clock topology matches CLOCK_TREE_SYS_001;
- GNSS PPS, RADAR_REF and IMU_DRDY all remain on TIM2 capture channels;
- CAN termination is population-selectable;
- RADAR_REF connector path includes ground return;
- GNSS RF ESD device sits immediately behind U.FL;
- no mmWave RF nets are present on System Carrier.

## PCB capture priorities

P0:
- input protection/eFuse;
- buck hot loop;
- MCU decoupling/VCAP;
- 50 MHz RMII clock;
- TIM2 capture lines;
- GNSS RF connector/ESD;
- CAN-FD connector/ESD/return;
- radar 12 V branch.

P1:
- RMII data;
- IMU SPI;
- GNSS UART;
- debug interfaces.

## Manufacturing outputs required before Review A close

- KiCad project/schematic;
- ERC JSON;
- native BOM export;
- pinmap consistency report;
- schematic PDF;
- component/footprint audit;
- Review A manifest with hashes.

PCB routing/DRC is a later gate and must not be implied by schematic Review A.
