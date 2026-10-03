import copy
from dataclasses import replace
from pathlib import Path

from tools.evm_profile_gate import (
    evaluate_profile_campaign,
    load_config,
    load_metrics_csv,
)
from tools.evm_run_manifest import load_json


ROOT = Path("tests/fixtures/evm_profiles")
METRICS = Path("tests/fixtures/evm_profile_metrics_ci.csv")
CONFIG = Path("config/evm_profile_gate_evt.json")


def manifests():
    return [
        (str(ROOT / "TRACK.json"), load_json(ROOT / "TRACK.json")),
        (str(ROOT / "LR1.json"), load_json(ROOT / "LR1.json")),
        (str(ROOT / "LR2.json"), load_json(ROOT / "LR2.json")),
        (str(ROOT / "LRX.json"), load_json(ROOT / "LRX.json")),
    ]


def test_profile_fixture_roles():
    result = evaluate_profile_campaign(
        load_metrics_csv(METRICS),
        manifests(),
        load_config(CONFIG),
    )

    assert result["schema"] == "EVM-PROFILE-RESULT-001"
    assert result["status"] == "TEST_READY"
    assert result["errors"] == []

    profiles = result["profiles"]

    assert profiles["TRACK"]["status"] == "OPERATIONAL"
    assert profiles["LR1"]["status"] == "OPERATIONAL"
    assert profiles["LR2"]["status"] == "CONDITIONAL"
    assert profiles["LRX"]["status"] == "RESEARCH_ONLY"

    assert profiles["LR1"]["gain_vs_track_db_median"] == 3.2
    assert profiles["LR2"]["gain_vs_track_db_median"] == 5.0
    assert profiles["LRX"]["gain_vs_track_db_median"] == 8.5


def test_lr_without_gain_fails():
    rows = load_metrics_csv(METRICS)
    changed = [
        replace(row, margin_db=-1.0)
        if row.profile_class == "LR1"
        else row
        for row in rows
    ]

    result = evaluate_profile_campaign(
        changed,
        manifests(),
        load_config(CONFIG),
    )

    assert result["profiles"]["LR1"]["status"] == "FAIL"
    assert "NO_RANGE_BENEFIT" in (
        result["profiles"]["LR1"]["reason_codes"]
    )


def test_overrun_is_hard_failure():
    rows = load_metrics_csv(METRICS)
    changed = [
        replace(row, overrun_count=1)
        if row.profile_class == "LR1"
        else row
        for row in rows
    ]

    result = evaluate_profile_campaign(
        changed,
        manifests(),
        load_config(CONFIG),
    )

    assert result["profiles"]["LR1"]["status"] == "FAIL"
    assert "OVERRUN" in result["profiles"]["LR1"]["reason_codes"]


def test_profile_manifest_mismatch_invalid():
    ms = manifests()
    altered = copy.deepcopy(ms[1][1])
    altered["profile_id"] = "WRONG-PROFILE"

    ms[1] = (ms[1][0], altered)

    result = evaluate_profile_campaign(
        load_metrics_csv(METRICS),
        ms,
        load_config(CONFIG),
    )

    assert result["status"] == "INVALID"
    assert any(
        item.startswith("profile_id_mismatch:")
        for item in result["errors"]
    )


def test_missing_track_baseline_holds_profile():
    rows = [
        row
        for row in load_metrics_csv(METRICS)
        if row.profile_class != "TRACK"
    ]

    ms = [
        item
        for item in manifests()
        if "TRACK.json" not in item[0]
    ]

    result = evaluate_profile_campaign(
        rows,
        ms,
        load_config(CONFIG),
    )

    assert result["status"] == "INVALID"
    assert result["profiles"]["LR1"]["status"] == "HOLD"
    assert "NO_TRACK_BASELINE_MATCH" in (
        result["profiles"]["LR1"]["reason_codes"]
    )
    assert "missing_profile_class:TRACK" in result["errors"]
