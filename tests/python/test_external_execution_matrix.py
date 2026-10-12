from copy import deepcopy

from tools.evidence_status import load_json
from tools.external_execution_matrix import build_matrix


MANIFEST = (
    "evidence/"
    "project_evidence_manifest.json"
)


def test_matrix_materializes_every_ready_queue_item(
    tmp_path,
):
    manifest = load_json(
        MANIFEST
    )

    result = build_matrix(
        manifest,
        output_root=
            tmp_path / "jobs",
    )

    assert (
        result["schema"]
        == "EXTERNAL-EXECUTION-MATRIX-001"
    )
    assert (
        result["status"]
        == "READY"
    )
    assert (
        result["queue_depth"]
        == len(
            result["rows"]
        )
    )
    assert (
        result[
            "summary"
        ][
            "template_ready"
        ]
        == result[
            "queue_depth"
        ]
    )

    for row in result[
        "rows"
    ]:
        assert (
            row[
                "job_pack_status"
            ]
            == "TEMPLATE_READY"
        )


def test_matrix_preserves_manifest(
    tmp_path,
):
    manifest = load_json(
        MANIFEST
    )
    original = deepcopy(
        manifest
    )

    build_matrix(
        manifest,
        output_root=
            tmp_path / "jobs",
    )

    assert manifest == original


def test_matrix_reports_known_preflight_states(
    tmp_path,
):
    result = build_matrix(
        load_json(
            MANIFEST
        ),
        output_root=
            tmp_path / "jobs",
    )

    by_id = {
        row["item_id"]:
            row
        for row in result[
            "rows"
        ]
    }

    assert (
        by_id[
            "M300_MEASURED"
        ][
            "preflight_status"
        ]
        == "BLOCKED"
    )

    assert (
        by_id[
            "HIL_R2_BENCH_MEASURED"
        ][
            "preflight_status"
        ]
        == "READY_FOR_COLLECTION"
    )

    assert (
        by_id[
            "ANT_D1_EM_REAL"
        ][
            "preflight_status"
        ]
        == "BLOCKED"
    )

    assert (
        by_id[
            "REFERENCE_RANGE_MEASURED"
        ][
            "preflight_status"
        ]
        == "READY_FOR_COLLECTION"
    )

    assert (
        by_id[
            "CARRIER_REVIEW_A"
        ][
            "preflight_status"
        ]
        == "READY_FOR_CAD_REVIEW_EXECUTION"
    )

    assert (
        by_id[
            "AWR_EVM_PROFILE_MEASURED"
        ][
            "preflight_status"
        ]
        == "READY_FOR_COLLECTION"
    )
