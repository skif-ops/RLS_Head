from pathlib import Path

from tools.altium_native_file_preflight import CFB_MAGIC, validate


def _cfb_stub(*, major: int = 3) -> bytes:
    sector_shift = 9 if major == 3 else 12
    size = 1 << sector_shift
    data = bytearray(size)
    data[:8] = CFB_MAGIC
    data[24:26] = (0x003E).to_bytes(2, "little")
    data[26:28] = major.to_bytes(2, "little")
    data[28:30] = (0xFFFE).to_bytes(2, "little")
    data[30:32] = sector_shift.to_bytes(2, "little")
    data[32:34] = (6).to_bytes(2, "little")
    return bytes(data)


def test_native_file_preflight_accepts_cfb_altium_pair(tmp_path: Path):
    sch = tmp_path / "EVT_SYS_CARRIER.SchDoc"
    pcb = tmp_path / "EVT_SYS_CARRIER.PcbDoc"
    sch.write_bytes(_cfb_stub())
    pcb.write_bytes(_cfb_stub())

    result = validate(schematic=sch, pcb=pcb)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["artifacts"]["schematic"]["cfb_major_version"] == 3
    assert result["artifacts"]["pcb"]["sector_size"] == 512
    assert len(result["artifacts"]["pcb"]["sha256"]) == 64


def test_native_file_preflight_rejects_extension_only_placeholders(
    tmp_path: Path,
):
    sch = tmp_path / "EVT_SYS_CARRIER.SchDoc"
    pcb = tmp_path / "EVT_SYS_CARRIER.PcbDoc"
    sch.write_bytes(b"NOT_A_NATIVE_SCHDOC")
    pcb.write_bytes(b"NOT_A_NATIVE_PCBDOC")

    result = validate(schematic=sch, pcb=pcb)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("schematic:")
        for item in result["errors"]
    )
    assert any(
        item.startswith("pcb:")
        for item in result["errors"]
    )


def test_native_file_preflight_rejects_wrong_cfb_geometry(tmp_path: Path):
    sch = tmp_path / "EVT_SYS_CARRIER.SchDoc"
    pcb = tmp_path / "EVT_SYS_CARRIER.PcbDoc"
    broken = bytearray(_cfb_stub())
    broken[30:32] = (12).to_bytes(2, "little")
    sch.write_bytes(bytes(broken))
    pcb.write_bytes(_cfb_stub())

    result = validate(schematic=sch, pcb=pcb)

    assert result["status"] == "FAIL"
    assert "schematic:cfb_sector_shift:12!=9" in result["errors"]
