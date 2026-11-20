from __future__ import annotations

import json
import math
import random
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.hil_host.protocol import crc32c
from tools.hil_host.targetstate import HEADER_FMT, HEADER_SIZE, MAGIC, PAYLOAD_FMT, PAYLOAD_SIZE


SCENARIO_VERSION = 1
MAX_TARGETS = 16
REFERENCE_RCS_M2 = 0.01
REFERENCE_RANGE_M = 300.0
REFERENCE_SNR_DB = 12.0
MANEUVERS = ("straight", "weave", "circle")


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name}: требуется конечное число")
    return value


def _bounded(value: float, lower: float, upper: float, name: str) -> float:
    value = _finite(value, name)
    if not lower <= value <= upper:
        raise ValueError(f"{name}: допустимый диапазон {lower:g}..{upper:g}")
    return value


@dataclass
class TargetConfig:
    track_id: int
    name: str
    enabled: bool = True
    rcs_m2: float = 0.01
    speed_kmh: float = 160.0
    initial_range_m: float = 300.0
    initial_azimuth_deg: float = 0.0
    initial_elevation_deg: float = 0.0
    course_deg: float = 180.0
    vertical_speed_m_s: float = 0.0
    maneuver: str = "straight"
    maneuver_amplitude_deg: float = 10.0
    maneuver_period_s: float = 8.0

    def validate(self, maximum_range_m: float) -> None:
        if not 1 <= int(self.track_id) <= 65535:
            raise ValueError("ID объекта: допустимый диапазон 1..65535")
        if not self.name.strip():
            raise ValueError(f"Объект {self.track_id}: имя не задано")
        self.rcs_m2 = _bounded(self.rcs_m2, 0.0001, 100.0, f"ЭПР объекта {self.track_id}, м2")
        self.speed_kmh = _bounded(self.speed_kmh, 1.0, 1500.0, f"Скорость объекта {self.track_id}, км/ч")
        self.initial_range_m = _bounded(
            self.initial_range_m,
            5.0,
            maximum_range_m,
            f"Начальная дальность объекта {self.track_id}, м",
        )
        self.initial_azimuth_deg = _bounded(
            self.initial_azimuth_deg,
            -180.0,
            180.0,
            f"Азимут объекта {self.track_id}, град",
        )
        self.initial_elevation_deg = _bounded(
            self.initial_elevation_deg,
            -60.0,
            60.0,
            f"Угол места объекта {self.track_id}, град",
        )
        self.course_deg = _bounded(self.course_deg, -180.0, 180.0, f"Курс объекта {self.track_id}, град")
        self.vertical_speed_m_s = _bounded(
            self.vertical_speed_m_s,
            -100.0,
            100.0,
            f"Вертикальная скорость объекта {self.track_id}, м/с",
        )
        if self.maneuver not in MANEUVERS:
            raise ValueError(f"Объект {self.track_id}: неизвестный маневр {self.maneuver}")
        self.maneuver_amplitude_deg = _bounded(
            self.maneuver_amplitude_deg,
            0.0,
            90.0,
            f"Амплитуда маневра объекта {self.track_id}, град",
        )
        self.maneuver_period_s = _bounded(
            self.maneuver_period_s,
            1.0,
            600.0,
            f"Период маневра объекта {self.track_id}, с",
        )

    @classmethod
    def from_dict(cls, value: dict) -> "TargetConfig":
        return cls(**value)


@dataclass
class Scenario:
    name: str = "Три объекта с разной ЭПР"
    update_hz: float = 12.5
    maximum_range_m: float = 3000.0
    range_noise_m: float = 0.35
    angle_noise_deg: float = 0.08
    snr_noise_db: float = 0.25
    random_seed: int = 216
    loop_targets: bool = True
    targets: list[TargetConfig] = field(default_factory=list)
    scenario_version: int = SCENARIO_VERSION

    def validate(self) -> None:
        if int(self.scenario_version) != SCENARIO_VERSION:
            raise ValueError(f"Неподдерживаемая версия сценария {self.scenario_version}")
        if not self.name.strip():
            raise ValueError("Имя сценария не задано")
        self.update_hz = _bounded(self.update_hz, 1.0, 50.0, "Частота обновления, Гц")
        self.maximum_range_m = _bounded(self.maximum_range_m, 100.0, 10000.0, "Максимальная дальность, м")
        self.range_noise_m = _bounded(self.range_noise_m, 0.0, 100.0, "СКО шума дальности, м")
        self.angle_noise_deg = _bounded(self.angle_noise_deg, 0.0, 10.0, "СКО углового шума, град")
        self.snr_noise_db = _bounded(self.snr_noise_db, 0.0, 20.0, "СКО шума SNR, дБ")
        if not 1 <= len(self.targets) <= MAX_TARGETS:
            raise ValueError(f"Сценарий должен содержать от 1 до {MAX_TARGETS} объектов")
        identifiers = set()
        for target in self.targets:
            target.validate(self.maximum_range_m)
            if target.track_id in identifiers:
                raise ValueError(f"Повторяется ID объекта {target.track_id}")
            identifiers.add(target.track_id)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "Scenario":
        raw = dict(value)
        raw["targets"] = [TargetConfig.from_dict(item) for item in raw.get("targets", [])]
        scenario = cls(**raw)
        scenario.validate()
        return scenario

    @classmethod
    def load(cls, path: Path) -> "Scenario":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))

    def save(self, path: Path) -> None:
        self.validate()
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class TwinSample:
    elapsed_s: float
    track_id: int
    name: str
    rcs_m2: float
    full_speed_kmh: float
    range_m: float
    range_rate_m_s: float
    azimuth_deg: float
    elevation_deg: float
    snr_db: float
    quality: float
    confidence: float
    packet: bytes

    def as_event(self) -> dict:
        result = asdict(self)
        result.pop("packet")
        return result


