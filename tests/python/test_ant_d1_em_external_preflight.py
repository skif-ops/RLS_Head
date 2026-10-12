import json
from pathlib import Path

from tools.ant_d1_em_external_preflight import evaluate_preflight


def valid_manifest():
    return {
        "schema": "ANT-D1-EM-MANIFEST-001",
        "model_id": "D1-EVT",
        "model_revision": "A",
        "solver_name": "EM_SOLVER",
        "solver_version": "1.0",
        "synthetic_fixture": False,
        "evidence_level": "SIMULATED_EM",
        "artifacts": [
            {
                "kind": "solver_export",
                "path": "outputs/solver_export.txt",
                "sha256": "<FILL_AFTER_SOLVER>",
            },
            {
                "kind": "model_input",
                "path": "inputs/model.json",
                "sha256": "<FILL_AFTER_INPUT_LOCK>",
            },
            {
                "kind": "material_definition",
                "path": "inputs/material.json",
                "sha256": "<FILL_AFTER_INPUT_LOCK>",
            },
            {
                "kind": "antenna_map",
                "path": "outputs/antenna_map.csv",
                "sha256": "<FILL_AFTER_SOLVER>",
            },
        ],
    }


def setup_inputs(tmp_path: Path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "inputs" / "model.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (tmp_path / "inputs" / "material.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    cfg = tmp_path / "map_config.json"
    cfg.write_text(
        json.dumps({"schema": "TEST"}) + "\n",
        encoding="utf-8",
    )
    return cfg


def test_ready_when_inputs_exist_and_outputs_are_pending(tmp_path):
    cfg = setup_inputs(tmp_path)

    result = evaluate_preflight(
        manifest=valid_manifest(),
        repository_root=tmp_path,
        map_config=cfg,
    )

    assert result["status"] == "READY_FOR_SOLVER_EXECUTION"
    assert result["errors"] == []
    assert "output_not_generated_yet:solver_export" in result["warnings"]
    assert "output_not_generated_yet:antenna_map" in result["warnings"]


def test_missing_model_input_blocks(tmp_path):
    cfg = setup_inputs(tmp_path)
    (tmp_path / "inputs" / "model.json").unlink()

    result = evaluate_preflight(
        manifest=valid_manifest(),
        repository_root=tmp_path,
        map_config=cfg,
    )

    assert result["status"] == "BLOCKED"
    assert "missing_input_file:model_input" in result["errors"]


def test_synthetic_fixture_blocks(tmp_path):
    cfg = setup_inputs(tmp_path)
    manifest = valid_manifest()
    manifest["synthetic_fixture"] = True

    result = evaluate_preflight(
        manifest=manifest,
        repository_root=tmp_path,
        map_config=cfg,
    )

    assert "synthetic_fixture_not_false" in result["errors"]


def test_unsupported_evidence_level_blocks(tmp_path):
    cfg = setup_inputs(tmp_path)
    manifest = valid_manifest()
    manifest["evidence_level"] = "SOFTWARE_CI"

    result = evaluate_preflight(
        manifest=manifest,
        repository_root=tmp_path,
        map_config=cfg,
    )

    assert "unsupported_evidence_level" in result["errors"]


def test_unsafe_path_blocks(tmp_path):
    cfg = setup_inputs(tmp_path)
    manifest = valid_manifest()
    manifest["artifacts"][1]["path"] = "../model.json"

    result = evaluate_preflight(
        manifest=manifest,
        repository_root=tmp_path,
        map_config=cfg,
    )

    assert "unsafe_or_missing_path:model_input" in result["errors"]


def test_missing_map_config_blocks(tmp_path):
    setup_inputs(tmp_path)

    result = evaluate_preflight(
        manifest=valid_manifest(),
        repository_root=tmp_path,
        map_config=tmp_path / "missing.json",
    )

    assert "map_config_missing" in result["errors"]
