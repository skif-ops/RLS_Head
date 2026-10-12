import json

from tools.carrier_review_a_readiness import (
    evaluate,
)


def test_current_carrier_is_blocked_by_explicit_external_data(
    tmp_path,
):
    manifest = {
        "schema":
            "SYSTEM-CARRIER-CAD-SCAFFOLD-001",
        "child_sheets": [
            "10_POWER_INPUT.kicad_sch",
            "20_MCU_CORE.kicad_sch",
            "30_TIME_GNSS.kicad_sch",
            "40_IMU.kicad_sch",
            "50_RADAR_IO_CAN.kicad_sch",
            "60_ETHERNET.kicad_sch",
            "70_DEBUG_BOOT.kicad_sch",
        ],
        "symbol_placeholders": [
            {
                "reference": "J6",
                "value":
                    "P01-0006-01_MAGJACK",
            }
        ],
    }

    manifest_path = (
        tmp_path
        / "cad_scaffold_manifest.json"
    )
    manifest_path.write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )

    result = evaluate(
        repository_root=".",
        scaffold_manifest=
            manifest_path,
    )

    assert (
        result["schema"]
        == "SYSTEM-CARRIER-REVIEW-A-READINESS-001"
    )
    assert result["status"] == "BLOCKED"
    assert result["sheet_count"] == 8
    assert result[
        "open_external_blocker_count"
    ] >= 1
    assert any(
        error
        == "external_document_blocker:MAGJACK_DRAWING"
        for error
        in result["errors"]
    )
    assert any(
        error.startswith(
            "symbol_placeholder:J6:"
        )
        for error
        in result["errors"]
    )
