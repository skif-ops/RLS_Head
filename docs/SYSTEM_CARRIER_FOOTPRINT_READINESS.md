# System Carrier footprint readiness

The current Rev. A footprint plan is `FOOTPRINT_FREEZE_READY`: every reference in `FOOTPRINT_PLAN_SYS_001.csv` is `LOCKED` and resolves to an existing project-local or stock footprint.

Project-local verified footprints include ICM-42688-P LGA14 and TPS259470A RPW0010A for U6 and U7. Locked stock footprints include STM32H753 LQFP176, TCAN3404 DRB0008A, TPS62132 and TPS62133 RGT0016C, TPD4E05U06 DQA, ESD2CANFD24 DBZ, Molex Micro-Fit and JST-GH J8.

J8 uses `Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal`, matching `SM06B-GHS-TB(LF)(SN)`.

The native Altium import must preserve every designator-to-footprint assignment and must include verified Altium pad geometry and 3D clearance for the compact-board audit. A locked KiCad footprint alone does not authorize fabrication.
