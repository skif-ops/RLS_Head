from pathlib import Path

from tools.measurement_pack import (
    PACKS,
    build_pack,
    validate_pack,
)


def test_all_pack_kinds_generate_and_validate(tmp_path):
    for kind in sorted(PACKS):
        root = tmp_path / kind

        manifest = build_pack(
            kind,
            root,
        )

        assert manifest["schema"] == "MEASUREMENT-EXECUTION-PACK-001"
        assert manifest["kind"] == kind
        assert manifest["template_only"] is True

        result = validate_pack(root)

        assert result["schema"] == (
            "MEASUREMENT-EXECUTION-PACK-VALIDATION-001"
        )
        assert result["status"] == "TEMPLATE_READY"
        assert result["kind"] == kind
        assert result["item_id"] == PACKS[kind]["item_id"]
        assert "evidence_claim.template.json" in result["generated_files"]
        assert "pack_manifest.json" in result["generated_files"]
        assert "README.md" in result["generated_files"]


def test_m300_pack_contains_mandatory_corner(tmp_path):
    root = tmp_path / "m300"

    build_pack(
        "m300",
        root,
    )

    run_manifest = (
        root / "run_manifest.json"
    ).read_text(
        encoding="utf-8"
    )

    assert '"range_nominal_m": 300.0' in run_manifest
    assert '"rcs_m2": 0.01' in run_manifest
    assert '"synthetic_fixture": false' in run_manifest


def test_physical_antenna_pack_has_measurement_columns(
    tmp_path,
):
    root = tmp_path / "physical_antenna"

    build_pack(
        "physical_antenna",
        root,
    )

    header = (
        root / "antenna_measurement.csv"
    ).read_text(
        encoding="utf-8"
    ).splitlines()[0]

    for column in (
        "frequency_hz",
        "realized_gain_db",
        "gain_uncertainty_db",
        "sigma_az_deg",
        "sigma_el_deg",
        "ambiguity_flag",
        "track_usable",
        "high_acc_usable",
        "repeat_count",
    ):
        assert column in header


def test_sys_err_pack_has_required_spatial_columns(
    tmp_path,
):
    root = tmp_path / "sys_err"

    build_pack(
        "sys_err",
        root,
    )

    header = (
        root / "sys_err_cells.csv"
    ).read_text(
        encoding="utf-8"
    ).splitlines()[0]

    for column in (
        "range_m",
        "sigma_range_m",
        "sigma_az_deg",
        "sigma_el_deg",
        "host_attitude_sigma_deg",
        "extrinsic_sigma_deg",
        "angular_rate_deg_s",
    ):
        assert column in header


def test_pack_templates_keep_fill_placeholders(
    tmp_path,
):
    root = tmp_path / "m300"

    build_pack(
        "m300",
        root,
    )

    result = validate_pack(root)

    assert result["status"] == "TEMPLATE_READY"
    assert "run_manifest.json" in result["placeholder_files"]
    assert (
        "evidence_claim.template.json"
        in result["placeholder_files"]
    )


def test_missing_generated_file_invalid(tmp_path):
    root = tmp_path / "reference_range"

    build_pack(
        "reference_range",
        root,
    )

    (
        root / "reference_range.csv"
    ).unlink()

    result = validate_pack(root)

    assert result["status"] == "INVALID"
    assert (
        "missing_file:reference_range.csv"
        in result["errors"]
    )


def test_pack_manifest_cannot_be_reclassified_as_real(
    tmp_path,
):
    root = tmp_path / "hil_r2_bench"

    build_pack(
        "hil_r2_bench",
        root,
    )

    manifest_path = root / "pack_manifest.json"
    text = manifest_path.read_text(
        encoding="utf-8"
    ).replace(
        '"template_only": true',
        '"template_only": false',
    )

    manifest_path.write_text(
        text,
        encoding="utf-8",
    )

    result = validate_pack(root)

    assert result["status"] == "INVALID"
    assert "template_only" in result["errors"]
