import hashlib
import json
from pathlib import Path

from tools.altium_production_release_gate import validate_manifest
from tools.altium_production_release_manifest import build_manifest


def _write(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(data, sort_keys=True) + "\n").encode()
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _fixture(tmp_path: Path, *, synthetic: bool = True) -> Path:
    contract = (
        tmp_path
        / "hardware/system_carrier/altium/ALTIUM_OUTJOB_CONTRACT_SYS_001.csv"
    )
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        "output_id,altium_output,type,required,scope,notes\n"
        "OUT-001,Gerber X2,FAB,YES,All,Required\n"
        "OUT-002,ODB++,FAB,OPTIONAL,All,Optional\n",
        encoding="utf-8",
    )

    drc_report = tmp_path / "release/native_drc_report.txt"
    drc_report.parent.mkdir(parents=True, exist_ok=True)
    drc_report.write_text("DRC PASS\n", encoding="utf-8")
    drc_report_hash = hashlib.sha256(drc_report.read_bytes()).hexdigest()

    gerber = tmp_path / "release/gerber_x2.zip"
    gerber.write_bytes(b"GERBER_X2")
    gerber_hash = hashlib.sha256(gerber.read_bytes()).hexdigest()

    review_evidence = {}
    for name in ("mechanical", "fabricator", "si", "dfm"):
        evidence_path = tmp_path / f"release/{name}_evidence.txt"
        evidence_path.write_text(
            f"{name} evidence\n",
            encoding="utf-8",
        )
        review_evidence[name] = {
            "path": f"release/{name}_evidence.txt",
            "sha256": hashlib.sha256(
                evidence_path.read_bytes()
            ).hexdigest(),
        }

    entries = {
        "equivalence_result": (
            "equivalence/altium_equivalence_result.json",
            {
                "schema": "ALTIUM-EQUIVALENCE-RESULT-001",
                "status": "PASS",
                "layout_authority": "AUTHORIZED",
                "production_authority": "NOT_AUTHORIZED",
                "preserve_kicad": True,
            },
        ),
        "native_drc_result": (
            "release/native_drc_result.json",
            {
                "schema": "ALTIUM-NATIVE-DRC-RESULT-001",
                "status": "PASS",
                "blocking_errors": 0,
                "unrouted_nets": 0,
                "source_report": "release/native_drc_report.txt",
                "source_report_sha256": drc_report_hash,
            },
        ),
        "mechanical_review": (
            "release/mechanical_review.json",
            {
                "schema": "ALTIUM-MECHANICAL-REVIEW-001",
                "status": "PASS",
                "board_outline_frozen": True,
                "mounting_geometry_frozen": True,
                "connector_access_verified": True,
                "step_enclosure_verified": True,
                "reviewer": "Synthetic CI",
                "evidence_refs": [review_evidence["mechanical"]],
            },
        ),
        "fabricator_binding": (
            "release/fabricator_binding.json",
            {
                "schema": "ALTIUM-FABRICATOR-BINDING-001",
                "status": "PASS",
                "stackup_bound": True,
                "copper_weight_bound": True,
                "impedance_50r_bound": True,
                "impedance_100r_bound": True,
                "min_trace_clearance_bound": True,
                "via_rules_bound": True,
                "fabricator": "Synthetic Fab",
                "evidence_refs": [review_evidence["fabricator"]],
            },
        ),
        "return_path_si_review": (
            "release/return_path_si_review.json",
            {
                "schema": "ALTIUM-RETURN-PATH-SI-REVIEW-001",
                "status": "PASS",
                "p0_open_findings": 0,
                "l2_ground_continuity_verified": True,
                "timing_return_paths_verified": True,
                "ethernet_mdi_return_path_verified": True,
                "reviewer": "Synthetic CI",
                "evidence_refs": [review_evidence["si"]],
            },
        ),
        "dfm_result": (
            "release/dfm_result.json",
            {
                "schema": "ALTIUM-DFM-RESULT-001",
                "status": "PASS",
                "p0_open_items": 0,
                "evidence_refs": [review_evidence["dfm"]],
            },
        ),
        "outjob_release_manifest": (
            "release/outjob_release_manifest.json",
            {
                "schema": "ALTIUM-OUTJOB-RELEASE-MANIFEST-001",
                "status": "PASS",
                "required_outputs_complete": True,
                "source_is_native_altium": True,
                "outputs": [
                    {
                        "output_id": "OUT-001",
                        "path": "release/gerber_x2.zip",
                        "sha256": gerber_hash,
                    }
                ],
            },
        ),
    }

    artifacts = []
    for artifact_id, (relative, payload) in entries.items():
        digest = _write(tmp_path / relative, payload)
        artifacts.append(
            {
                "id": artifact_id,
                "path": relative,
                "sha256": digest,
            }
        )

    manifest = {
        "schema": "ALTIUM-PRODUCTION-RELEASE-MANIFEST-001",
        "board_id": "EVT-SYS-CARRIER",
        "hardware_revision": "A",
        "primary_cad": "Altium Designer",
        "synthetic_fixture": synthetic,
        "evidence_level": (
            "SOFTWARE_CI"
            if synthetic
            else "NATIVE_ALTIUM_RELEASE"
        ),
        "artifacts": artifacts,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def test_synthetic_release_fixture_is_test_ready(tmp_path):
    manifest = _fixture(tmp_path)
    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "TEST_READY"
    assert result["errors"] == []
    assert result["reason_codes"] == []
    assert result["layout_authority"] == "AUTHORIZED"
    assert result["production_authority"] == "NOT_AUTHORIZED"


def test_native_release_pass_authorizes_production(tmp_path):
    manifest = _fixture(tmp_path, synthetic=False)
    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "PASS"
    assert result["production_authority"] == "AUTHORIZED"


def test_drc_error_blocks_release(tmp_path):
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text())
    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "native_drc_result"
    )
    path = tmp_path / item["path"]
    payload = json.loads(path.read_text())
    payload["blocking_errors"] = 1
    item["sha256"] = _write(path, payload)
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "FAIL"
    assert "DRC_BLOCKING_ERRORS" in result["reason_codes"]


