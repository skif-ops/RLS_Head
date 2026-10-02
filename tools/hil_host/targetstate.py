import struct

from .protocol import crc32c

MAGIC = 0x31474C52
HEADER_SIZE = 24
PAYLOAD_SIZE = 172
PACKET_SIZE = 200

HEADER_FMT = "<IBBBBHHIII"
PAYLOAD_FMT = "<QQQIBBBBI30fIIII"

assert struct.calcsize(HEADER_FMT) == HEADER_SIZE
assert struct.calcsize(PAYLOAD_FMT) == PAYLOAD_SIZE


def decode_targetstate_v1(packet: bytes) -> dict:
    if len(packet) != PACKET_SIZE:
        raise ValueError(f"expected 200 bytes, got {len(packet)}")

    expected_crc, = struct.unpack_from("<I", packet, 196)
    actual_crc = crc32c(packet[:196])

    if actual_crc != expected_crc:
        raise ValueError("TargetState CRC mismatch")

    (
        magic,
        major,
        minor,
        message_type,
        header_flags,
        payload_len,
        header_len,
        sequence,
        source_id,
        boot_id,
    ) = struct.unpack_from(HEADER_FMT, packet, 0)

    if magic != MAGIC:
        raise ValueError("bad TargetState magic")

    if header_len != HEADER_SIZE:
        raise ValueError("bad TargetState header length")

    if payload_len != PAYLOAD_SIZE:
        raise ValueError("bad TargetState payload length")

    values = struct.unpack_from(PAYLOAD_FMT, packet, HEADER_SIZE)

    (
        measurement_timestamp_us,
        state_timestamp_us,
        publish_timestamp_us,
        track_id,
        coordinate_frame,
        track_state,
        motion_model,
        reserved0,
        validity_mask,
        *rest,
    ) = values

    floats = rest[:30]
    radar_status, fusion_status, track_flags, reserved1 = rest[30:]

    return {
        "protocol_major": major,
        "protocol_minor": minor,
        "message_type": message_type,
        "header_flags": header_flags,
        "sequence": sequence,
        "source_id": source_id,
        "boot_id": boot_id,
        "measurement_timestamp_us": measurement_timestamp_us,
        "state_timestamp_us": state_timestamp_us,
        "publish_timestamp_us": publish_timestamp_us,
        "track_id": track_id,
        "coordinate_frame": coordinate_frame,
        "track_state": track_state,
        "motion_model": motion_model,
        "reserved0": reserved0,
        "validity_mask": validity_mask,
        "range_m": floats[0],
        "range_rate_m_s": floats[1],
        "azimuth_deg": floats[2],
        "elevation_deg": floats[3],
        "position_m": tuple(floats[4:7]),
        "velocity_m_s": tuple(floats[7:10]),
        "acceleration_m_s2": tuple(floats[10:13]),
        "snr_db": floats[13],
        "track_quality": floats[14],
        "confidence": floats[15],
        "measurement_age_ms": floats[16],
        "position_cov_ut": tuple(floats[17:23]),
        "velocity_cov_ut": tuple(floats[23:29]),
        "timestamp_uncertainty_us": floats[29],
        "radar_status": radar_status,
        "fusion_status": fusion_status,
        "track_flags": track_flags,
        "reserved1": reserved1,
    }


def build_synthetic_targetstate_packet() -> bytes:
    header = struct.pack(
        HEADER_FMT,
        MAGIC,
        1,
        0,
        1,
        0,
        PAYLOAD_SIZE,
        HEADER_SIZE,
        7,
        42,
        99,
    )

    floats = [0.0] * 30
    floats[0] = 100.0
    floats[1] = 8.5
    floats[2] = 1.5
    floats[3] = -0.25
    floats[16] = 21.0
    floats[29] = 10.0

    payload = struct.pack(
        PAYLOAD_FMT,
        1_000_000,
        1_000_000,
        1_021_000,
        5,
        1,
        2,
        1,
        0,
        0x3FF,
        *floats,
        0x1234,
        0,
        0x19,
        0,
    )

    packet_without_crc = header + payload

    if len(packet_without_crc) != 196:
        raise AssertionError("unexpected TargetState pre-CRC size")

    return packet_without_crc + struct.pack("<I", crc32c(packet_without_crc))
