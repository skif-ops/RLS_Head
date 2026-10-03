import json
from pathlib import Path

import pytest

from tools.external_evidence_ingest import ingest_bundle


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def base_bundle():
    return {
        "schema": "EXTERNAL-EVIDENCE-BUNDLE-001",
        "kind": "hil_r2_bench",
        "item_id": "HIL_R2_BENCH_MEASURED",
        "evidence_level": "MEASURED_BENCH",
        "synthetic": False,
        "result": {
            "path": "result.json",
            "schema": "HIL-R2-BENCH-EVIDENCE-001",
        },
        "artifacts": [
            {
                "kind": "timing_capture",
                "path": "timing_capture.csv",
            }
        ],
    }


def make_valid_files(tmp_path: Path):
    write_json(
        tmp_path / "result.json",
        {
            "schema": "HIL-R2-BENCH-EVIDENCE-001",
            "gate_status": "PASS",
        },
    )
    (tmp_path / "timing_capture.csv").write_text(
        "kind,value_us,count\npps,1.0,100\n",
        encoding="utf-8",
    )


def test_valid_bundle_builds_hash_verified_claim(tmp_path):
    make_valid_files(tmp_path)
    result, claim = ingest_bundle(
        base_bundle(),
        bundle_root=tmp_path,
    )

    assert result["status"] == "CANDIDATE_READY"
    assert claim is not None
    assert claim["schema"] == "MEASURED-EVIDENCE-CLAIM-001"
    assert len(claim["result"]["sha256"]) == 64
    assert len(claim["provenance"]["artifacts"][0]["sha256"]) == 64


def test_kind_item_mismatch_rejected(tmp_path):
    make_valid_files(tmp_path)
    bundle = base_bundle()
    bundle["item_id"] = "M300_MEASURED"

    result, claim = ingest_bundle(bundle, bundle_root=tmp_path)
    assert claim is None
    assert "item_id_mismatch" in result["errors"]


def test_placeholder_rejected(tmp_path):
    make_valid_files(tmp_path)
    (tmp_path / "timing_capture.csv").write_text(
        "kind,value_us,count\n<FILL>,0,0\n",
        encoding="utf-8",
    )

    result, claim = ingest_bundle(
        base_bundle(),
        bundle_root=tmp_path,
    )
    assert claim is None
    assert "artifact_contains_placeholder:0" in result["errors"]


def test_synthetic_fixture_rejected(tmp_path):
    make_valid_files(tmp_path)
    write_json(
        tmp_path / "result.json",
        {
            "schema": "HIL-R2-BENCH-EVIDENCE-001",
            "gate_status": "PASS",
            "synthetic_fixture": True,
        },
    )

    result, claim = ingest_bundle(
        base_bundle(),
        bundle_root=tmp_path,
    )
    assert claim is None
    assert (
        "result_fixture_marker:synthetic_fixture"
        in result["errors"]
    )


def test_path_escape_rejected(tmp_path):
    make_valid_files(tmp_path)
    bundle = base_bundle()
    bundle["artifacts"][0]["path"] = "../outside.csv"

    result, claim = ingest_bundle(bundle, bundle_root=tmp_path)
    assert claim is None
    assert any(
        "unsafe path" in error
        for error in result["errors"]
    )


def test_wrong_result_schema_rejected(tmp_path):
    make_valid_files(tmp_path)
    bundle = base_bundle()
    bundle["result"]["schema"] = "WRONG"

    result, claim = ingest_bundle(bundle, bundle_root=tmp_path)
    assert claim is None
    assert "result_schema_mismatch" in result["errors"]


def test_wrong_bundle_schema_raises(tmp_path):
    make_valid_files(tmp_path)
    bundle = base_bundle()
    bundle["schema"] = "WRONG"

    with pytest.raises(ValueError):
        ingest_bundle(bundle, bundle_root=tmp_path)
