import copy
import hashlib
import json
from pathlib import Path

from tools.ant_em_evidence import (
    evaluate_em_evidence,
    load_json,
)


MANIFEST = Path(
    "tests/fixtures/d1_em/manifest.json"
)
CONFIG = Path(
    "config/d1_map_validation_evt.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_fixture_test_ready():
    result = evaluate_em_evidence(
        manifest=load_json(MANIFEST),
        map_validation_config=CONFIG,
        repository_root=".",
    )

    assert result["schema"] == "ANT-D1-EM-EVIDENCE-001"
    assert result["status"] == "TEST_READY"
    assert result["synthetic_fixture"] is True
    assert result["map_validation"]["status"] == "DATA_READY"
    assert result["errors"] == []
    assert all(
        item["hash_ok"]
        for item in result["verified_artifacts"].values()
    )


def test_real_simulated_em_data_ready(tmp_path):
    source = load_json(MANIFEST)
    copied = copy.deepcopy(source)
    copied["synthetic_fixture"] = False
    copied["evidence_level"] = "SIMULATED_EM"

    fixture_root = Path("tests/fixtures/d1_em")

    artifacts = []

    for item in copied["artifacts"]:
        source_path = Path(item["path"])
        target = tmp_path / source_path.name
        target.write_bytes(source_path.read_bytes())
        artifacts.append(
            {
                "kind": item["kind"],
                "path": target.name,
                "sha256": sha256(target),
            }
        )

    copied["artifacts"] = artifacts

    result = evaluate_em_evidence(
        manifest=copied,
        map_validation_config=CONFIG,
        repository_root=tmp_path,
    )

    assert result["status"] == "DATA_READY"
    assert result["evidence_level"] == "SIMULATED_EM"
    assert result["synthetic_fixture"] is False
    assert result["map_validation"]["status"] == "DATA_READY"


def test_hash_mismatch_invalid(tmp_path):
    manifest = load_json(MANIFEST)
    copied = copy.deepcopy(manifest)

    fixture_root = Path("tests/fixtures/d1_em")
    artifacts = []

    for item in copied["artifacts"]:
        source_path = Path(item["path"])
        target = tmp_path / source_path.name
        target.write_bytes(source_path.read_bytes())

        artifact = {
            "kind": item["kind"],
            "path": target.name,
            "sha256": sha256(target),
        }

        if item["kind"] == "model_input":
            artifact["sha256"] = "0" * 64

        artifacts.append(artifact)

    copied["artifacts"] = artifacts
    copied["synthetic_fixture"] = False
    copied["evidence_level"] = "SIMULATED_EM"

    result = evaluate_em_evidence(
        manifest=copied,
        map_validation_config=CONFIG,
        repository_root=tmp_path,
    )

    assert result["status"] == "INVALID"
    assert "model_input:hash_mismatch" in result["errors"]


def test_non_simulation_level_holds(tmp_path):
    copied = copy.deepcopy(load_json(MANIFEST))
    copied["synthetic_fixture"] = False
    copied["evidence_level"] = "SOFTWARE_CI"

    artifacts = []

    for item in copied["artifacts"]:
        source_path = Path(item["path"])
        target = tmp_path / source_path.name
        target.write_bytes(source_path.read_bytes())
        artifacts.append(
            {
                "kind": item["kind"],
                "path": target.name,
                "sha256": sha256(target),
            }
        )

    copied["artifacts"] = artifacts

    result = evaluate_em_evidence(
        manifest=copied,
        map_validation_config=CONFIG,
        repository_root=tmp_path,
    )

    assert result["status"] == "HOLD"


def test_missing_required_frequency_fails(tmp_path):
    copied = copy.deepcopy(load_json(MANIFEST))
    copied["synthetic_fixture"] = False
    copied["evidence_level"] = "SIMULATED_EM"

    artifacts = []

    for item in copied["artifacts"]:
        source_path = Path(item["path"])
        target = tmp_path / source_path.name

        if item["kind"] == "antenna_map":
            lines = [
                line
                for line in source_path.read_text(
                    encoding="utf-8"
                ).splitlines()
                if "81000000000" not in line
            ]
            target.write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8",
            )
        else:
            target.write_bytes(
                source_path.read_bytes()
            )

        artifacts.append(
            {
                "kind": item["kind"],
                "path": target.name,
                "sha256": sha256(target),
            }
        )

    copied["artifacts"] = artifacts

    result = evaluate_em_evidence(
        manifest=copied,
        map_validation_config=CONFIG,
        repository_root=tmp_path,
    )

    assert result["status"] == "FAIL"
    assert (
        result["map_validation"]["status"]
        == "INCOMPLETE"
    )
