import math
import struct

HIL_MAGIC = 0x31445248
HIL_MAJOR = 1
HIL_MINOR = 0

HEADER_SIZE = 32
DETECTION_SIZE = 104
CRC_SIZE = 4

VALID_ALL = 0x7F


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF

    for value in data:
        crc ^= value

        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x82F63B78
            else:
                crc >>= 1

    return (~crc) & 0xFFFFFFFF


def encode_detection(detection: dict) -> bytes:
    covariance = detection["covariance"]

    if len(covariance) != 16:
        raise ValueError("covariance must have 16 entries")

    numeric = [
        detection["range_m"],
        detection["range_rate_m_s"],
        detection["azimuth_rad"],
        detection["elevation_rad"],
        *covariance,
        detection["snr_db"],
        detection["quality"],
        detection["timestamp_uncertainty_us"],
    ]

    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("non-finite detection value")

    payload = struct.pack(
        "<I4f16f3fII",
        detection["detection_id"],
        detection["range_m"],
        detection["range_rate_m_s"],
        detection["azimuth_rad"],
        detection["elevation_rad"],
        *covariance,
        detection["snr_db"],
        detection["quality"],
        detection["timestamp_uncertainty_us"],
        detection["validity_flags"],
        detection["radar_flags"],
    )

    if len(payload) != DETECTION_SIZE:
        raise AssertionError("unexpected detection wire size")

    return payload


def encode_hil_frame(
    *,
    sequence: int,
    frame_id: int,
    measurement_time_us: int,
    detections: list[dict],
    flags: int = 0,
) -> bytes:
    payload = b"".join(encode_detection(d) for d in detections)

    header = struct.pack(
        "<IHHIIQHHI",
        HIL_MAGIC,
        HIL_MAJOR,
        HIL_MINOR,
        sequence,
        frame_id,
        measurement_time_us,
        len(detections),
        flags,
        len(payload),
    )

    if len(header) != HEADER_SIZE:
        raise AssertionError("unexpected HIL header size")

    packet_without_crc = header + payload
    return packet_without_crc + struct.pack("<I", crc32c(packet_without_crc))


def reference_detection(
    *,
    detection_id: int = 1,
    range_m: float = 100.0,
    range_rate_m_s: float = 10.0,
) -> dict:
    covariance = [0.0] * 16
    covariance[0] = 0.0625
    covariance[5] = 0.25
    covariance[10] = 1.0e-6
    covariance[15] = 1.0e-6

    return {
        "detection_id": detection_id,
        "range_m": range_m,
        "range_rate_m_s": range_rate_m_s,
        "azimuth_rad": 0.0,
        "elevation_rad": 0.0,
        "covariance": covariance,
        "snr_db": 20.0,
        "quality": 1.0,
        "timestamp_uncertainty_us": 10.0,
        "validity_flags": VALID_ALL,
        "radar_flags": 0x1234,
    }
