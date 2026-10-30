import csv
from pathlib import Path

from tools.altium_pilot_bom_enrich import enrich


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware/system_carrier"
NATIVE_BOM = (
    SYSTEM / "altium/release/pilot_r1/assembly/BOM_NATIVE.csv"
)


def test_current_pilot_bom_matches_uart_gnss_eco():
    rows, result = enrich(
        system_root=SYSTEM,
        native_bom=NATIVE_BOM,
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["native_designator_count"] == 83
    assert result["contract_designator_count"] == 83
    assert result["output_designator_count"] == 83
    assert result["pilot_disposition_counts"] == {
        "DNP": 2,
        "FIT": 78,
        "PCB_ONLY": 3,
    }
    assert len(rows) == 83


def test_pilot_bom_enrichment_rejects_mpn_change(tmp_path):
    with NATIVE_BOM.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["MPN"] = "WRONG"
    changed = tmp_path / "bom.csv"
    with changed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    _, result = enrich(
        system_root=SYSTEM,
        native_bom=changed,
    )

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("mpn_mismatch:")
        for item in result["errors"]
    )
