from __future__ import annotations

import queue
import socket
import threading
import time
from pathlib import Path

from .model import Scenario, TwinEngine


class TwinTcpServer(threading.Thread):
    def __init__(
        self,
        scenario: Scenario,
        host: str = "127.0.0.1",
        port: int = 9750,
        events: queue.Queue | None = None,
        record_path: Path | None = None,
    ) -> None:
        super().__init__(daemon=True)
        scenario.validate()
        self.scenario = scenario
        self.host = host
        self.port = int(port)
        self.events = events
        self.record_path = record_path
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.bound_port: int | None = None
        self.client_count = 0
        self.packet_count = 0

    def _emit(self, kind: str, payload) -> None:
        if self.events is not None:
            self.events.put((kind, payload))

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        clients: list[socket.socket] = []
        record = None
        listener = None
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, self.port))
            listener.listen(8)
            listener.setblocking(False)
            self.bound_port = int(listener.getsockname()[1])
            self.ready_event.set()
            if self.record_path is not None:
                self.record_path.parent.mkdir(parents=True, exist_ok=True)
                record = self.record_path.open("wb")
            self._emit("status", f"Двойник запущен: {self.host}:{self.bound_port}")
            engine = TwinEngine(self.scenario)
            period_s = 1.0 / self.scenario.update_hz
            next_tick = time.monotonic()

            while not self.stop_event.is_set():
                while True:
                    try:
                        connection, _address = listener.accept()
                    except BlockingIOError:
                        break
                    connection.settimeout(0.2)
                    clients.append(connection)
                    self.client_count = len(clients)
                    self._emit("clients", self.client_count)

                now = time.monotonic()
                if now >= next_tick:
                    samples = engine.step(period_s)
                    data = b"".join(sample.packet for sample in samples)
                    if record is not None and data:
                        record.write(data)
                        record.flush()
                    disconnected = []
                    for connection in clients:
                        try:
                            if data:
                                connection.sendall(data)
                        except (OSError, socket.timeout):
                            disconnected.append(connection)
                    for connection in disconnected:
                        try:
                            connection.close()
                        finally:
                            clients.remove(connection)
                    self.client_count = len(clients)
                    self.packet_count += len(samples)
                    self._emit("clients", self.client_count)
                    self._emit(
                        "tick",
                        {
                            "packet_count": self.packet_count,
                            "client_count": self.client_count,
                            "samples": [sample.as_event() for sample in samples],
                        },
                    )
                    next_tick += period_s
                    if now - next_tick > period_s:
                        next_tick = now + period_s
                self.stop_event.wait(min(0.02, max(0.001, next_tick - time.monotonic())))
        except Exception as exc:
            self.ready_event.set()
            self._emit("error", str(exc))
        finally:
            for connection in clients:
                try:
                    connection.close()
                except OSError:
                    pass
            if listener is not None:
                listener.close()
            if record is not None:
                record.close()
            self.client_count = 0
            self._emit("clients", 0)
            self._emit("stopped", None)
