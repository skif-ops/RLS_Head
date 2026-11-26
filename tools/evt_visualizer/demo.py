from __future__ import annotations

import math
import struct
from dataclasses import asdict, dataclass

from tools.hil_host.protocol import crc32c
from tools.hil_host.targetstate import HEADER_FMT, HEADER_SIZE, MAGIC, PAYLOAD_FMT, PAYLOAD_SIZE


MIN_TARGET_SPEED_KM_H = 130.0
MAX_TARGET_SPEED_KM_H = 190.0
MOUNT_NATURAL_FREQUENCY_HZ = 8.0
MOUNT_DAMPING_RATIO = 0.70
COMMAND_BANDWIDTH_HZ = 1.5
MOUNT_MAX_RATE_DEG_S = 90.0
MOUNT_MAX_ACCEL_DEG_S2 = 180.0


@dataclass(frozen=True)
class TrackingTwinState:
    elapsed_s: float
    range_m: float
    range_rate_m_s: float
    azimuth_deg: float
    elevation_deg: float
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]
    acceleration_m_s2: tuple[float, float, float]
    full_speed_km_h: float
    mount_command_azimuth_deg: float
    mount_actual_azimuth_deg: float
    mount_rate_deg_s: float
    mount_error_deg: float
    mount_natural_frequency_hz: float
    command_bandwidth_hz: float
    resonance_margin: float
    model_status: str

    def as_event(self) -> dict:
        return asdict(self)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


class TrackingTwin:
    """One-target tracking scene with a provisional two-stage radar-mount model."""

    def __init__(self) -> None:
        self.elapsed_s = 0.0
        self.orbit_angle_rad = -1.2
        self.mount_angle_deg = 0.0
        self.mount_rate_deg_s = 0.0

    def step(self, dt_s: float) -> TrackingTwinState:
        if dt_s <= 0.0:
            raise ValueError("dt_s must be positive")
        remaining = dt_s
        state = None
        while remaining > 1.0e-9:
            step_s = min(remaining, 0.002)
            state = self._substep(step_s)
            remaining -= step_s
        return state

    def _substep(self, dt_s: float) -> TrackingTwinState:
        self.elapsed_s += dt_s
        speed_mid = (MIN_TARGET_SPEED_KM_H + MAX_TARGET_SPEED_KM_H) / 7.2
        speed_amplitude = (MAX_TARGET_SPEED_KM_H - MIN_TARGET_SPEED_KM_H) / 7.2
        speed_frequency_rad_s = 0.22
        speed_m_s = speed_mid + speed_amplitude * math.sin(speed_frequency_rad_s * self.elapsed_s)
        tangential_accel_m_s2 = speed_amplitude * speed_frequency_rad_s * math.cos(
            speed_frequency_rad_s * self.elapsed_s
        )

        orbit_radius_m = 70.0
        orbit_center_y_m = 220.0
        orbit_rate_rad_s = speed_m_s / orbit_radius_m
        self.orbit_angle_rad += orbit_rate_rad_s * dt_s

        sin_angle = math.sin(self.orbit_angle_rad)
        cos_angle = math.cos(self.orbit_angle_rad)
        x_m = orbit_radius_m * sin_angle
        y_m = orbit_center_y_m + orbit_radius_m * cos_angle
        vx_m_s = speed_m_s * cos_angle
        vy_m_s = -speed_m_s * sin_angle
        ax_m_s2 = tangential_accel_m_s2 * cos_angle - speed_m_s * orbit_rate_rad_s * sin_angle
        ay_m_s2 = -tangential_accel_m_s2 * sin_angle - speed_m_s * orbit_rate_rad_s * cos_angle
        range_m = math.hypot(x_m, y_m)
        range_rate_m_s = (x_m * vx_m_s + y_m * vy_m_s) / range_m
        azimuth_deg = math.degrees(math.atan2(x_m, y_m))

        mount_omega = 2.0 * math.pi * MOUNT_NATURAL_FREQUENCY_HZ
        mount_accel_deg_s2 = (
            mount_omega * mount_omega * (azimuth_deg - self.mount_angle_deg)
            - 2.0 * MOUNT_DAMPING_RATIO * mount_omega * self.mount_rate_deg_s
        )
        mount_accel_deg_s2 = _clamp(
            mount_accel_deg_s2,
            -MOUNT_MAX_ACCEL_DEG_S2,
            MOUNT_MAX_ACCEL_DEG_S2,
        )
        self.mount_rate_deg_s = _clamp(
            self.mount_rate_deg_s + mount_accel_deg_s2 * dt_s,
            -MOUNT_MAX_RATE_DEG_S,
            MOUNT_MAX_RATE_DEG_S,
        )
        self.mount_angle_deg += self.mount_rate_deg_s * dt_s

        return TrackingTwinState(
            elapsed_s=self.elapsed_s,
            range_m=range_m,
            range_rate_m_s=range_rate_m_s,
            azimuth_deg=azimuth_deg,
            elevation_deg=0.0,
            position_m=(x_m, y_m, 0.0),
            velocity_m_s=(vx_m_s, vy_m_s, 0.0),
            acceleration_m_s2=(ax_m_s2, ay_m_s2, 0.0),
            full_speed_km_h=speed_m_s * 3.6,
            mount_command_azimuth_deg=azimuth_deg,
            mount_actual_azimuth_deg=self.mount_angle_deg,
            mount_rate_deg_s=self.mount_rate_deg_s,
            mount_error_deg=azimuth_deg - self.mount_angle_deg,
            mount_natural_frequency_hz=MOUNT_NATURAL_FREQUENCY_HZ,
            command_bandwidth_hz=COMMAND_BANDWIDTH_HZ,
            resonance_margin=MOUNT_NATURAL_FREQUENCY_HZ / COMMAND_BANDWIDTH_HZ,
            model_status="ПРЕДВАРИТЕЛЬНАЯ МЕХАНИЧЕСКАЯ МОДЕЛЬ",
        )


