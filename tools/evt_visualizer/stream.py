from __future__ import annotations

import struct
from dataclasses import dataclass

from tools.hil_host.targetstate import MAGIC, PACKET_SIZE, decode_targetstate_v1


MAGIC_BYTES = struct.pack("<I", MAGIC)


@dataclass(frozen=True)
class DecodedPacket:
    state: dict
    raw: bytes


class TargetStateStreamDecoder:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.bytes_received = 0
        self.packets_decoded = 0
        self.rejected_candidates = 0
        self.discarded_bytes = 0

    def feed(self, data: bytes) -> list[DecodedPacket]:
        self.bytes_received += len(data)
        self.buffer.extend(data)
        decoded: list[DecodedPacket] = []

        while True:
            marker = self.buffer.find(MAGIC_BYTES)
            if marker < 0:
                keep = min(len(self.buffer), len(MAGIC_BYTES) - 1)
                self.discarded_bytes += len(self.buffer) - keep
                if keep:
                    del self.buffer[:-keep]
                else:
                    self.buffer.clear()
                break
            if marker:
                self.discarded_bytes += marker
                del self.buffer[:marker]
            if len(self.buffer) < PACKET_SIZE:
                break

            raw = bytes(self.buffer[:PACKET_SIZE])
            try:
                state = decode_targetstate_v1(raw)
            except ValueError:
                self.rejected_candidates += 1
                self.discarded_bytes += 1
                del self.buffer[0]
                continue

            del self.buffer[:PACKET_SIZE]
            self.packets_decoded += 1
            decoded.append(DecodedPacket(state=state, raw=raw))

        return decoded
