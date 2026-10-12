from tools.carrier_erc_triage import build_triage


def erc(pin_count=2, warning_count=1):
    return {
        "kicad_version": "9.0.9",
        "sheets": [
            {
                "path": "/MCU_CORE/",
                "violations": [
                    *[
                        {
                            "severity": "error",
                            "type": "pin_not_connected",
                            "description": "pin",
                            "items": [
                                {
                                    "description": "U1 pin",
                                }
                            ],
                        }
                        for _ in range(pin_count)
                    ],
                    *[
                        {
                            "severity": "warning",
                            "type": "label_dangling",
                            "description": "label",
                            "items": [],
                        }
                        for _ in range(warning_count)
                    ],
                ],
            }
        ],
    }


def test_summarizes_erc_by_type_sheet_and_ref():
    result = build_triage(erc())

    assert result["schema"] == "SYSTEM-CARRIER-ERC-TRIAGE-001"
    assert result["total_violations"] == 3
    assert result["by_severity"] == {
        "error": 2,
        "warning": 1,
    }
    assert result["by_type"]["pin_not_connected"] == 2
    assert result["by_sheet"]["/MCU_CORE/"] == 3
    assert result["by_ref"]["U1"] == 2


def test_baseline_delta_is_explicit():
    result = build_triage(
        erc(pin_count=1, warning_count=0),
        baseline=erc(pin_count=3, warning_count=2),
    )

    assert result["delta"]["total"] == -4
    assert (
        result["delta"]["by_type"]["pin_not_connected"]
        == -2
    )
    assert (
        result["delta"]["by_type"]["label_dangling"]
        == -2
    )
