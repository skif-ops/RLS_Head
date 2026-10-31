from __future__ import annotations

import argparse
import csv
import math
import queue
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tools.evt_visualizer import __version__
from tools.evt_visualizer.demo import build_demo_packet
from tools.evt_visualizer.stream import DecodedPacket, TargetStateStreamDecoder

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


BAUD_RATE = 921600
SERIAL_FORMAT = "8N1"
TRACK_TTL_S = 2.0
CSV_FIELDS = [
    "computer_time",
    "sequence",
    "boot_id",
    "track_id",
    "range_m",
    "range_rate_m_s",
    "azimuth_deg",
    "elevation_deg",
    "snr_db",
    "track_quality",
    "confidence",
    "measurement_age_ms",
    "timestamp_uncertainty_us",
    "radar_status",
    "fusion_status",
    "track_flags",
]


class SourceWorker(threading.Thread):
    def __init__(self, output: queue.Queue, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.output = output
        self.stop_event = stop_event

    def emit_bytes(self, decoder: TargetStateStreamDecoder, data: bytes) -> None:
        for packet in decoder.feed(data):
            self.output.put(("packet", packet))


class SerialWorker(SourceWorker):
    def __init__(self, port: str, output: queue.Queue, stop_event: threading.Event) -> None:
        super().__init__(output, stop_event)
        self.port = port

    def run(self) -> None:
        decoder = TargetStateStreamDecoder()
        try:
            with serial.Serial(
                self.port,
                BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            ) as connection:
                self.output.put(("status", f"Подключено: {self.port}, {BAUD_RATE} {SERIAL_FORMAT}"))
                while not self.stop_event.is_set():
                    data = connection.read(connection.in_waiting or 1)
                    if data:
                        self.emit_bytes(decoder, data)
        except Exception as exc:
            self.output.put(("error", f"Ошибка COM-порта {self.port}: {exc}"))
        finally:
            self.output.put(("stopped", None))


class DemoWorker(SourceWorker):
    def run(self) -> None:
        decoder = TargetStateStreamDecoder()
        started = time.monotonic()
        sequence = 1
        self.output.put(("status", "Демонстрационный режим"))
        while not self.stop_event.wait(0.08):
            elapsed = time.monotonic() - started
            for track_id in (1, 2, 3):
                self.emit_bytes(decoder, build_demo_packet(sequence, elapsed, track_id))
                sequence += 1
        self.output.put(("stopped", None))


class ReplayWorker(SourceWorker):
    def __init__(self, path: Path, output: queue.Queue, stop_event: threading.Event) -> None:
        super().__init__(output, stop_event)
        self.path = path

    def run(self) -> None:
        decoder = TargetStateStreamDecoder()
        self.output.put(("status", f"Воспроизведение: {self.path.name}"))
        try:
            with self.path.open("rb") as stream:
                while not self.stop_event.is_set():
                    chunk = stream.read(200)
                    if not chunk:
                        break
                    self.emit_bytes(decoder, chunk)
                    if self.stop_event.wait(0.04):
                        break
        except OSError as exc:
            self.output.put(("error", f"Не удалось прочитать запись: {exc}"))
        finally:
            self.output.put(("stopped", None))


class EvtVisualizer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"EVT ГСН Визуализатор {__version__}")
        self.geometry("1280x820")
        self.minsize(1040, 680)
        self.configure(bg="#111820")

        self.events: queue.Queue = queue.Queue()
        self.worker: SourceWorker | None = None
        self.stop_event: threading.Event | None = None
        self.tracks: dict[int, dict] = {}
        self.track_seen: dict[int, float] = {}
        self.history: dict[int, deque] = defaultdict(lambda: deque(maxlen=40))
        self.packet_count = 0
        self.sequence_gaps = 0
        self.last_sequence: int | None = None
        self.record_csv = None
        self.record_binary = None
        self.record_writer = None
        self.record_count = 0

        self._configure_style()
        self._build_controls()
        self._refresh_ports()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._process_events)
        self.after(100, self._redraw)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#111820")
        style.configure("Panel.TFrame", background="#1A2632")
        style.configure("TLabel", background="#111820", foreground="#E8F0F7", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16), foreground="#FFFFFF")
        style.configure("Metric.TLabel", background="#1A2632", foreground="#A9C5D8", font=("Segoe UI", 9))
        style.configure("MetricValue.TLabel", background="#1A2632", foreground="#FFFFFF", font=("Consolas", 12, "bold"))
        style.configure("TButton", padding=(10, 6), font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#1C7ED6", foreground="white")
        style.map("Accent.TButton", background=[("active", "#339AF0")])
        style.configure("Treeview", background="#111820", fieldbackground="#111820", foreground="#E8F0F7", rowheight=26)
        style.configure("Treeview.Heading", background="#243444", foreground="white", font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#1C7ED6")])

    def _build_controls(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(14, 8))
        ttk.Label(header, text="EVT ГСН Визуализатор", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="TargetState V1 | USB-UART 3,3 В | 921600 8N1").pack(side="left", padx=18)

        controls = ttk.Frame(self, style="Panel.TFrame")
        controls.pack(fill="x", padx=16, pady=(0, 10))
        controls.columnconfigure(10, weight=1)

        ttk.Label(controls, text="COM-порт", style="Metric.TLabel").grid(row=0, column=0, padx=(12, 4), pady=10)
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(controls, textvariable=self.port_var, width=14, state="readonly")
        self.port_box.grid(row=0, column=1, padx=4)
        ttk.Button(controls, text="Обновить", command=self._refresh_ports).grid(row=0, column=2, padx=4)
        self.connect_button = ttk.Button(controls, text="Подключить", style="Accent.TButton", command=self._toggle_connection)
        self.connect_button.grid(row=0, column=3, padx=4)
        ttk.Button(controls, text="Демо", command=self._start_demo).grid(row=0, column=4, padx=4)
        ttk.Button(controls, text="Открыть BIN", command=self._open_replay).grid(row=0, column=5, padx=4)
        self.record_button = ttk.Button(controls, text="Запись", command=self._toggle_recording)
        self.record_button.grid(row=0, column=6, padx=4)
        ttk.Button(controls, text="Подключение", command=self._show_connection_help).grid(row=0, column=7, padx=4)
        ttk.Label(controls, text="Дальность", style="Metric.TLabel").grid(row=0, column=8, padx=(14, 4))
        self.range_var = tk.StringVar(value="200")
        range_box = ttk.Combobox(controls, textvariable=self.range_var, values=("25", "50", "100", "200", "300", "500"), width=6, state="readonly")
        range_box.grid(row=0, column=9, padx=4)
        ttk.Label(controls, text="м", style="Metric.TLabel").grid(row=0, column=10, sticky="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg="#081018", highlightthickness=1, highlightbackground="#2B3D4F")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        side = ttk.Frame(body, style="Panel.TFrame")
        side.grid(row=0, column=1, sticky="nsew")
        side.columnconfigure(0, weight=1)
        side.rowconfigure(2, weight=1)
        ttk.Label(side, text="Обнаруженные цели", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        metrics = ttk.Frame(side, style="Panel.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", padx=12)
        for column in range(4):
            metrics.columnconfigure(column, weight=1)
        self.metric_vars = {
            "packets": tk.StringVar(value="0"),
            "tracks": tk.StringVar(value="0"),
            "gaps": tk.StringVar(value="0"),
            "record": tk.StringVar(value="0"),
        }
        labels = (("Пакеты", "packets"), ("Цели", "tracks"), ("Пропуски", "gaps"), ("Записано", "record"))
        for index, (label, key) in enumerate(labels):
            cell = ttk.Frame(metrics, style="Panel.TFrame")
            cell.grid(row=0, column=index, sticky="ew", padx=4, pady=4)
            ttk.Label(cell, text=label, style="Metric.TLabel").pack()
            ttk.Label(cell, textvariable=self.metric_vars[key], style="MetricValue.TLabel").pack()

        columns = ("id", "range", "azimuth", "speed", "snr", "quality")
        self.table = ttk.Treeview(side, columns=columns, show="headings", selectmode="browse")
        headings = {"id": "ID", "range": "Дальность", "azimuth": "Азимут", "speed": "Скорость", "snr": "SNR", "quality": "Качество"}
        widths = {"id": 48, "range": 86, "azimuth": 76, "speed": 82, "snr": 62, "quality": 76}
        for key in columns:
            self.table.heading(key, text=headings[key])
            self.table.column(key, width=widths[key], anchor="center", stretch=True)
        self.table.grid(row=2, column=0, sticky="nsew", padx=12, pady=10)

        details = ttk.Frame(side, style="Panel.TFrame")
        details.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.details_var = tk.StringVar(value="Выберите цель в таблице")
        ttk.Label(details, textvariable=self.details_var, style="Metric.TLabel", justify="left").pack(anchor="w")
        self.table.bind("<<TreeviewSelect>>", self._show_selected)

        self.status_var = tk.StringVar(value="Готово. Выберите COM-порт или запустите демо.")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", padx=16, pady=(0, 12))

    def _show_connection_help(self) -> None:
        messagebox.showinfo(
            "Подключение через USB-UART",
            "Основной канал J6:\n"
            "J6.1 GND -> GND адаптера\n"
            "J6.2 HOST_UART1_TX -> RX адаптера\n"
            "J6.3 HOST_UART1_RX -> TX адаптера, если нужен обратный канал\n\n"
            "Параметры: 921600 бод, 8N1, уровни 3,3 В.\n"
            "VCC, 3V3 и 5V адаптера к плате не подключать.\n"
            "Не использовать адаптер RS-232 или RS-485. Плата питается отдельно через J1.",
        )

    def _refresh_ports(self) -> None:
        ports = [] if list_ports is None else [port.device for port in list_ports.comports()]
        self.port_box["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])
        if not ports:
            self.port_var.set("")

    def _start_worker(self, worker: SourceWorker) -> None:
        self._stop_source()
        self.stop_event = worker.stop_event
        self.worker = worker
        self.connect_button.configure(text="Отключить")
        worker.start()

    def _toggle_connection(self) -> None:
        if self.worker is not None:
            self._stop_source()
            return
        if serial is None:
            messagebox.showerror("Нет драйвера программы", "Модуль pyserial отсутствует. Используйте готовый EXE из архива.")
            return
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("COM-порт", "Подключите USB-UART адаптер и нажмите Обновить.")
            return
        stop_event = threading.Event()
        self._start_worker(SerialWorker(port, self.events, stop_event))

    def _start_demo(self) -> None:
        stop_event = threading.Event()
        self._start_worker(DemoWorker(self.events, stop_event))

    def _open_replay(self) -> None:
        filename = filedialog.askopenfilename(title="Открыть запись TargetState", filetypes=(("Двоичная запись", "*.bin"), ("Все файлы", "*.*")))
        if not filename:
            return
        stop_event = threading.Event()
        self._start_worker(ReplayWorker(Path(filename), self.events, stop_event))

    def _stop_source(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
        self.worker = None
        self.stop_event = None
        self.connect_button.configure(text="Подключить")
        self.status_var.set("Источник остановлен")

    def _toggle_recording(self) -> None:
        if self.record_csv is not None:
            self._close_recording()
            return
        filename = filedialog.asksaveasfilename(
            title="Сохранить запись",
            defaultextension=".csv",
            filetypes=(("CSV и BIN", "*.csv"),),
            initialfile=time.strftime("EVT_capture_%Y%m%d_%H%M%S.csv"),
        )
        if not filename:
            return
        csv_path = Path(filename)
        bin_path = csv_path.with_suffix(".bin")
        try:
            self.record_csv = csv_path.open("w", encoding="utf-8-sig", newline="")
            self.record_binary = bin_path.open("wb")
            self.record_writer = csv.DictWriter(self.record_csv, fieldnames=CSV_FIELDS)
            self.record_writer.writeheader()
            self.record_button.configure(text="Остановить запись")
            self.status_var.set(f"Запись: {csv_path.name} и {bin_path.name}")
        except OSError as exc:
            self._close_recording()
            messagebox.showerror("Запись", str(exc))

    def _close_recording(self) -> None:
        if self.record_csv is not None:
            self.record_csv.close()
        if self.record_binary is not None:
            self.record_binary.close()
        self.record_csv = None
        self.record_binary = None
        self.record_writer = None
        self.record_button.configure(text="Запись")

    def _record(self, packet: DecodedPacket) -> None:
        if self.record_writer is None or self.record_binary is None:
            return
        state = packet.state
        row = {field: state.get(field, "") for field in CSV_FIELDS}
        row["computer_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.record_writer.writerow(row)
        self.record_binary.write(packet.raw)
        self.record_csv.flush()
        self.record_binary.flush()
        self.record_count += 1

    def _process_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "packet":
                self._handle_packet(payload)
            elif event == "status":
                self.status_var.set(payload)
            elif event == "error":
                self.status_var.set(payload)
                messagebox.showerror("EVT ГСН Визуализатор", payload)
            elif event == "stopped":
                self.worker = None
                self.stop_event = None
                self.connect_button.configure(text="Подключить")
        self.after(50, self._process_events)

    def _handle_packet(self, packet: DecodedPacket) -> None:
        state = packet.state
        sequence = state["sequence"]
        if self.last_sequence is not None and sequence != ((self.last_sequence + 1) & 0xFFFFFFFF):
            self.sequence_gaps += 1
        self.last_sequence = sequence
        self.packet_count += 1
        track_id = state["track_id"]
        self.tracks[track_id] = state
        self.track_seen[track_id] = time.monotonic()
        self.history[track_id].append((state["range_m"], state["azimuth_deg"]))
        self._record(packet)

    def _remove_stale_tracks(self) -> None:
        now = time.monotonic()
        stale = [track_id for track_id, seen in self.track_seen.items() if now - seen > TRACK_TTL_S]
        for track_id in stale:
            self.tracks.pop(track_id, None)
            self.track_seen.pop(track_id, None)
            self.history.pop(track_id, None)

    def _redraw(self) -> None:
        self._remove_stale_tracks()
        self._draw_radar()
        self._update_table()
        self.metric_vars["packets"].set(str(self.packet_count))
        self.metric_vars["tracks"].set(str(len(self.tracks)))
        self.metric_vars["gaps"].set(str(self.sequence_gaps))
        self.metric_vars["record"].set(str(self.record_count))
        self.after(100, self._redraw)

    def _draw_radar(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 100)
        height = max(self.canvas.winfo_height(), 100)
        center_x = width / 2
        center_y = height * 0.86
        radius = min(width * 0.46, height * 0.78)
        maximum = float(self.range_var.get())

        for fraction in (0.25, 0.5, 0.75, 1.0):
            r = radius * fraction
            self.canvas.create_arc(center_x - r, center_y - r, center_x + r, center_y + r, start=0, extent=180, style="arc", outline="#284255", width=1)
            self.canvas.create_text(center_x + 5, center_y - r + 12, text=f"{maximum * fraction:.0f} м", fill="#65849A", anchor="w", font=("Segoe UI", 9))
        for angle in (-60, -30, 0, 30, 60):
            radians = math.radians(angle)
            x = center_x + radius * math.sin(radians)
            y = center_y - radius * math.cos(radians)
            self.canvas.create_line(center_x, center_y, x, y, fill="#284255")
            self.canvas.create_text(x, y - 8, text=f"{angle:+d}°", fill="#65849A", font=("Segoe UI", 9))
        self.canvas.create_line(center_x - radius, center_y, center_x + radius, center_y, fill="#284255")
        self.canvas.create_text(18, 18, text="ВИД СВЕРХУ", fill="#A9C5D8", anchor="nw", font=("Segoe UI Semibold", 10))

        colors = ("#40C057", "#FFD43B", "#FF6B6B", "#4DABF7", "#CC5DE8")
        for track_id, state in self.tracks.items():
            color = colors[(track_id - 1) % len(colors)]
            for index, (distance, azimuth) in enumerate(self.history[track_id]):
                x, y = self._radar_point(distance, azimuth, center_x, center_y, radius, maximum)
                fade = max(2, int(5 * (index + 1) / max(len(self.history[track_id]), 1)))
                self.canvas.create_oval(x - fade / 2, y - fade / 2, x + fade / 2, y + fade / 2, fill=color, outline="")
            x, y = self._radar_point(state["range_m"], state["azimuth_deg"], center_x, center_y, radius, maximum)
            self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill=color, outline="white", width=2)
            self.canvas.create_text(x + 12, y - 12, text=f"T{track_id}  {state['range_m']:.1f} м", fill="white", anchor="w", font=("Segoe UI Semibold", 10))

    @staticmethod
    def _radar_point(distance: float, azimuth_deg: float, center_x: float, center_y: float, radius: float, maximum: float) -> tuple[float, float]:
        scaled = min(max(distance, 0.0) / maximum, 1.0) * radius
        angle = math.radians(azimuth_deg)
        return center_x + scaled * math.sin(angle), center_y - scaled * math.cos(angle)

    def _update_table(self) -> None:
        selected = self.table.selection()
        selected_id = selected[0] if selected else None
        current = set(self.table.get_children())
        wanted = {str(track_id) for track_id in self.tracks}
        for item in current - wanted:
            self.table.delete(item)
        for track_id, state in sorted(self.tracks.items()):
            values = (
                track_id,
                f"{state['range_m']:.1f} м",
                f"{state['azimuth_deg']:+.1f}°",
                f"{state['range_rate_m_s']:+.1f} м/с",
                f"{state['snr_db']:.1f} дБ",
                f"{state['track_quality']:.2f}",
            )
            key = str(track_id)
            if self.table.exists(key):
                self.table.item(key, values=values)
            else:
                self.table.insert("", "end", iid=key, values=values)
        if selected_id and self.table.exists(selected_id):
            self.table.selection_set(selected_id)

    def _show_selected(self, _event=None) -> None:
        selected = self.table.selection()
        if not selected:
            return
        state = self.tracks.get(int(selected[0]))
        if state is None:
            return
        self.details_var.set(
            f"ID {state['track_id']} | sequence {state['sequence']}\n"
            f"Высота угла: {state['elevation_deg']:+.2f}° | SNR: {state['snr_db']:.1f} дБ\n"
            f"Достоверность: {state['confidence']:.3f} | Возраст: {state['measurement_age_ms']:.1f} мс\n"
            f"Radar status: 0x{state['radar_status']:08X} | Flags: 0x{state['track_flags']:08X}"
        )

    def _on_close(self) -> None:
        self._stop_source()
        self._close_recording()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--smoke-seconds", type=float, default=0.0)
    args, _unknown = parser.parse_known_args()
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = EvtVisualizer()
    if args.demo:
        app.after(200, app._start_demo)
    if args.smoke_seconds > 0:
        app.after(max(500, int(args.smoke_seconds * 1000)), app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