def test_open_dfm_p0_blocks_release(tmp_path):
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text())
    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "dfm_result"
    )
    path = tmp_path / item["path"]
    payload = json.loads(path.read_text())
    payload["p0_open_items"] = 1
    item["sha256"] = _write(path, payload)
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "FAIL"
    assert "DFM_P0_OPEN_ITEMS" in result["reason_codes"]


def test_manifest_builder_hashes_exact_release_evidence(tmp_path):
    template = _fixture(tmp_path)
    template_data = json.loads(template.read_text())
    for item in template_data["artifacts"]:
        item["sha256"] = "<SHA256>"
    template.write_text(
        json.dumps(template_data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = build_manifest(
        template_path=template,
        repository_root=tmp_path,
    )

    assert result["status"] == "READY"
    assert result["errors"] == []
    assert all(
        len(item["sha256"]) == 64
        for item in result["manifest"]["artifacts"]
    )



def test_changed_review_evidence_hash_blocks_release(tmp_path):
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text())

    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "mechanical_review"
    )
    review_path = tmp_path / item["path"]
    review = json.loads(review_path.read_text())
    evidence_path = tmp_path / review["evidence_refs"][0]["path"]
    evidence_path.write_text("changed evidence\n", encoding="utf-8")

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "INVALID"
    assert any(
        error.startswith("mechanical_evidence_ref_hash:")
        for error in result["errors"]
    )



def test_pending_null_numeric_evidence_fails_closed(tmp_path):
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text())

    item = next(
        artifact
        for artifact in data["artifacts"]
        if artifact["id"] == "native_drc_result"
    )
    path = tmp_path / item["path"]
    payload = json.loads(path.read_text())
    payload["status"] = "PENDING"
    payload["blocking_errors"] = None
    payload["unrouted_nets"] = None
    item["sha256"] = _write(path, payload)
    manifest.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    result = validate_manifest(manifest, tmp_path)

    assert result["status"] == "FAIL"
    assert "NATIVE_DRC_RESULT_NOT_PASS" in result["reason_codes"]
    assert "DRC_BLOCKING_ERRORS" in result["reason_codes"]
    assert "UNROUTED_NETS" in result["reason_codes"]
