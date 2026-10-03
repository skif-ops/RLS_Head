import csv
import json

from tools.hil_host.r2_evidence import (
    GateConfig,
    evaluate,
    ingest_csv,
    result_dict,
)


def gate() -> GateConfig:
    return GateConfig(
        min_radar_imu_samples=4,
        min_pps_samples=4,
        radar_imu_max_abs_us=250.0,
        radar_imu_rms_us=200.0,
        pps_max_abs_us=100.0,
        pps_rms_us=75.0,
        holdover_max_abs_us=600.0,
        max_missed_events=0,
        max_monotonic_failures=0,
    )


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["kind", "value_us", "count"],
        )
        writer.writeheader()
        writer.writerows(rows)


def nominal_rows():
    rows = []

    for value in (-100.0, 50.0, 120.0, -80.0):
        rows.append(
            {"kind": "radar_imu", "value_us": value, "count": ""}
        )

    for value in (-20.0, 10.0, 30.0, -10.0):
        rows.append(
            {"kind": "pps", "value_us": value, "count": ""}
        )

    rows.append(
        {"kind": "holdover", "value_us": 120.0, "count": ""}
    )

    return rows


def test_nominal_pass(tmp_path):
    source = tmp_path / "capture.csv"
    write_rows(source, nominal_rows())

    evidence = ingest_csv(source)

    status, reasons = evaluate(evidence, gate())

    assert status == "PASS"
    assert reasons == []
    assert evidence.radar_imu.count == 4
    assert evidence.pps.count == 4


def test_radar_imu_fail(tmp_path):
    rows = nominal_rows()
    rows.append(
        {"kind": "radar_imu", "value_us": 400.0, "count": ""}
    )

    source = tmp_path / "capture.csv"
    write_rows(source, rows)

    status, reasons = evaluate(
        ingest_csv(source),
        gate(),
    )

    assert status == "FAIL"
    assert "radar_imu" in reasons


def test_capture_miss_fail(tmp_path):
    rows = nominal_rows()
    rows.append(
        {"kind": "imu_drdy_missed", "value_us": "", "count": 1}
    )

    source = tmp_path / "capture.csv"
    write_rows(source, rows)

    status, reasons = evaluate(
        ingest_csv(source),
        gate(),
    )

    assert status == "FAIL"
    assert "capture" in reasons


def test_json_result_schema(tmp_path):
    source = tmp_path / "capture.csv"
    write_rows(source, nominal_rows())

    result = result_dict(
        ingest_csv(source),
        gate(),
        source,
    )

    payload = json.dumps(result)
    restored = json.loads(payload)

    assert restored["schema"] == "HIL-R2-BENCH-EVIDENCE-001"
    assert restored["gate_status"] == "PASS"
    assert restored["radar_imu"]["count"] == 4


def test_unknown_kind_rejected(tmp_path):
    source = tmp_path / "capture.csv"

    write_rows(
        source,
        [{"kind": "unknown", "value_us": "", "count": 1}],
    )

    try:
        ingest_csv(source)
    except ValueError as exc:
        assert "unsupported kind" in str(exc)
    else:
        raise AssertionError("unknown kind accepted")
