import json
from pathlib import Path

from tools.reference_range_external_preflight import evaluate_preflight


def write_csv(path: Path, body: str = ""):
    path.write_text(
        "run_id,range_m,signal_db,detector_margin_db,detected,track_valid\n"
        + body,
        encoding="utf-8",
    )


def write_manifest(path: Path, range_m: int):
    path.write_text(
        json.dumps(
            {
                "schema": "EVM-RUN-MANIFEST-001",
                "run_id": f"R{range_m}",
                "mode": "QUALIFY",
                "profile_id": "TRACK",
                "profile_config_sha256": "a" * 64,
                "source_commit": "b" * 40,
                "target_id": "REF",
                "range_nominal_m": float(range_m),
                "rcs_m2": 0.01,
                "start_time_us": 1,
                "end_time_us": 2,
                "truth_status": "VALID",
                "time_alignment_valid": True,
                "config_locked": True,
                "evidence_level": "MEASURED_EVM",
                "synthetic_fixture": False,
                "files": [],
            }
        ) + "\n",
        encoding="utf-8",
    )


def test_empty_campaign_is_structurally_ready_with_warnings(tmp_path):
    csv_path = tmp_path / "reference_range.csv"
    write_csv(csv_path)
    manifests = tmp_path / "manifests"
    manifests.mkdir()

    result = evaluate_preflight(
        reference_csv=csv_path,
        manifest_dir=manifests,
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert "reference_csv_has_no_samples" in result["warnings"]
    assert any(w.startswith("missing_range_manifests:") for w in result["warnings"])


def test_complete_manifest_ladder_ready(tmp_path):
    csv_path = tmp_path / "reference_range.csv"
    write_csv(csv_path)
    manifests = tmp_path / "manifests"
    manifests.mkdir()

    for r in (50, 100, 150, 200, 250, 300):
        write_manifest(manifests / f"r{r}.json", r)

    result = evaluate_preflight(
        reference_csv=csv_path,
        manifest_dir=manifests,
    )

    assert result["status"] == "READY_FOR_COLLECTION"
    assert result["manifest_ranges_present_m"] == [50, 100, 150, 200, 250, 300]


def test_bad_manifest_blocks(tmp_path):
    csv_path = tmp_path / "reference_range.csv"
    write_csv(csv_path)
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "bad.json").write_text("{bad", encoding="utf-8")

    result = evaluate_preflight(
        reference_csv=csv_path,
        manifest_dir=manifests,
    )

    assert result["status"] == "BLOCKED"
    assert "invalid_manifest_json:bad.json" in result["errors"]


def test_wrong_csv_header_blocks(tmp_path):
    csv_path = tmp_path / "reference_range.csv"
    csv_path.write_text("bad,header\n", encoding="utf-8")
    manifests = tmp_path / "manifests"
    manifests.mkdir()

    result = evaluate_preflight(
        reference_csv=csv_path,
        manifest_dir=manifests,
    )

    assert result["status"] == "BLOCKED"
    assert "reference_csv_header" in result["errors"]


def test_missing_manifest_dir_blocks(tmp_path):
    csv_path = tmp_path / "reference_range.csv"
    write_csv(csv_path)

    result = evaluate_preflight(
        reference_csv=csv_path,
        manifest_dir=tmp_path / "missing",
    )

    assert result["status"] == "BLOCKED"
    assert "manifest_dir_missing" in result["errors"]
