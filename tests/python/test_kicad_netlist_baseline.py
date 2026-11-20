import csv
from pathlib import Path

from tools.kicad_netlist_baseline import build


def test_kicad_netlist_baseline_filters_to_physical_refs(tmp_path):
    system = tmp_path / "hardware/system_carrier"
    system.mkdir(parents=True)
    (system / "BOM_SYS_CARRIER_LAYOUT_004.csv").write_text(
        "ref,qty,manufacturer,value_or_mpn,description,procurement_class,"
        "footprint_id,population,status\n"
        "U1,1,X,U1,MCU,LOCKED,FP,POPULATE,LOCKED\n"
        "R1,1,X,R1,R,LOCKED,FP,POPULATE,LOCKED\n",
        encoding="utf-8",
    )
    (system / "SYMBOL_PIN_CONTRACT_SYS_001.csv").write_text(
        "ref,pin_number,connection\n"
        "U1,2,OPEN_INTERNAL_SELECT\n",
        encoding="utf-8",
    )

    xml = tmp_path / "net.xml"
    xml.write_text(
        """<export>
<nets>
  <net code="1" name="NET_A">
    <node ref="U1" pin="1"/>
    <node ref="R1" pin="1"/>
    <node ref="#PWR01" pin="1"/>
  </net>
  <net code="2" name="NET_B">
    <node ref="R1" pin="2"/>
  </net>
</nets>
</export>
""",
        encoding="utf-8",
    )

    out = tmp_path / "baseline.csv"
    result = build(
        system_root=system,
        xml_netlist=xml,
        output_csv=out,
    )

    assert result["status"] == "PASS"
    assert result["connected_endpoint_count"] == 3

    with out.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {(r["designator"], r["pin"], r["net_name"]) for r in rows} == {
        ("U1", "1", "NET_A"),
        ("R1", "1", "NET_A"),
        ("R1", "2", "NET_B"),
    }


def test_kicad_netlist_baseline_rejects_connected_open_pin(tmp_path):
    system = tmp_path / "hardware/system_carrier"
    system.mkdir(parents=True)
    (system / "BOM_SYS_CARRIER_LAYOUT_004.csv").write_text(
        "ref\nU1\n", encoding="utf-8"
    )
    (system / "SYMBOL_PIN_CONTRACT_SYS_001.csv").write_text(
        "ref,pin_number,connection\nU1,2,OPEN_INTERNAL_SELECT\n",
        encoding="utf-8",
    )
    xml = tmp_path / "net.xml"
    xml.write_text(
        '<export><nets><net name="GND"><node ref="U1" pin="2"/>'
        '</net></nets></export>',
        encoding="utf-8",
    )

    result = build(
        system_root=system,
        xml_netlist=xml,
        output_csv=tmp_path / "baseline.csv",
    )

    assert result["status"] == "FAIL"
    assert "open_pin_connected:U1.2:GND" in result["errors"]
