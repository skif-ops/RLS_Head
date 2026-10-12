from pathlib import Path

from tools.carrier_review_a_external_preflight import evaluate_preflight


AUDITS = {
    "power": "PENDING",
    "clock": "PENDING",
    "reset_boot": "PENDING",
    "timing_capture": "PENDING",
    "imu": "PENDING",
    "ethernet": "PENDING",
    "can_fd": "PENDING",
}


def manifest():
    return {
        "schema": "CARRIER-REVIEW-A-MANIFEST-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "cad_tool": "KiCad",
        "cad_version": "9",
        "synthetic_fixture": False,
        "evidence_level": "CAD_REVIEW",
        "erc_policy": {
            "errors_allowed": 0,
            "warnings_allowed": 0,
        },
        "artifacts": [
            {"id": "schematic", "path": "carrier/board.kicad_sch", "sha256": "<FILL>"},
            {"id": "erc_json", "path": "carrier/erc.json", "sha256": "<FILL>"},
            {"id": "pinmap", "path": "inputs/pinmap.csv", "sha256": "<FILL>"},
            {"id": "bom", "path": "inputs/bom.csv", "sha256": "<FILL>"},
        ],
        "audits": dict(AUDITS),
    }


def make_inputs(root: Path):
    (root / "inputs").mkdir()
    (root / "carrier").mkdir()

    (root / "inputs" / "pinmap.csv").write_text(
        (
            "signal,mcu_pin,peripheral,direction,criticality\n"
            "GNSS_PPS,PA0,TIM2_CH1,IN,P0\n"
            "RADAR_REF,PB10,TIM2_CH3,IN,P0\n"
            "IMU_DRDY,PB11,TIM2_CH4,IN,P0\n"
        ),
        encoding="utf-8",
    )

    (root / "inputs" / "bom.csv").write_text(
        (
            "ref,qty,manufacturer,mpn,description\n"
            "U1,1,ST,STM32H753IIT6,MCU\n"
            "U2,1,TDK,ICM-42688-P,IMU\n"
            "U3,1,Microchip,LAN8742Ai-CZ-TR,PHY\n"
            "U4,1,TI,TCAN3404DRBRQ1,CAN\n"
            "U5,1,TI,TPS62130ARGTR,BUCK\n"
            "U6,1,TI,TPS259470ARPWR,EFUSE\n"
        ),
        encoding="utf-8",
    )


def test_ready_with_pending_outputs_and_audits(tmp_path):
    make_inputs(tmp_path)
    result = evaluate_preflight(
        manifest=manifest(),
        repository_root=tmp_path,
    )

    assert result["status"] == "READY_FOR_CAD_REVIEW_EXECUTION"
    assert "schematic:not_present_yet" in result["warnings"]
    assert "erc_json:not_present_yet" in result["warnings"]
    assert "audit_pending:power" in result["warnings"]


def test_bad_pinmap_blocks(tmp_path):
    make_inputs(tmp_path)
    (tmp_path / "inputs" / "pinmap.csv").write_text(
        "signal,mcu_pin,peripheral,direction,criticality\n",
        encoding="utf-8",
    )

    result = evaluate_preflight(
        manifest=manifest(),
        repository_root=tmp_path,
    )
    assert "pinmap_not_ready" in result["errors"]


def test_missing_audit_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    del data["audits"]["imu"]

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )
    assert "missing_audit:imu" in result["errors"]


def test_synthetic_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    data["synthetic_fixture"] = True

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )
    assert "synthetic_fixture_not_false" in result["errors"]


def test_unsafe_path_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    data["artifacts"][2]["path"] = "../pinmap.csv"

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )
    assert any("unsafe_path" in error for error in result["errors"])
