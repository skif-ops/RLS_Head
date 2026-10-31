from __future__ import annotations

import math
import struct

from tools.hil_host.protocol import crc32c
from tools.hil_host.targetstate import HEADER_FMT, HEADER_SIZE, MAGIC, PAYLOAD_FMT, PAYLOAD_SIZE


def build_demo_packet(sequence: int, elapsed_s: float, track_id: int) -> bytes:
    phase = elapsed_s * (0.23 + track_id * 0.03) + track_id * 1.8
    range_m = 35.0 + track_id * 28.0 + 8.0 * math.sin(phase * 0.55)
    azimuth_deg = 34.0 * math.sin(phase)
    elevation_deg = 2.0 * math.sin(phase * 0.4)
    range_rate_m_s = 4.4 * math.cos(phase * 0.55)
    azimuth_rad = math.radians(azimuth_deg)
    elevation_rad = math.radians(elevation_deg)
    horizontal = range_m * math.cos(elevation_rad)
    position = (
        horizontal * math.sin(azimuth_rad),
        horizontal * math.cos(azimuth_rad),
        range_m * math.sin(elevation_rad),
    )
    velocity = (
        range_rate_m_s * math.sin(azimuth_rad),
        range_rate_m_s * math.cos(azimuth_rad),
        0.0,
    )

    floats = [0.0] * 30
    floats[0] = range_m
    floats[1] = range_rate_m_s
    floats[2] = azimuth_deg
    floats[3] = elevation_deg
    floats[4:7] = position
    floats[7:10] = velocity
    floats[10:13] = (0.0, 0.0, 0.0)
    floats[13] = 24.0 - track_id * 2.0
    floats[14] = 0.92 - track_id * 0.06
    floats[15] = 0.95 - track_id * 0.05
    floats[16] = 18.0
    floats[17:23] = (0.16, 0.0, 0.0, 0.16, 0.0, 0.25)
    floats[23:29] = (0.25, 0.0, 0.0, 0.25, 0.0, 0.36)
    floats[29] = 12.0

    timestamp_us = int(elapsed_s * 1_000_000)
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
        track_id,
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
