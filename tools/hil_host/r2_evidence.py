from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class ResidualStats:
    count: int = 0
    mean_us: float = 0.0
    m2_us2: float = 0.0
    min_us: float | None = None
    max_us: float | None = None
    max_abs_us: float = 0.0

    def push(self, value_us: float) -> None:
        if not math.isfinite(value_us):
            raise ValueError("non-finite residual")

        if self.count == 0:
            self.count = 1
            self.mean_us = value_us
            self.m2_us2 = 0.0
            self.min_us = value_us
            self.max_us = value_us
            self.max_abs_us = abs(value_us)
            return

        new_count = self.count + 1
        delta = value_us - self.mean_us
        self.mean_us += delta / new_count
        delta2 = value_us - self.mean_us
        self.m2_us2 += delta * delta2
        self.count = new_count

        assert self.min_us is not None
        assert self.max_us is not None

        self.min_us = min(self.min_us, value_us)
        self.max_us = max(self.max_us, value_us)
        self.max_abs_us = max(self.max_abs_us, abs(value_us))

    @property
    def rms_us(self) -> float:
        if self.count == 0:
            return math.nan

        mean_sq = self.m2_us2 / self.count + self.mean_us * self.mean_us
        return math.sqrt(max(0.0, mean_sq))

    @property
    def stddev_us(self) -> float:
        if self.count < 2:
            return math.nan

        return math.sqrt(max(0.0, self.m2_us2 / (self.count - 1)))


@dataclass
class Evidence:
    radar_imu: ResidualStats
    pps: ResidualStats

    radar_ref_events: int = 0
    imu_drdy_events: int = 0
    pps_events: int = 0

    radar_ref_missed: int = 0
    imu_drdy_missed: int = 0
    pps_missed: int = 0

    monotonic_failures: int = 0

    holdover_max_abs_us: float = 0.0

    @classmethod
    def empty(cls) -> "Evidence":
        return cls(
            radar_imu=ResidualStats(),
            pps=ResidualStats(),
        )


@dataclass(frozen=True)
class GateConfig:
    min_radar_imu_samples: int
    min_pps_samples: int

    radar_imu_max_abs_us: float
    radar_imu_rms_us: float

    pps_max_abs_us: float
    pps_rms_us: float

    holdover_max_abs_us: float

    max_missed_events: int
    max_monotonic_failures: int


def load_gate_config(path: str | Path) -> GateConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return GateConfig(**data)


def ingest_rows(rows: Iterable[dict[str, str]]) -> Evidence:
    evidence = Evidence.empty()

    for line_number, row in enumerate(rows, start=2):
        kind = (row.get("kind") or "").strip()

        if not kind:
            raise ValueError(f"line {line_number}: missing kind")

        value_text = (row.get("value_us") or "").strip()

        if kind in {"radar_imu", "pps", "holdover"}:
            if not value_text:
                raise ValueError(
                    f"line {line_number}: {kind} requires value_us"
                )

            try:
                value_us = float(value_text)
            except ValueError as exc:
                raise ValueError(
                    f"line {line_number}: invalid value_us"
                ) from exc

            if not math.isfinite(value_us):
                raise ValueError(
                    f"line {line_number}: non-finite value_us"
                )

            if kind == "radar_imu":
                evidence.radar_imu.push(value_us)
                evidence.radar_ref_events += 1
                evidence.imu_drdy_events += 1

            elif kind == "pps":
                evidence.pps.push(value_us)
                evidence.pps_events += 1

            else:
                evidence.holdover_max_abs_us = max(
                    evidence.holdover_max_abs_us,
                    abs(value_us),
                )

            continue

        count_text = (row.get("count") or "").strip() or "1"

        try:
            count = int(count_text)
        except ValueError as exc:
            raise ValueError(
                f"line {line_number}: invalid count"
            ) from exc

        if count < 0:
            raise ValueError(
                f"line {line_number}: negative count"
            )

        if kind == "radar_ref_missed":
            evidence.radar_ref_missed += count
        elif kind == "imu_drdy_missed":
            evidence.imu_drdy_missed += count
        elif kind == "pps_missed":
            evidence.pps_missed += count
        elif kind == "monotonic_failure":
            evidence.monotonic_failures += count
        else:
            raise ValueError(
                f"line {line_number}: unsupported kind {kind!r}"
            )

    return evidence


def ingest_csv(path: str | Path) -> Evidence:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        required = {"kind", "value_us", "count"}

        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        if not required.issubset(reader.fieldnames):
            raise ValueError(
                f"CSV header must include {sorted(required)}"
            )

        return ingest_rows(reader)


def evaluate(evidence: Evidence, config: GateConfig) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if (
        evidence.radar_imu.count < config.min_radar_imu_samples
        or evidence.pps.count < config.min_pps_samples
    ):
        return "INSUFFICIENT", ["sample_count"]

    if (
        evidence.radar_imu.max_abs_us > config.radar_imu_max_abs_us
        or evidence.radar_imu.rms_us > config.radar_imu_rms_us
    ):
        reasons.append("radar_imu")

    if (
        evidence.pps.max_abs_us > config.pps_max_abs_us
        or evidence.pps.rms_us > config.pps_rms_us
    ):
        reasons.append("pps")

    if evidence.holdover_max_abs_us > config.holdover_max_abs_us:
        reasons.append("holdover")

    missed = (
        evidence.radar_ref_missed
        + evidence.imu_drdy_missed
        + evidence.pps_missed
    )

    if missed > config.max_missed_events:
        reasons.append("capture")

    if evidence.monotonic_failures > config.max_monotonic_failures:
        reasons.append("monotonic_time")

    if reasons:
        return "FAIL", reasons

    return "PASS", []


def result_dict(
    evidence: Evidence,
    config: GateConfig,
    source_csv: str | Path,
) -> dict:
    status, reasons = evaluate(evidence, config)

    return {
        "schema": "HIL-R2-BENCH-EVIDENCE-001",
        "source_csv": str(source_csv),
        "gate_status": status,
        "reason_codes": reasons,
        "radar_imu": {
            **asdict(evidence.radar_imu),
            "rms_us": evidence.radar_imu.rms_us,
            "stddev_us": evidence.radar_imu.stddev_us,
        },
        "pps": {
            **asdict(evidence.pps),
            "rms_us": evidence.pps.rms_us,
            "stddev_us": evidence.pps.stddev_us,
        },
        "holdover_max_abs_us": evidence.holdover_max_abs_us,
        "missed_events": {
            "radar_ref": evidence.radar_ref_missed,
            "imu_drdy": evidence.imu_drdy_missed,
            "pps": evidence.pps_missed,
        },
        "monotonic_failures": evidence.monotonic_failures,
        "event_counts": {
            "radar_ref": evidence.radar_ref_events,
            "imu_drdy": evidence.imu_drdy_events,
            "pps": evidence.pps_events,
        },
        "gate_config": asdict(config),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate HIL-R2 timing bench evidence."
    )

    parser.add_argument("csv")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    evidence = ingest_csv(args.csv)
    config = load_gate_config(args.config)

    result = result_dict(
        evidence,
        config,
        args.csv,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(result["gate_status"])

    return 0 if result["gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
