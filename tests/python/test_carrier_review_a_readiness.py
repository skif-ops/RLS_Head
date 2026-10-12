from tools.carrier_review_a_readiness import evaluate


def test_current_carrier_is_blocked_by_explicit_external_data(tmp_path):
    result = evaluate(
        repository_root=".",
        generated_dir=tmp_path / "cad",
    )

    assert result["schema"] == "SYSTEM-CARRIER-REVIEW-A-READINESS-001"
    assert result["status"] == "BLOCKED"
    assert result["parsed_schematic_count"] == 8
    assert result["open_external_blocker_count"] >= 1
    assert any(
        error == "external_document_blocker:MAGJACK_DRAWING"
        for error in result["errors"]
    )
