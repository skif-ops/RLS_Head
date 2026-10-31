from tools.evt_visualizer.demo import build_demo_packet
from tools.evt_visualizer.stream import TargetStateStreamDecoder


def test_fragmented_targetstate_stream():
    packets = [build_demo_packet(index, index * 0.1, (index % 3) + 1) for index in range(1, 7)]
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
    good = build_demo_packet(2, 0.2, 2)
    decoder = TargetStateStreamDecoder()

    decoded = decoder.feed(bytes(corrupt) + good)

    assert len(decoded) == 1
    assert decoded[0].state["sequence"] == 2
    assert decoder.rejected_candidates == 1


def test_demo_packet_contains_visualization_fields():
    decoder = TargetStateStreamDecoder()
    decoded = decoder.feed(build_demo_packet(44, 2.5, 3))[0].state

    assert decoded["sequence"] == 44
    assert decoded["track_id"] == 3
    assert decoded["range_m"] > 0.0
    assert -90.0 < decoded["azimuth_deg"] < 90.0
    assert 0.0 <= decoded["confidence"] <= 1.0
