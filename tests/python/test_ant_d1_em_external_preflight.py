from pathlib import Path

from tools.ant_d1_em_external_preflight import evaluate_preflight


def manifest():
    return {
        "schema": "ANT-D1-EM-MANIFEST-001",
        "model_id": "D1",
        "model_revision": "A",
        "solver_name": "EM_SOLVER",
        "solver_version": "1.0",
        "synthetic_fixture": False,
        "evidence_level": "SIMULATED_EM",
        "artifacts": [
            {
                "kind": "model_input",
                "path": "model/input.dat",
                "sha256": "<FILL_SHA256>",
            },
            {
                "kind": "material_definition",
                "path": "model/materials.json",
                "sha256": "<FILL_SHA256>",
            },
            {
                "kind": "solver_export",
                "path": "output/solver_export.dat",
                "sha256": "<FILL_SHA256>",
            },
            {
                "kind": "antenna_map",
                "path": "output/antenna_map.csv",
                "sha256": "<FILL_SHA256>",
            },
        ],
    }


def make_inputs(root: Path):
    (root / "model").mkdir()
    (root / "output").mkdir()
    (root / "model" / "input.dat").write_text("model\n", encoding="utf-8")
    (root / "model" / "materials.json").write_text("{}\n", encoding="utf-8")


def test_inputs_ready_outputs_missing_are_warnings(tmp_path):
    make_inputs(tmp_path)
    result = evaluate_preflight(
        manifest=manifest(),
        repository_root=tmp_path,
    )

    assert result["status"] == "READY_FOR_SOLVER_EXECUTION"
    assert result["errors"] == []
    assert "solver_export:output_not_present_yet" in result["warnings"]
    assert "antenna_map:output_not_present_yet" in result["warnings"]


def test_missing_model_input_blocks(tmp_path):
    make_inputs(tmp_path)
    (tmp_path / "model" / "input.dat").unlink()

    result = evaluate_preflight(
        manifest=manifest(),
        repository_root=tmp_path,
    )

    assert result["status"] == "BLOCKED"
    assert "model_input:missing_input_file" in result["errors"]


def test_missing_required_artifact_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    data["artifacts"] = [
        item
        for item in data["artifacts"]
        if item["kind"] != "antenna_map"
    ]

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )

    assert "missing_artifact:antenna_map" in result["errors"]


def test_synthetic_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    data["synthetic_fixture"] = True

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )

    assert "synthetic_fixture_not_false" in result["errors"]


def test_unsafe_path_blocks(tmp_path):
    make_inputs(tmp_path)
    data = manifest()
    data["artifacts"][0]["path"] = "../outside.dat"

    result = evaluate_preflight(
        manifest=data,
        repository_root=tmp_path,
    )

    assert any("unsafe_path" in error for error in result["errors"])


def test_completed_outputs_remove_missing_output_warnings(tmp_path):
    make_inputs(tmp_path)
    (tmp_path / "output" / "solver_export.dat").write_text("export\n", encoding="utf-8")
    (tmp_path / "output" / "antenna_map.csv").write_text("frequency_hz\n", encoding="utf-8")

    result = evaluate_preflight(
        manifest=manifest(),
        repository_root=tmp_path,
    )

    assert result["status"] == "READY_FOR_SOLVER_EXECUTION"
    assert "solver_export:output_not_present_yet" not in result["warnings"]
    assert "antenna_map:output_not_present_yet" not in result["warnings"]
