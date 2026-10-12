import json

from tools.carrier_review_a_readiness import (
    evaluate,
)


CHILDREN = [
    "10_POWER_INPUT.kicad_sch",
    "20_MCU_CORE.kicad_sch",
    "30_TIME_GNSS.kicad_sch",
    "40_IMU.kicad_sch",
    "50_RADAR_IO_CAN.kicad_sch",
    "60_ETHERNET.kicad_sch",
    "70_DEBUG_BOOT.kicad_sch",
]


def _write_manifest(tmp_path, placeholders):
    path = tmp_path / "cad_scaffold_manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema":
                    "SYSTEM-CARRIER-CAD-SCAFFOLD-001",
                "child_sheets": CHILDREN,
                "symbol_placeholders":
                    placeholders,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_current_carrier_is_ready_for_real_review_a(tmp_path):
    result = evaluate(
        repository_root=".",
        scaffold_manifest=_write_manifest(
            tmp_path,
            [],
        ),
    )

    assert (
        result["schema"]
        == "SYSTEM-CARRIER-REVIEW-A-READINESS-001"
    )
    assert result["status"] == "READY_FOR_REVIEW_A"
    assert result["sheet_count"] == 8
    assert result["placeholder_count"] == 0
    assert result["open_external_blocker_count"] == 0
    assert result["unresolved_footprint_count"] == 0
    assert result["errors"] == []


def test_any_symbol_placeholder_still_blocks_review_a(tmp_path):
    result = evaluate(
        repository_root=".",
        scaffold_manifest=_write_manifest(
            tmp_path,
            [
                {
                    "reference": "J6",
                    "value": "UNRESOLVED",
                }
            ],
        ),
    )

    assert result["status"] == "BLOCKED"
    assert result["open_external_blocker_count"] == 0
    assert any(
        error.startswith("symbol_placeholder:J6:")
        for error in result["errors"]
    )
