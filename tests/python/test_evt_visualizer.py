import math

from tools.evt_visualizer.demo import (
    MAX_TARGET_SPEED_KM_H,
    MIN_TARGET_SPEED_KM_H,
    TrackingTwin,
    build_demo_packet,
    build_tracking_packet,
)
from tools.evt_visualizer.stream import TargetStateStreamDecoder


def test_fragmented_targetstate_stream():
    packets = [build_demo_packet(index, index * 0.1) for index in range(1, 7)]
    stream = b"junk" + b"".join(packets)
    decoder = TargetStateStreamDecoder()
    decoded = []
    for offset in range(0, len(stream), 37):
        decoded.extend(decoder.feed(stream[offset:offset + 37]))

    assert [item.state["sequence"] for item in decoded] == list(range(1, 7))
    assert decoder.packets_decoded == 6
    assert decoder.discarded_bytes == 4


def test_stream_resynchronizes_after_corrupt_packet():
    corrupt = bytearray(build_demo_packet(1, 0.1, 1))
    corrupt[50] ^= 0x01
    good = build_demo_packet(2, 0.2)
    decoder = TargetStateStreamDecoder()

    decoded = decoder.feed(bytes(corrupt) + good)

    assert len(decoded) == 1
    assert decoded[0].state["sequence"] == 2
    assert decoder.rejected_candidates == 1


def test_demo_packet_contains_visualization_fields():
    decoder = TargetStateStreamDecoder()
    decoded = decoder.feed(build_demo_packet(44, 2.5))[0].state

    assert decoded["sequence"] == 44
    assert decoded["track_id"] == 1
    assert decoded["range_m"] > 0.0
    assert -90.0 < decoded["azimuth_deg"] < 90.0
    assert 0.0 <= decoded["confidence"] <= 1.0
    speed_km_h = math.sqrt(sum(value * value for value in decoded["velocity_m_s"])) * 3.6
    assert MIN_TARGET_SPEED_KM_H <= speed_km_h <= MAX_TARGET_SPEED_KM_H


def test_tracking_twin_has_one_target_and_resonance_margin():
    twin = TrackingTwin()
    states = [twin.step(0.08) for _ in range(800)]
    speeds = [state.full_speed_km_h for state in states]
    settled_states = states[125:]

    assert min(speeds) >= MIN_TARGET_SPEED_KM_H - 1.0e-6
    assert max(speeds) <= MAX_TARGET_SPEED_KM_H + 1.0e-6
    assert states[-1].resonance_margin > 5.0
    assert states[-1].model_status == "ПРЕДВАРИТЕЛЬНАЯ МЕХАНИЧЕСКАЯ МОДЕЛЬ"
    assert max(abs(state.mount_rate_deg_s) for state in states) <= 90.0 + 1.0e-6
    assert max(abs(state.mount_error_deg) for state in settled_states) < 1.0

    packet = build_tracking_packet(1, states[-1])
    decoded = TargetStateStreamDecoder().feed(packet)
    assert len(decoded) == 1
    assert decoded[0].state["track_id"] == 1
