from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/hil-r1.yml"


def test_workflow_does_not_treat_release_result_presence_as_authority():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert text.count(
        "production_result_path = Path("
    ) == 2
    assert text.count(
        'production_result.get("status") == "PASS"'
    ) == 2
    assert text.count(
        'production_result.get("production_authority")'
    ) == 2
    assert text.count(
        '== "AUTHORIZED"'
    ) >= 4

    forbidden = (
        'production_released = Path(\n'
        '              "hardware/system_carrier/altium/release/"\n'
        '              "production_release_result.json"\n'
        '          ).is_file()'
    )
    assert forbidden not in text
