import hashlib
from pathlib import Path

from tools.altium_compile_evidence import build, validate


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    project = (
        tmp_path
        / "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb"
    )
    schematic = (
        tmp_path
        / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"
    )
    raw = (
        tmp_path
        / "hardware/system_carrier/altium/equivalence/compile_report_raw.txt"
    )
    project.parent.mkdir(parents=True, exist_ok=True)
    schematic.parent.mkdir(parents=True, exist_ok=True)
    raw.parent.mkdir(parents=True, exist_ok=True)
    project.write_bytes(b"PROJECT")
    schematic.write_bytes(b"SCHDOC")
    raw.write_text("Altium compile: 0 errors, 0 warnings\n", encoding="utf-8")
    return project, schematic, raw


def test_compile_evidence_build_and_validate_pass(tmp_path):
    project, schematic, raw = _fixture(tmp_path)

    report = build(
        repository_root=tmp_path,
        raw_report=raw,
        errors=0,
        warnings=0,
    )

    assert report["status"] == "PASS"
    assert report["errors"] == 0
    assert report["warnings"] == 0
    assert report["source_report_sha256"] == hashlib.sha256(
        raw.read_bytes()
    ).hexdigest()
    assert report["source_project_sha256"] == hashlib.sha256(
        project.read_bytes()
    ).hexdigest()
    assert report["source_schematic_sha256"] == hashlib.sha256(
        schematic.read_bytes()
    ).hexdigest()

    report_path = (
        tmp_path
        / "hardware/system_carrier/altium/equivalence/compile_report.json"
    )
    import json
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate(
        compile_report=report_path,
        repository_root=tmp_path,
    )
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["reason_codes"] == []


def test_compile_evidence_detects_changed_raw_report(tmp_path):
    _, _, raw = _fixture(tmp_path)
    report = build(
        repository_root=tmp_path,
        raw_report=raw,
        errors=0,
        warnings=0,
    )

    report_path = (
        tmp_path
        / "hardware/system_carrier/altium/equivalence/compile_report.json"
    )
    import json
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    raw.write_text("changed after wrapper\n", encoding="utf-8")

    result = validate(
        compile_report=report_path,
        repository_root=tmp_path,
    )
    assert result["status"] == "INVALID"
    assert "source_report_hash" in result["errors"]


def test_compile_evidence_nonzero_counts_fail(tmp_path):
    _, _, raw = _fixture(tmp_path)
    report = build(
        repository_root=tmp_path,
        raw_report=raw,
        errors=1,
        warnings=0,
    )

    assert report["status"] == "FAIL"

    report_path = (
        tmp_path
        / "hardware/system_carrier/altium/equivalence/compile_report.json"
    )
    import json
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate(
        compile_report=report_path,
        repository_root=tmp_path,
    )
    assert result["status"] == "FAIL"
    assert "COMPILE_ERRORS:1" in result["reason_codes"]
