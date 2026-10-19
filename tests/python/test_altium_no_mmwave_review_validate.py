import hashlib
import json
from pathlib import Path

from tools.altium_no_mmwave_review_validate import validate


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, routing_ok: bool = True) -> tuple[Path, Path, Path, Path]:
    pcb = tmp_path / "EVT_SYS_CARRIER.PcbDoc"
    pcb.write_bytes(b"NATIVE_PCB")

    components = tmp_path / "component_inventory.csv"
    components.write_text(
        "designator,pattern,x_mil,y_mil\nU1,LQFP,0,0\n",
        encoding="utf-8",
    )
    nets = tmp_path / "net_inventory.csv"
    nets.write_text("net_name\nGNSS_RF\n3V3\n", encoding="utf-8")

    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "schema": "ALTIUM-NO-MMWAVE-REVIEW-001",
                "status": "PASS",
                "reviewer": "Review A",
                "no_76_81ghz_components": True,
                "no_76_81ghz_nets": True,
                "no_76_81ghz_routing": routing_ok,
                "no_76_81ghz_antenna": True,
                "input_sha256": {
                    "pcb": _sha(pcb),
                    "component_inventory": _sha(components),
                    "net_inventory": _sha(nets),
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return review, pcb, components, nets


def test_no_mmwave_review_passes_when_bound_to_exact_native_evidence(tmp_path):
    review, pcb, components, nets = _fixture(tmp_path)

    result = validate(
        review_json=review,
        pcb_path=pcb,
        component_inventory=components,
        net_inventory=nets,
    )

    assert result["status"] == "PASS"
    assert (
        result["verified_checks"]["no_76_81GHz_rf_on_system_carrier"]
        == "PASS"
    )
    assert result["input_sha256"]["review"] == _sha(review)


def test_no_mmwave_review_detects_changed_pcb(tmp_path):
    review, pcb, components, nets = _fixture(tmp_path)
    pcb.write_bytes(b"CHANGED_PCB")

    result = validate(
        review_json=review,
        pcb_path=pcb,
        component_inventory=components,
        net_inventory=nets,
    )

    assert result["status"] == "FAIL"
    assert "hash_mismatch:pcb" in result["errors"]


def test_no_mmwave_review_requires_explicit_routing_review(tmp_path):
    review, pcb, components, nets = _fixture(
        tmp_path,
        routing_ok=False,
    )

    result = validate(
        review_json=review,
        pcb_path=pcb,
        component_inventory=components,
        net_inventory=nets,
    )

    assert result["status"] == "FAIL"
    assert "NO_76_81GHZ_ROUTING" in result["reason_codes"]