class _TargetRuntime:
    def __init__(self, config: TargetConfig) -> None:
        self.config = config
        self.elapsed_s = 0.0
        self.position_m = (0.0, 0.0, 0.0)
        self.velocity_m_s = (0.0, 0.0, 0.0)
        self._reset_position()

    def _reset_position(self) -> None:
        elevation = math.radians(self.config.initial_elevation_deg)
        azimuth = math.radians(self.config.initial_azimuth_deg)
        horizontal = self.config.initial_range_m * math.cos(elevation)
        self.position_m = (
            horizontal * math.sin(azimuth),
            horizontal * math.cos(azimuth),
            self.config.initial_range_m * math.sin(elevation),
        )
        self.velocity_m_s = (0.0, 0.0, self.config.vertical_speed_m_s)

    def step(self, dt_s: float, maximum_range_m: float, loop_targets: bool) -> tuple:
        self.elapsed_s += dt_s
        previous_velocity = self.velocity_m_s
        phase = 2.0 * math.pi * self.elapsed_s / self.config.maneuver_period_s
        if self.config.maneuver == "weave":
            course_deg = self.config.course_deg + self.config.maneuver_amplitude_deg * math.sin(phase)
        elif self.config.maneuver == "circle":
            course_deg = self.config.course_deg + math.degrees(phase)
        else:
            course_deg = self.config.course_deg

        speed_m_s = self.config.speed_kmh / 3.6
        vertical_speed = max(-speed_m_s, min(speed_m_s, self.config.vertical_speed_m_s))
        horizontal_speed = math.sqrt(max(0.0, speed_m_s * speed_m_s - vertical_speed * vertical_speed))
        course = math.radians(course_deg)
        velocity = (
            horizontal_speed * math.sin(course),
            horizontal_speed * math.cos(course),
            vertical_speed,
        )
        position = tuple(self.position_m[index] + velocity[index] * dt_s for index in range(3))
        acceleration = tuple((velocity[index] - previous_velocity[index]) / dt_s for index in range(3))
        self.position_m = position
        self.velocity_m_s = velocity

        distance = math.sqrt(sum(value * value for value in position))
        if loop_targets and (distance < 5.0 or distance > maximum_range_m or position[2] < -maximum_range_m):
            self._reset_position()
            position = self.position_m
            velocity = self.velocity_m_s
            acceleration = (0.0, 0.0, 0.0)
        return position, velocity, acceleration


