import csv
from pathlib import Path

from tools.altium_pilot_bom_enrich import enrich


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "hardware/system_carrier"
NATIVE_BOM = (
    SYSTEM / "altium/release/pilot_r1/assembly/BOM_NATIVE.csv"
)


def test_superseded_pilot_bom_is_rejected_after_uart_gnss_eco():
    _, result = enrich(
        system_root=SYSTEM,
        native_bom=NATIVE_BOM,
    )

    assert result["status"] == "FAIL"
    assert result["native_designator_count"] == 92
    assert "extra_designators:C60,C61,C62,C63,C64,C65,C80,C81,C82,L80,R80,R81,R82,U3,U8,Y2" in result["errors"]
    assert "missing_designators:C90,C91,C92,C93,L9,R90,U9" in result["errors"]


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
