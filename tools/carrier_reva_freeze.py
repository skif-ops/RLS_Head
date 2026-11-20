from __future__ import annotations

import csv
from pathlib import Path


REQUIRED = {
    "STM32H753IIT6",
    "ICM-42688-P",
    "TCAN3404DRBRQ1",
    "TPS62132RGTR",
    "TPS62133RGTR",
    "TPS259470ARPWR",
    "TPD4E05U06DQAR",
    "43045-0600",
    "SM06B-GHS-TB(LF)(SN)",
}


def validate_freeze(directory: str | Path) -> dict:
    root = Path(directory)
    bom = root / "BOM_SYS_CARRIER_003.csv"
    io = root / "FIRMWARE_IO_CONTRACT_SYS_001.csv"

    errors = []

    if not bom.is_file():
        errors.append("missing_bom")
        rows = []
    else:
        with bom.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

    selected = {
        str(row.get("mpn", "")).strip()
        for row in rows
        if str(row.get("status", "")).strip() == "SELECTED"
    }

    for mpn in sorted(REQUIRED - selected):
        errors.append(f"missing_selected:{mpn}")

    if "TPS62130ARGTR" in selected:
        errors.append("adjustable_buck_not_allowed")

    if not io.is_file():
        errors.append("missing_firmware_io_contract")
    else:
        with io.open("r", encoding="utf-8", newline="") as handle:
            io_rows = list(csv.DictReader(handle))
        signals = {str(row.get("signal", "")).strip() for row in io_rows}
        for signal in {
            "GNSS_PPS", "RADAR_REF", "IMU_DRDY", "RADAR_CAN",
            "HOST_UART1", "HOST_UART2", "GNSS_UART",
        }:
            if signal not in signals:
                errors.append(f"missing_io:{signal}")

    return {
        "schema": "SYSTEM-CARRIER-REVA-FREEZE-001",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "selected_mpn_count": len(selected),
    }
