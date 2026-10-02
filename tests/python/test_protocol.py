import struct

from tools.hil_host.protocol import (
    CRC_SIZE,
    DETECTION_SIZE,
    HEADER_SIZE,
    crc32c,
    encode_hil_frame,
    reference_detection,
)
from tools.hil_host.targetstate import (
    PACKET_SIZE,
    build_synthetic_targetstate_packet,
    decode_targetstate_v1,
)


def test_crc32c_golden():
    assert crc32c(b"123456789") == 0xE3069283


def test_hil_frame_wire_size_and_crc():
    frame = encode_hil_frame(
        sequence=1,
        frame_id=1,
        measurement_time_us=1_000_000,
        detections=[reference_detection()],
    )

    assert len(frame) == HEADER_SIZE + DETECTION_SIZE + CRC_SIZE

    expected_crc, = struct.unpack_from("<I", frame, len(frame) - 4)
    assert crc32c(frame[:-4]) == expected_crc


def test_empty_hil_frame():
    frame = encode_hil_frame(
        sequence=2,
        frame_id=2,
        measurement_time_us=1_050_000,
        detections=[],
    )

    assert len(frame) == HEADER_SIZE + CRC_SIZE


def test_targetstate_decode_contract():
    packet = build_synthetic_targetstate_packet()

    assert len(packet) == PACKET_SIZE

    decoded = decode_targetstate_v1(packet)

    assert decoded["sequence"] == 7
    assert decoded["source_id"] == 42
    assert decoded["boot_id"] == 99
    assert decoded["track_id"] == 5
    assert decoded["range_m"] == 100.0
    assert decoded["measurement_age_ms"] == 21.0
    assert decoded["track_flags"] == 0x19


def test_targetstate_crc_rejection():
    packet = bytearray(build_synthetic_targetstate_packet())
    packet[50] ^= 0x01

    try:
        decode_targetstate_v1(bytes(packet))
    except ValueError as exc:
        assert "CRC" in str(exc)
    else:
        raise AssertionError("corrupted TargetState packet was accepted")