def state_at(elapsed_s: float) -> TrackingTwinState:
    twin = TrackingTwin()
    remaining = max(elapsed_s, 0.08)
    state = None
    while remaining > 1.0e-9:
        step_s = min(remaining, 0.08)
        state = twin.step(step_s)
        remaining -= step_s
    return state


def build_tracking_packet(sequence: int, state: TrackingTwinState) -> bytes:
    floats = [0.0] * 30
    floats[0] = state.range_m
    floats[1] = state.range_rate_m_s
    floats[2] = state.azimuth_deg
    floats[3] = state.elevation_deg
    floats[4:7] = state.position_m
    floats[7:10] = state.velocity_m_s
    floats[10:13] = state.acceleration_m_s2
    floats[13] = 24.0
    floats[14] = 0.90
    floats[15] = 0.94
    floats[16] = 18.0
    floats[17:23] = (0.16, 0.0, 0.0, 0.16, 0.0, 0.25)
    floats[23:29] = (0.25, 0.0, 0.0, 0.25, 0.0, 0.36)
    floats[29] = 12.0

    timestamp_us = int(state.elapsed_s * 1_000_000)
    header = struct.pack(
        HEADER_FMT,
        MAGIC,
        1,
        0,
        1,
        0,
        PAYLOAD_SIZE,
        HEADER_SIZE,
        sequence,
        1,
        0x45565401,
    )
    payload = struct.pack(
        PAYLOAD_FMT,
        timestamp_us,
        timestamp_us,
        timestamp_us + 18_000,
        1,
        1,
        2,
        1,
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


def build_demo_packet(sequence: int, elapsed_s: float, track_id: int = 1) -> bytes:
    if track_id != 1:
        raise ValueError("the tracking digital twin contains exactly one target")
    return build_tracking_packet(sequence, state_at(elapsed_s))