class TwinEngine:
    def __init__(self, scenario: Scenario) -> None:
        scenario.validate()
        self.scenario = scenario
        self.elapsed_s = 0.0
        self.sequence = 1
        self.random = random.Random(int(scenario.random_seed))
        self.runtime = {target.track_id: _TargetRuntime(target) for target in scenario.targets}

    @staticmethod
    def rcs_gain_db(rcs_m2: float) -> float:
        if rcs_m2 <= 0.0:
            raise ValueError("ЭПР должна быть положительной")
        return 10.0 * math.log10(rcs_m2 / REFERENCE_RCS_M2)

    @staticmethod
    def _logistic(value: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, value))))

    def step(self, dt_s: float | None = None) -> list[TwinSample]:
        dt_s = 1.0 / self.scenario.update_hz if dt_s is None else _bounded(dt_s, 0.001, 1.0, "Шаг модели, с")
        self.elapsed_s += dt_s
        samples = []
        for target in self.scenario.targets:
            if not target.enabled:
                continue
            runtime = self.runtime[target.track_id]
            position, velocity, acceleration = runtime.step(
                dt_s,
                self.scenario.maximum_range_m,
                self.scenario.loop_targets,
            )
            samples.append(self._sample(target, position, velocity, acceleration))
        return samples

    def _sample(self, target: TargetConfig, position: tuple, velocity: tuple, acceleration: tuple) -> TwinSample:
        true_range = max(0.001, math.sqrt(sum(value * value for value in position)))
        true_azimuth = math.degrees(math.atan2(position[0], position[1]))
        true_elevation = math.degrees(math.asin(max(-1.0, min(1.0, position[2] / true_range))))
        measured_range = max(0.0, true_range + self.random.gauss(0.0, self.scenario.range_noise_m))
        measured_azimuth = true_azimuth + self.random.gauss(0.0, self.scenario.angle_noise_deg)
        measured_elevation = true_elevation + self.random.gauss(0.0, self.scenario.angle_noise_deg)
        range_rate = sum(position[index] * velocity[index] for index in range(3)) / true_range
        snr_db = (
            REFERENCE_SNR_DB
            + self.rcs_gain_db(target.rcs_m2)
            - 40.0 * math.log10(max(true_range, 1.0) / REFERENCE_RANGE_M)
            + self.random.gauss(0.0, self.scenario.snr_noise_db)
        )
        snr_db = max(-30.0, min(70.0, snr_db))
        quality = self._logistic((snr_db - 3.0) / 5.0)
        confidence = self._logistic((snr_db - 1.0) / 4.0)
        packet = self._build_packet(
            target,
            position,
            velocity,
            acceleration,
            measured_range,
            range_rate,
            measured_azimuth,
            measured_elevation,
            snr_db,
            quality,
            confidence,
        )
        sample = TwinSample(
            elapsed_s=self.elapsed_s,
            track_id=target.track_id,
            name=target.name,
            rcs_m2=target.rcs_m2,
            full_speed_kmh=math.sqrt(sum(value * value for value in velocity)) * 3.6,
            range_m=measured_range,
            range_rate_m_s=range_rate,
            azimuth_deg=measured_azimuth,
            elevation_deg=measured_elevation,
            snr_db=snr_db,
            quality=quality,
            confidence=confidence,
            packet=packet,
        )
        self.sequence = (self.sequence + 1) & 0xFFFFFFFF
        return sample

    def _build_packet(
        self,
        target: TargetConfig,
        position: tuple,
        velocity: tuple,
        acceleration: tuple,
        range_m: float,
        range_rate_m_s: float,
        azimuth_deg: float,
        elevation_deg: float,
        snr_db: float,
        quality: float,
        confidence: float,
    ) -> bytes:
        floats = [0.0] * 30
        floats[0] = range_m
        floats[1] = range_rate_m_s
        floats[2] = azimuth_deg
        floats[3] = elevation_deg
        floats[4:7] = position
        floats[7:10] = velocity
        floats[10:13] = acceleration
        floats[13] = snr_db
        floats[14] = quality
        floats[15] = confidence
        floats[16] = 1000.0 / self.scenario.update_hz
        position_variance = max(0.01, self.scenario.range_noise_m ** 2)
        angle_variance = max(1.0e-6, math.radians(self.scenario.angle_noise_deg) ** 2)
        floats[17:23] = (position_variance, 0.0, 0.0, position_variance, 0.0, angle_variance)
        velocity_variance = max(0.04, position_variance * self.scenario.update_hz)
        floats[23:29] = (velocity_variance, 0.0, 0.0, velocity_variance, 0.0, velocity_variance)
        floats[29] = 12.0

        timestamp_us = int(self.elapsed_s * 1_000_000)
        header = struct.pack(
            HEADER_FMT,
            MAGIC,
            1,
            0,
            1,
            0,
            PAYLOAD_SIZE,
            HEADER_SIZE,
            self.sequence,
            0x45565402,
            int(self.scenario.random_seed) & 0xFFFFFFFF,
        )
        payload = struct.pack(
            PAYLOAD_FMT,
            timestamp_us,
            timestamp_us,
            timestamp_us + int(1_000_000 / self.scenario.update_hz),
            int(target.track_id),
            1,
            2,
            {"straight": 1, "weave": 2, "circle": 3}[target.maneuver],
            0,
            0x3FF,
            *floats,
            0,
            0,
            0x01,
            0,
        )
        packet = header + payload
        return packet + struct.pack("<I", crc32c(packet))


def default_scenario() -> Scenario:
    scenario = Scenario(
        targets=[
            TargetConfig(1, "Малая ЭПР", True, 0.01, 130.0, 350.0, -25.0, 2.0, 165.0, 0.0, "straight", 0.0, 10.0),
            TargetConfig(2, "Средняя ЭПР", True, 0.10, 160.0, 500.0, 0.0, 5.0, 180.0, 1.0, "weave", 12.0, 9.0),
            TargetConfig(3, "Большая ЭПР", True, 1.00, 190.0, 700.0, 28.0, 8.0, -165.0, -1.0, "circle", 0.0, 24.0),
        ]
    )
    scenario.validate()
    return scenario
