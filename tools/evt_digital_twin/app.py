from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .model import MANEUVERS, MAX_TARGETS, Scenario, TargetConfig, default_scenario
from .server import TwinTcpServer


MANEUVER_LABELS = {
    "straight": "Прямолинейный",
    "weave": "Змейка",
    "circle": "Разворот",
}
MANEUVER_CODES = {value: key for key, value in MANEUVER_LABELS.items()}


class DigitalTwinApp(tk.Tk):
    def __init__(self, scenario: Scenario | None = None) -> None:
        super().__init__()
        self.title(f"EVT ГСН Цифровой двойник {__version__}")
        self.geometry("1320x820")
        self.minsize(1120, 720)
        self.configure(bg="#101820")
        self.scenario = scenario or default_scenario()
        self.events: queue.Queue = queue.Queue()
        self.server: TwinTcpServer | None = None
        self.latest: dict[int, dict] = {}
        self.selected_track_id: int | None = None

        self._configure_style()
        self._build_ui()
        self._load_global_fields()
        self._populate_table()
        first = self.table.get_children()
        if first:
            self.table.selection_set(first[0])
            self._select_target()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._process_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#101820")
        style.configure("Panel.TFrame", background="#1A2632")
        style.configure("TLabel", background="#101820", foreground="#E8F0F7", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#1A2632", foreground="#D9E5EE", font=("Segoe UI", 9))
        style.configure("Title.TLabel", background="#101820", foreground="white", font=("Segoe UI Semibold", 17))
        style.configure("Section.TLabel", background="#1A2632", foreground="white", font=("Segoe UI Semibold", 11))
        style.configure("TButton", padding=(10, 6), font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#1971C2", foreground="white")
        style.map("Accent.TButton", background=[("active", "#228BE6")])
        style.configure("Treeview", background="#0A121A", fieldbackground="#0A121A", foreground="#E8F0F7", rowheight=28)
        style.configure("Treeview.Heading", background="#243444", foreground="white", font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#1971C2")])
        style.configure("TCheckbutton", background="#1A2632", foreground="#E8F0F7")

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(14, 8))
        ttk.Label(header, text="EVT ГСН Цифровой двойник", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="TargetState V1 | локальный TCP | без управляющих команд").pack(side="left", padx=18)

        global_panel = ttk.Frame(self, style="Panel.TFrame")
        global_panel.pack(fill="x", padx=16, pady=(0, 10))
        for column in range(16):
            global_panel.columnconfigure(column, weight=0)
        global_panel.columnconfigure(15, weight=1)

        self.name_var = tk.StringVar()
        self.port_var = tk.StringVar(value="9750")
        self.update_var = tk.StringVar()
        self.max_range_var = tk.StringVar()
        self.range_noise_var = tk.StringVar()
        self.angle_noise_var = tk.StringVar()
        self.record_enabled_var = tk.BooleanVar(value=False)
        self.record_path_var = tk.StringVar()

        ttk.Label(global_panel, text="Сценарий", style="Panel.TLabel").grid(row=0, column=0, padx=(12, 4), pady=(10, 4))
        ttk.Entry(global_panel, textvariable=self.name_var, width=25).grid(row=0, column=1, columnspan=2, padx=4, sticky="ew")
        ttk.Label(global_panel, text="TCP 127.0.0.1", style="Panel.TLabel").grid(row=0, column=3, padx=(12, 4))
        ttk.Entry(global_panel, textvariable=self.port_var, width=7).grid(row=0, column=4, padx=4)
        ttk.Label(global_panel, text="Частота, Гц", style="Panel.TLabel").grid(row=0, column=5, padx=(12, 4))
        ttk.Entry(global_panel, textvariable=self.update_var, width=7).grid(row=0, column=6, padx=4)
        ttk.Label(global_panel, text="Макс. дальность, м", style="Panel.TLabel").grid(row=0, column=7, padx=(12, 4))
        ttk.Entry(global_panel, textvariable=self.max_range_var, width=9).grid(row=0, column=8, padx=4)
        self.start_button = ttk.Button(global_panel, text="Запустить двойник", style="Accent.TButton", command=self._toggle_server)
        self.start_button.grid(row=0, column=9, padx=(16, 4))
        ttk.Button(global_panel, text="Запустить визуализатор", command=self._launch_visualizer).grid(row=0, column=10, padx=4)
        ttk.Button(global_panel, text="Сохранить", command=self._save_scenario).grid(row=0, column=11, padx=4)
        ttk.Button(global_panel, text="Открыть", command=self._load_scenario).grid(row=0, column=12, padx=4)

        ttk.Label(global_panel, text="Шум дальности, м", style="Panel.TLabel").grid(row=1, column=0, padx=(12, 4), pady=(4, 10))
        ttk.Entry(global_panel, textvariable=self.range_noise_var, width=7).grid(row=1, column=1, padx=4, sticky="w")
        ttk.Label(global_panel, text="Шум угла, град", style="Panel.TLabel").grid(row=1, column=2, padx=(12, 4))
        ttk.Entry(global_panel, textvariable=self.angle_noise_var, width=7).grid(row=1, column=3, padx=4, sticky="w")
        ttk.Checkbutton(global_panel, text="Записывать BIN", variable=self.record_enabled_var).grid(row=1, column=4, columnspan=2, padx=(12, 4), sticky="w")
        ttk.Entry(global_panel, textvariable=self.record_path_var, width=36).grid(row=1, column=6, columnspan=3, padx=4, sticky="ew")
        ttk.Button(global_panel, text="Выбрать файл", command=self._choose_record).grid(row=1, column=9, padx=4)
        self.metric_var = tk.StringVar(value="Клиенты: 0 | Пакеты: 0")
        ttk.Label(global_panel, textvariable=self.metric_var, style="Panel.TLabel").grid(row=1, column=10, columnspan=5, padx=12, sticky="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        body.columnconfigure(0, weight=3, minsize=650)
        body.columnconfigure(1, weight=2, minsize=390)
        body.rowconfigure(0, weight=1)

        list_panel = ttk.Frame(body, style="Panel.TFrame")
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_panel.columnconfigure(0, weight=1)
        list_panel.rowconfigure(1, weight=1)
        top = ttk.Frame(list_panel, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ttk.Label(top, text="Объекты сценария", style="Section.TLabel").pack(side="left")
        ttk.Button(top, text="Добавить", command=self._add_target).pack(side="right", padx=4)
        ttk.Button(top, text="Удалить", command=self._delete_target).pack(side="right", padx=4)

        columns = ("enabled", "id", "name", "rcs", "speed", "range", "azimuth", "course", "maneuver", "snr")
        self.table = ttk.Treeview(list_panel, columns=columns, show="headings", selectmode="browse")
        headings = {
            "enabled": "Вкл",
            "id": "ID",
            "name": "Имя",
            "rcs": "ЭПР, м2",
            "speed": "Скорость",
            "range": "Дальность",
            "azimuth": "Азимут",
            "course": "Курс",
            "maneuver": "Маневр",
            "snr": "SNR",
        }
        widths = {"enabled": 42, "id": 42, "name": 120, "rcs": 72, "speed": 80, "range": 80, "azimuth": 66, "course": 62, "maneuver": 92, "snr": 60}
        for key in columns:
            self.table.heading(key, text=headings[key])
            self.table.column(key, width=widths[key], anchor="center", stretch=key in {"name", "maneuver"})
        self.table.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self.table.bind("<<TreeviewSelect>>", self._select_target)

        editor = ttk.Frame(body, style="Panel.TFrame")
        editor.grid(row=0, column=1, sticky="nsew")
        editor.columnconfigure(1, weight=1)
        ttk.Label(editor, text="Параметры объекта", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))

        self.target_vars = {
            "track_id": tk.StringVar(),
            "name": tk.StringVar(),
            "rcs_m2": tk.StringVar(),
            "speed_kmh": tk.StringVar(),
            "initial_range_m": tk.StringVar(),
            "initial_azimuth_deg": tk.StringVar(),
            "initial_elevation_deg": tk.StringVar(),
            "course_deg": tk.StringVar(),
            "vertical_speed_m_s": tk.StringVar(),
            "maneuver": tk.StringVar(),
            "maneuver_amplitude_deg": tk.StringVar(),
            "maneuver_period_s": tk.StringVar(),
        }
        self.target_enabled_var = tk.BooleanVar(value=True)
        fields = (
            ("ID", "track_id"),
            ("Имя", "name"),
            ("ЭПР, м2", "rcs_m2"),
            ("Скорость, км/ч", "speed_kmh"),
            ("Начальная дальность, м", "initial_range_m"),
            ("Начальный азимут, град", "initial_azimuth_deg"),
            ("Начальный угол места, град", "initial_elevation_deg"),
            ("Курс, град", "course_deg"),
            ("Вертикальная скорость, м/с", "vertical_speed_m_s"),
        )
        row = 1
        for label, key in fields:
            ttk.Label(editor, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=12, pady=4)
            ttk.Entry(editor, textvariable=self.target_vars[key]).grid(row=row, column=1, sticky="ew", padx=(4, 12), pady=4)
            row += 1
        ttk.Label(editor, text="Тип маневра", style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=12, pady=4)
        ttk.Combobox(
            editor,
            textvariable=self.target_vars["maneuver"],
            values=tuple(MANEUVER_LABELS[item] for item in MANEUVERS),
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", padx=(4, 12), pady=4)
        row += 1
        for label, key in (("Амплитуда маневра, град", "maneuver_amplitude_deg"), ("Период маневра, с", "maneuver_period_s")):
            ttk.Label(editor, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=12, pady=4)
            ttk.Entry(editor, textvariable=self.target_vars[key]).grid(row=row, column=1, sticky="ew", padx=(4, 12), pady=4)
            row += 1
        ttk.Checkbutton(editor, text="Объект включен", variable=self.target_enabled_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))
        row += 1
        ttk.Button(editor, text="Применить параметры объекта", style="Accent.TButton", command=self._apply_target).grid(row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))
        row += 1
        ttk.Label(
            editor,
            text="ЭПР влияет на расчетный SNR и качество. TargetState V1 не содержит отдельного поля ЭПР, поэтому ее точное значение отображается в этом окне и сохраняется в сценарии JSON.",
            style="Panel.TLabel",
            justify="left",
            wraplength=360,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))

        self.status_var = tk.StringVar(value="Готово. Настройте объекты и запустите двойник.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=16, pady=(0, 12))

    def _load_global_fields(self) -> None:
        self.name_var.set(self.scenario.name)
        self.update_var.set(f"{self.scenario.update_hz:g}")
        self.max_range_var.set(f"{self.scenario.maximum_range_m:g}")
        self.range_noise_var.set(f"{self.scenario.range_noise_m:g}")
        self.angle_noise_var.set(f"{self.scenario.angle_noise_deg:g}")

    def _read_global_fields(self) -> None:
        self.scenario.name = self.name_var.get().strip()
        self.scenario.update_hz = float(self.update_var.get().replace(",", "."))
        self.scenario.maximum_range_m = float(self.max_range_var.get().replace(",", "."))
        self.scenario.range_noise_m = float(self.range_noise_var.get().replace(",", "."))
        self.scenario.angle_noise_deg = float(self.angle_noise_var.get().replace(",", "."))

    def _populate_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for target in self.scenario.targets:
            self._upsert_target_row(target)

    def _upsert_target_row(self, target: TargetConfig) -> None:
        live = self.latest.get(target.track_id, {})
        values = (
            "Да" if target.enabled else "Нет",
            target.track_id,
            target.name,
            f"{target.rcs_m2:.4g}",
            f"{target.speed_kmh:.1f}",
            f"{live.get('range_m', target.initial_range_m):.1f}",
            f"{live.get('azimuth_deg', target.initial_azimuth_deg):+.1f}",
            f"{target.course_deg:+.1f}",
            MANEUVER_LABELS[target.maneuver],
            "" if not live else f"{live['snr_db']:.1f}",
        )
        key = str(target.track_id)
        if self.table.exists(key):
            self.table.item(key, values=values)
        else:
            self.table.insert("", "end", iid=key, values=values)

    def _select_target(self, _event=None) -> None:
        selected = self.table.selection()
        if not selected:
            return
        track_id = int(selected[0])
        target = next((item for item in self.scenario.targets if item.track_id == track_id), None)
        if target is None:
            return
        self.selected_track_id = track_id
        for key in self.target_vars:
            value = getattr(target, key)
            if key == "maneuver":
                value = MANEUVER_LABELS[value]
            self.target_vars[key].set(str(value))
        self.target_enabled_var.set(target.enabled)

    def _target_from_fields(self) -> TargetConfig:
        def number(key: str) -> float:
            return float(self.target_vars[key].get().replace(",", "."))

        maneuver_label = self.target_vars["maneuver"].get()
        if maneuver_label not in MANEUVER_CODES:
            raise ValueError("Выберите тип маневра")
        return TargetConfig(
            track_id=int(number("track_id")),
            name=self.target_vars["name"].get().strip(),
            enabled=self.target_enabled_var.get(),
            rcs_m2=number("rcs_m2"),
            speed_kmh=number("speed_kmh"),
            initial_range_m=number("initial_range_m"),
            initial_azimuth_deg=number("initial_azimuth_deg"),
            initial_elevation_deg=number("initial_elevation_deg"),
            course_deg=number("course_deg"),
            vertical_speed_m_s=number("vertical_speed_m_s"),
            maneuver=MANEUVER_CODES[maneuver_label],
            maneuver_amplitude_deg=number("maneuver_amplitude_deg"),
            maneuver_period_s=number("maneuver_period_s"),
        )

    def _apply_target(self, quiet: bool = False) -> bool:
        try:
            self._read_global_fields()
            candidate = self._target_from_fields()
            candidate.validate(self.scenario.maximum_range_m)
            if any(item.track_id == candidate.track_id and item.track_id != self.selected_track_id for item in self.scenario.targets):
                raise ValueError(f"ID {candidate.track_id} уже используется")
            index = next(index for index, item in enumerate(self.scenario.targets) if item.track_id == self.selected_track_id)
            previous_id = self.scenario.targets[index].track_id
            self.scenario.targets[index] = candidate
            self.scenario.validate()
            if previous_id != candidate.track_id and self.table.exists(str(previous_id)):
                self.table.delete(str(previous_id))
            self.selected_track_id = candidate.track_id
            self._upsert_target_row(candidate)
            self.table.selection_set(str(candidate.track_id))
            if not quiet:
                self.status_var.set(f"Параметры объекта {candidate.track_id} применены")
            return True
        except (ValueError, StopIteration) as exc:
            if not quiet:
                messagebox.showerror("Параметры объекта", str(exc))
            return False

    def _add_target(self) -> None:
        if len(self.scenario.targets) >= MAX_TARGETS:
            messagebox.showwarning("Объекты", f"Допускается не более {MAX_TARGETS} объектов")
            return
        identifiers = {item.track_id for item in self.scenario.targets}
        track_id = next(item for item in range(1, 65536) if item not in identifiers)
        target = TargetConfig(track_id=track_id, name=f"Объект {track_id}", initial_azimuth_deg=min(60.0, track_id * 5.0))
        self.scenario.targets.append(target)
        self._upsert_target_row(target)
        self.table.selection_set(str(track_id))
        self._select_target()

    def _delete_target(self) -> None:
        if len(self.scenario.targets) <= 1:
            messagebox.showwarning("Объекты", "В сценарии должен остаться хотя бы один объект")
            return
        selected = self.table.selection()
        if not selected:
            return
        track_id = int(selected[0])
        self.scenario.targets = [item for item in self.scenario.targets if item.track_id != track_id]
        self.table.delete(str(track_id))
        self.latest.pop(track_id, None)
        first = self.table.get_children()
        if first:
            self.table.selection_set(first[0])
            self._select_target()

    def _scenario_ready(self) -> bool:
        try:
            self._read_global_fields()
            if self.selected_track_id is not None and not self._apply_target(quiet=True):
                raise ValueError("Исправьте параметры выбранного объекта")
            self.scenario.validate()
            return True
        except ValueError as exc:
            messagebox.showerror("Параметры сценария", str(exc))
            return False

    def _choose_record(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Файл записи TargetState",
            defaultextension=".bin",
            filetypes=(("TargetState BIN", "*.bin"),),
            initialfile=time.strftime("digital_twin_%Y%m%d_%H%M%S.bin"),
        )
        if filename:
            self.record_path_var.set(filename)
            self.record_enabled_var.set(True)

    def _toggle_server(self) -> None:
        if self.server is not None:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self, port_override: int | None = None) -> None:
        if not self._scenario_ready():
            return
        try:
            port = port_override if port_override is not None else int(self.port_var.get())
            if port != 0 and not 1024 <= port <= 65535:
                raise ValueError("TCP-порт должен находиться в диапазоне 1024..65535")
            record_path = None
            if self.record_enabled_var.get():
                raw = self.record_path_var.get().strip()
                if not raw:
                    raw = str(Path.cwd() / time.strftime("digital_twin_%Y%m%d_%H%M%S.bin"))
                    self.record_path_var.set(raw)
                record_path = Path(raw)
            self.latest.clear()
            self.server = TwinTcpServer(self.scenario, port=port, events=self.events, record_path=record_path)
            self.server.start()
            self.start_button.configure(text="Остановить двойник")
            self.status_var.set("Запуск цифрового двойника")
        except ValueError as exc:
            messagebox.showerror("Запуск", str(exc))

    def _stop_server(self) -> None:
        if self.server is not None:
            self.server.stop()
        self.server = None
        self.start_button.configure(text="Запустить двойник")
        self.status_var.set("Цифровой двойник остановлен")

    def _launch_visualizer(self) -> None:
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).with_name("EVT_GSN_Visualizer.exe"))
        candidates.extend(
            [
                Path.cwd() / "EVT_GSN_Visualizer.exe",
                Path(__file__).resolve().parents[2] / ".codex-temp" / "evt_viz_dist5" / "EVT_GSN_Visualizer.exe",
            ]
        )
        executable = next((item for item in candidates if item.exists()), None)
        if executable is None:
            messagebox.showerror("Визуализатор", "EVT_GSN_Visualizer.exe не найден рядом с двойником")
            return
        try:
            subprocess.Popen([str(executable)], cwd=str(executable.parent))
            self.status_var.set("Визуализатор запущен. Нажмите в нем Подключить к двойнику")
        except OSError as exc:
            messagebox.showerror("Визуализатор", str(exc))

    def _save_scenario(self) -> None:
        if not self._scenario_ready():
            return
        filename = filedialog.asksaveasfilename(
            title="Сохранить сценарий",
            defaultextension=".json",
            filetypes=(("Сценарий JSON", "*.json"),),
            initialfile="EVT_digital_twin_scenario.json",
        )
        if not filename:
            return
        try:
            self.scenario.save(Path(filename))
            self.status_var.set(f"Сценарий сохранен: {Path(filename).name}")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Сохранение сценария", str(exc))

    def _load_scenario(self) -> None:
        filename = filedialog.askopenfilename(title="Открыть сценарий", filetypes=(("Сценарий JSON", "*.json"),))
        if not filename:
            return
        try:
            self._stop_server()
            self.scenario = Scenario.load(Path(filename))
            self.latest.clear()
            self._load_global_fields()
            self._populate_table()
            first = self.table.get_children()
            if first:
                self.table.selection_set(first[0])
                self._select_target()
            self.status_var.set(f"Сценарий открыт: {Path(filename).name}")
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Открытие сценария", str(exc))

    def _process_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "status":
                self.status_var.set(payload)
                if self.server is not None and self.server.bound_port is not None:
                    self.port_var.set(str(self.server.bound_port))
            elif event == "tick":
                for sample in payload["samples"]:
                    self.latest[int(sample["track_id"])] = sample
                for target in self.scenario.targets:
                    self._upsert_target_row(target)
                self.metric_var.set(f"Клиенты: {payload['client_count']} | Пакеты: {payload['packet_count']}")
            elif event == "clients":
                packets = 0 if self.server is None else self.server.packet_count
                self.metric_var.set(f"Клиенты: {payload} | Пакеты: {packets}")
            elif event == "error":
                self.status_var.set(f"Ошибка: {payload}")
                self.server = None
                self.start_button.configure(text="Запустить двойник")
                messagebox.showerror("Цифровой двойник", payload)
            elif event == "stopped":
                self.server = None
                self.start_button.configure(text="Запустить двойник")
        self.after(50, self._process_events)

    def _on_close(self) -> None:
        if self.server is not None:
            self.server.stop()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scenario")
    parser.add_argument("--auto-start", action="store_true")
    parser.add_argument("--port", type=int, default=9750)
    parser.add_argument("--smoke-seconds", type=float, default=0.0)
    args, _unknown = parser.parse_known_args()
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    scenario = Scenario.load(Path(args.scenario)) if args.scenario else default_scenario()
    app = DigitalTwinApp(scenario)
    app.port_var.set(str(args.port))
    if args.auto_start:
        app.after(150, lambda: app._start_server(port_override=args.port))
    if args.smoke_seconds > 0:
        if not args.auto_start:
            app.after(150, lambda: app._start_server(port_override=args.port))
        app.after(max(800, int(args.smoke_seconds * 1000)), app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
