import copy
import json
from pathlib import Path

from tools.carrier_review_a import (
    parse_erc_json,
    validate_manifest,
    validate_pinmap,
)


FIXTURE = Path(
    "tests/fixtures/carrier_review_a/manifest.json"
)


def load_fixture() -> dict:
    return json.loads(
        FIXTURE.read_text(encoding="utf-8")
    )


def test_synthetic_fixture_test_ready():
    result = validate_manifest(FIXTURE, ".")

    assert result["schema"] == (
        "CARRIER-REVIEW-A-RESULT-001"
    )
    assert result["status"] == "TEST_READY"
    assert result["synthetic_fixture"] is True
    assert result["errors"] == []
    assert result["reason_codes"] == []
    assert result["erc"]["errors"] == 0
    assert result["erc"]["warnings"] == 0
    assert result["pinmap"]["status"] == "PASS"
    assert result["bom"]["status"] == "PASS"
    assert all(
        value == "PASS"
        for value in result["audits"].values()
    )


def test_erc_nested_sheet_violation_parse(tmp_path):
    erc_path = tmp_path / "erc.json"

    erc_path.write_text(
        json.dumps(
            {
                "kicad_version": "9.0.9",
                "source": "board.kicad_sch",
                "sheets": [
                    {
                        "path": "/",
                        "violations": [
                            {
                                "severity": "error",
                                "type": "pin_not_connected",
                                "description": "open pin",
                            },
                            {
                                "severity": "warning",
                                "type": "pin_to_pin",
                                "description": "pin conflict",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = parse_erc_json(erc_path)

    assert result["errors"] == 1
    assert result["warnings"] == 1
    assert len(result["violations"]) == 2
    assert result["violations"][0]["sheet"] == "/"


def test_timing_pinmap_mismatch_fails(tmp_path):
    path = tmp_path / "pinmap.csv"

    path.write_text(
        "signal,mcu_pin,peripheral,direction,criticality\n"
        "GNSS_PPS,PA1,TIM2_CH1,IN,P0\n"
        "RADAR_REF,PB10,TIM2_CH3,IN,P0\n"
        "IMU_DRDY,PB11,TIM2_CH4,IN,P0\n",
        encoding="utf-8",
    )

    result = validate_pinmap(path)

    assert result["status"] == "FAIL"
    assert any(
        item.startswith("GNSS_PPS:pin:")
        for item in result["findings"]
    )


def test_real_review_cannot_pass_as_software_ci(
    tmp_path,
):
    manifest = load_fixture()
    manifest["synthetic_fixture"] = False
    manifest["evidence_level"] = "SOFTWARE_CI"

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    result = validate_manifest(path, ".")

    assert result["status"] == "HOLD"
    assert "EVIDENCE_LEVEL" in result["reason_codes"]


def test_hash_mismatch_invalid(tmp_path):
    manifest = copy.deepcopy(load_fixture())
    manifest["artifacts"][0]["sha256"] = "0" * 64

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    result = validate_manifest(path, ".")

    assert result["status"] == "INVALID"
    assert any(
        item.startswith("hash_mismatch:")
        for item in result["errors"]
    )
