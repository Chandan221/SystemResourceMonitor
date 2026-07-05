import customtkinter as ctk
import threading
import time
import os
from collections import deque
from tkinter import filedialog, messagebox

import psutil

from monitors.system_info import (
    get_cpu_stats, get_cpu_freq, get_cpu_count,
    get_ram_usage, get_disk_partitions, get_disk_usage,
    get_subfolder_sizes, format_bytes, get_process_count,
    scan_files_by_type, delete_file, categorize_extension,
    get_top_processes, get_battery_info,
    get_network_speed, get_network_interfaces, format_speed, format_speed_custom, SPEED_UNITS,
)
from widgets.gauge import CircularGauge, ProgressBarWidget, StatCard
from widgets.chart import LineChart


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SystemMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("System Resource Monitor")
        self.geometry("1200x780")
        self.minsize(900, 600)

        self.cpu_history = deque(maxlen=60)
        self.ram_history = deque(maxlen=60)
        self.net_sent_history = deque(maxlen=60)
        self.net_recv_history = deque(maxlen=60)
        self.running = True
        self.refresh_interval = 2.0
        self.current_tab = "dashboard"
        self._process_update_counter = 0
        self._cached_processes = []

        self._setup_ui()
        self.update_idletasks()
        self.after(10, self._init_app)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(100, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="Resource\nMonitor",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="center"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        nav_buttons = [
            ("Dashboard", "dashboard"),
            ("Disk Usage", "disk"),
            ("Network", "network"),
            ("Folder Analyzer", "folders"),
            ("File Analyzer", "files"),
        ]
        self.nav_buttons = []
        for i, (text, key) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                anchor="w",
                height=40,
                text_color=("#cc0000", "#ffffff"),
                hover_color=("#ffcccc", "#2a2a4a"),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.grid(row=i + 1, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons.append(btn)

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=("#cccccc", "#333355"))
        sep.grid(row=7, column=0, padx=15, pady=10, sticky="ew")

        self.theme_btn = ctk.CTkButton(
            self.sidebar, text="☀ Light Mode",
            font=ctk.CTkFont(size=12),
            fg_color="transparent", anchor="w", height=32,
            text_color=("#cc0000", "#ffffff"),
            hover_color=("#ffcccc", "#2a2a4a"),
            command=self._toggle_theme,
        )
        self.theme_btn.grid(row=8, column=0, padx=10, pady=2, sticky="ew")

        refresh_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        refresh_frame.grid(row=9, column=0, padx=10, pady=(5, 2), sticky="ew")
        refresh_frame.grid_columnconfigure(0, weight=1)

        refresh_label = ctk.CTkLabel(
            refresh_frame, text="Refresh Interval",
            font=ctk.CTkFont(size=11), anchor="w",
            text_color=("#cc0000", "#aaaaaa"),
        )
        refresh_label.grid(row=0, column=0, sticky="w")

        self.refresh_slider = ctk.CTkSlider(
            refresh_frame, from_=1, to=10, number_of_steps=9,
            command=self._set_refresh_interval,
        )
        self.refresh_slider.grid(row=1, column=0, pady=(2, 0), sticky="ew")
        self.refresh_slider.set(2)

        self.refresh_value_label = ctk.CTkLabel(
            refresh_frame, text="2s", font=ctk.CTkFont(size=10)
        )
        self.refresh_value_label.grid(row=2, column=0, sticky="w")

        self.version_label = ctk.CTkLabel(
            self.sidebar, text="v1.0.4", font=ctk.CTkFont(size=11),
            text_color=("#444444", "#555555")
        )
        self.version_label.grid(row=101, column=0, pady=10)

        self.main_area = ctk.CTkFrame(self, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

        self.tabs = {}
        self._tabs_built = set()

        self.loading_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame.grid_rowconfigure(0, weight=1)

        self.loading_label = ctk.CTkLabel(
            self.loading_frame, text="",
            font=ctk.CTkFont(size=18),
            justify="center"
        )
        self.loading_label.grid(row=0, column=0)
        self._set_loading("Initializing...")

    def _set_loading(self, message):
        self.loading_label.configure(text=message)

    def _init_app(self):
        try:
            self._set_loading("Building dashboard...")
            self._build_quick()
            self._switch_tab("dashboard")
            self.loading_frame.destroy()
            self._start_monitoring()
            self.after(500, self._build_charts)
        except Exception as e:
            self._set_loading(f"Error: {e}")

    def _build_quick(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["dashboard"] = tab
        self._tabs_built.add("dashboard")

        header = ctk.CTkLabel(
            tab, text="System Overview",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        self.gauge_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.gauge_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        for i in range(3):
            self.gauge_frame.grid_columnconfigure(i, weight=1)

        self.cpu_gauge = CircularGauge(
            self.gauge_frame, title="CPU Usage",
            max_value=100, units="%",
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.cpu_gauge.grid(row=0, column=0, padx=8, sticky="nsew")

        self.ram_gauge = CircularGauge(
            self.gauge_frame, title="Memory Usage",
            max_value=100, units="%",
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.ram_gauge.grid(row=0, column=1, padx=8, sticky="nsew")

        self.disk_gauge = CircularGauge(
            self.gauge_frame, title="Disk Usage",
            max_value=100, units="%",
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.disk_gauge.grid(row=0, column=2, padx=8, sticky="nsew")

        stats_frame = ctk.CTkFrame(tab, fg_color="transparent")
        stats_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        for i in range(5):
            stats_frame.grid_columnconfigure(i, weight=1)

        self.stat_cards = {}
        stat_data = [
            ("cpu_freq", "CPU Frequency"),
            ("cpu_cores", "CPU Cores"),
            ("processes", "Processes"),
            ("uptime", "Uptime"),
            ("battery", "Battery"),
        ]
        for i, (key, title) in enumerate(stat_data):
            card = StatCard(
                stats_frame, title=title, value="---",
                fg_color=("#e8e8e8", "#1e1e3a"),
            )
            card.grid(row=0, column=i, padx=5, sticky="ew")
            self.stat_cards[key] = card

        self.main_charts_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.main_charts_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.main_charts_frame.grid_columnconfigure(0, weight=1)
        self.main_charts_frame.grid_columnconfigure(1, weight=1)

        charts_placeholder = ctk.CTkLabel(
            self.main_charts_frame, text="Loading charts...",
            font=ctk.CTkFont(size=12), text_color=("#444444", "#555555"),
            anchor="center"
        )
        charts_placeholder.grid(row=0, column=0, columnspan=2, pady=40)

        export_btn = ctk.CTkButton(
            tab, text="Export Data (CSV)",
            font=ctk.CTkFont(size=12),
            command=self._export_csv,
            width=140, height=28,
        )
        export_btn.grid(row=4, column=0, padx=20, pady=(5, 0), sticky="w")

        self.percore_frame = ctk.CTkFrame(tab, fg_color=("#e8e8e8", "#1e1e3a"))
        self.percore_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        self.percore_frame.grid_columnconfigure(0, weight=1)

        percore_header = ctk.CTkFrame(self.percore_frame, fg_color="transparent")
        percore_header.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        percore_header.grid_columnconfigure(0, weight=1)

        percore_title = ctk.CTkLabel(
            percore_header, text="Per-Core CPU Usage",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        percore_title.grid(row=0, column=0, sticky="w")

        self.percore_toggle = ctk.CTkButton(
            percore_header, text="▼", width=26, height=22,
            font=ctk.CTkFont(size=9),
            fg_color="#2a2a4a", hover_color="#3a3a5a",
        )
        self.percore_toggle.grid(row=0, column=1, padx=(0, 4))

        self.percore_body = ctk.CTkScrollableFrame(
            self.percore_frame, fg_color="transparent",
            orientation="horizontal", height=70,
        )
        self.percore_body.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")

        self.percore_bars = []
        self.percore_toggle.configure(command=self._toggle_percore)

        self.proc_frame = ctk.CTkFrame(tab, fg_color=("#e8e8e8", "#1e1e3a"))
        self.proc_frame.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        self.proc_frame.grid_columnconfigure(0, weight=1)

        proc_header = ctk.CTkFrame(self.proc_frame, fg_color="transparent")
        proc_header.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        proc_header.grid_columnconfigure(0, weight=1)

        proc_title = ctk.CTkLabel(
            proc_header, text="Top Processes (by CPU)",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        proc_title.grid(row=0, column=0, sticky="w")

        self.proc_toggle = ctk.CTkButton(
            proc_header, text="▼", width=26, height=22,
            font=ctk.CTkFont(size=9),
            fg_color="#2a2a4a", hover_color="#3a3a5a",
        )
        self.proc_toggle.grid(row=0, column=1, padx=(0, 4))

        self.proc_body = ctk.CTkFrame(self.proc_frame, fg_color="transparent")
        self.proc_body.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")
        self.proc_body.grid_columnconfigure(1, weight=1)

        self.proc_labels = []
        self.proc_toggle.configure(command=self._toggle_proc)

    def _build_charts(self):
        try:
            for w in self.main_charts_frame.winfo_children():
                w.destroy()
            self.cpu_chart = LineChart(
                self.main_charts_frame, title="CPU Usage History",
                max_points=60, height=200,
                fg_color=("#e8e8e8", "#1e1e3a"),
            )
            self.cpu_chart.grid(row=0, column=0, padx=5, sticky="nsew")
            self.ram_chart = LineChart(
                self.main_charts_frame, title="Memory Usage History",
                max_points=60, height=200,
                fg_color=("#e8e8e8", "#1e1e3a"),
            )
            self.ram_chart.grid(row=0, column=1, padx=5, sticky="nsew")
        except Exception as e:
            err = ctk.CTkLabel(
                self.main_charts_frame, text=f"Charts unavailable: {e}",
                font=ctk.CTkFont(size=12), text_color="#ff1744"
            )
            err.grid(row=0, column=0, columnspan=2, pady=20)

    def _toggle_percore(self):
        if self.percore_body.winfo_ismapped():
            self.percore_body.grid_remove()
            self.percore_toggle.configure(text="▶")
        else:
            self.percore_body.grid()
            self.percore_toggle.configure(text="▼")

    def _toggle_proc(self):
        if self.proc_body.winfo_ismapped():
            self.proc_body.grid_remove()
            self.proc_toggle.configure(text="▶")
        else:
            self.proc_body.grid()
            self.proc_toggle.configure(text="▼")

    def _build_disk_tab(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["disk"] = tab

        header = ctk.CTkLabel(
            tab, text="Disk Usage",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        self.disk_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.disk_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.disk_container.grid_columnconfigure(0, weight=1)

        self.disk_bars = []

        refresh_btn = ctk.CTkButton(
            tab, text="Refresh",
            font=ctk.CTkFont(size=13),
            command=self._refresh_disk_tab,
            width=120,
        )
        refresh_btn.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        loading = ctk.CTkLabel(
            self.disk_container, text="Loading disk information...",
            font=ctk.CTkFont(size=13), anchor="w"
        )
        loading.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.disk_loading_label = loading

    def _build_network_tab(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["network"] = tab

        header = ctk.CTkLabel(
            tab, text="Network Monitor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        speed_unit_frame = ctk.CTkFrame(tab, fg_color="transparent")
        speed_unit_frame.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        speed_unit_label = ctk.CTkLabel(
            speed_unit_frame, text="Speed Unit:",
            font=ctk.CTkFont(size=13)
        )
        speed_unit_label.grid(row=0, column=0, padx=(0, 8))
        self.speed_unit_var = ctk.StringVar(value="Auto")
        self.speed_unit_combo = ctk.CTkComboBox(
            speed_unit_frame, variable=self.speed_unit_var,
            values=["Auto"] + SPEED_UNITS, width=100,
            font=ctk.CTkFont(size=12), state="readonly",
        )
        self.speed_unit_combo.grid(row=0, column=1)

        gauge_frame = ctk.CTkFrame(tab, fg_color="transparent")
        gauge_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        for i in range(2):
            gauge_frame.grid_columnconfigure(i, weight=1)

        self.net_down_gauge = CircularGauge(
            gauge_frame, title="Download Speed",
            max_value=100, units="%",
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.net_down_gauge.grid(row=0, column=0, padx=8, sticky="nsew")

        self.net_up_gauge = CircularGauge(
            gauge_frame, title="Upload Speed",
            max_value=100, units="%",
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.net_up_gauge.grid(row=0, column=1, padx=8, sticky="nsew")

        self.net_chart = LineChart(
            tab, title="Network Speed History",
            max_points=60, height=180,
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.net_chart.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.net_chart._get_line_color = lambda: "#00e676"

        self.net_interfaces_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.net_interfaces_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        iface_title = ctk.CTkLabel(
            self.net_interfaces_frame, text="Network Interfaces",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        )
        iface_title.grid(row=0, column=0, columnspan=5, pady=(0, 8), sticky="w")

        col_specs = [("Interface", 0, 1), ("Type", 70, 0), ("IP Address", 140, 0), ("Speed", 70, 0), ("Status", 80, 0)]
        for col, (txt, w, wt) in enumerate(col_specs):
            self.net_interfaces_frame.grid_columnconfigure(col, weight=wt, minsize=w)
            hdr = ctk.CTkLabel(
                self.net_interfaces_frame, text=txt,
                font=ctk.CTkFont(size=11, weight="bold"), anchor="w", width=w,
            )
            hdr.grid(row=1, column=col, padx=(6, 2), pady=(0, 4), sticky="w")

        self.interface_widgets = []

    def _update_network_tab(self):
        try:
            sent_speed, recv_speed, total_sent, total_recv = get_network_speed()
            unit = self.speed_unit_combo.get()
            unit = None if unit == "Auto" else unit
            up_text = format_speed_custom(sent_speed, unit) if unit else format_speed(sent_speed)
            down_text = format_speed_custom(recv_speed, unit) if unit else format_speed(recv_speed)
            peak = max(sent_speed, recv_speed, 1)
            up_pct = min((sent_speed / peak) * 100, 100)
            down_pct = min((recv_speed / peak) * 100, 100)
            self.net_up_gauge.set_value(up_pct, down_text, text=up_text)
            self.net_down_gauge.set_value(down_pct, f"DL: {down_text} / UL: {up_text}", text=down_text)

            self.net_sent_history.append(sent_speed)
            self.net_recv_history.append(recv_speed)

            peak_hist = max(max(self.net_sent_history), max(self.net_recv_history), 1)
            down_chart = [(v / peak_hist) * 100 for v in self.net_recv_history]
            self.net_chart.set_data(down_chart)
        except Exception:
            pass

    def _build_folders_tab(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["folders"] = tab

        header = ctk.CTkLabel(
            tab, text="Folder Size Analyzer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        controls.grid_columnconfigure(0, weight=1)

        self.folder_path_var = ctk.StringVar(value="No folder selected")

        self.folder_label = ctk.CTkLabel(
            controls, textvariable=self.folder_path_var,
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.folder_label.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.grid(row=0, column=1, pady=5)

        self.select_btn = ctk.CTkButton(
            btn_frame, text="Select Folder",
            font=ctk.CTkFont(size=13),
            command=self._select_folder,
            width=120,
        )
        self.select_btn.grid(row=0, column=0, padx=5)

        self.scan_btn = ctk.CTkButton(
            btn_frame, text="Scan Sizes",
            font=ctk.CTkFont(size=13),
            command=self._scan_folder,
            width=100,
            state="disabled",
        )
        self.scan_btn.grid(row=0, column=1, padx=5)

        self.folder_progress = ctk.CTkProgressBar(tab)
        self.folder_progress.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.folder_progress.set(0)

        self.folder_status = ctk.CTkLabel(
            tab, text="", font=ctk.CTkFont(size=12)
        )
        self.folder_status.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="w")

        self.folder_results = ctk.CTkFrame(tab, fg_color="transparent")
        self.folder_results.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.folder_results.grid_columnconfigure(0, weight=1)

        self.folder_items = []
        self.selected_folder = None

    def _refresh_disk_tab(self):
        for widget in self.disk_container.winfo_children():
            widget.destroy()
        self.disk_bars.clear()

        loading = ctk.CTkLabel(
            self.disk_container, text="Loading disk information...",
            font=ctk.CTkFont(size=13), anchor="w"
        )
        loading.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        thread = threading.Thread(target=self._do_refresh_disk, daemon=True)
        thread.start()

    def _do_refresh_disk(self):
        try:
            partitions = get_disk_partitions()
            self.after(0, lambda: self._display_disk_data(partitions))
        except Exception as e:
            self.after(0, lambda: self._show_disk_error(str(e)))

    def _display_disk_data(self, partitions):
        for widget in self.disk_container.winfo_children():
            widget.destroy()
        self.disk_bars.clear()

        for p in partitions:
            frame = ctk.CTkFrame(self.disk_container, fg_color=("#e8e8e8", "#1e1e3a"))
            frame.grid(row=len(self.disk_bars), column=0, pady=4, sticky="ew")
            frame.grid_columnconfigure(1, weight=1)

            label = ctk.CTkLabel(
                frame, text=f"{p['device']} ({p['mountpoint']})",
                font=ctk.CTkFont(size=13, weight="bold"), width=160, anchor="w"
            )
            label.grid(row=0, column=0, padx=12, pady=8, sticky="w")

            bar = ctk.CTkProgressBar(frame, height=18, corner_radius=4)
            bar.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
            bar.set(p["percent"] / 100)

            details = (
                f"{format_bytes(p['used'])} / {format_bytes(p['total'])} "
                f"({p['percent']:.1f}%)  Free: {format_bytes(p['free'])}"
            )
            info = ctk.CTkLabel(
                frame, text=details,
                font=ctk.CTkFont(size=11), anchor="w"
            )
            info.grid(row=0, column=2, padx=12, pady=8)

            self.disk_bars.append((frame, bar, p))

    def _show_disk_error(self, error_msg):
        for widget in self.disk_container.winfo_children():
            widget.destroy()
        err = ctk.CTkLabel(
            self.disk_container, text=f"Error loading disks: {error_msg}",
            font=ctk.CTkFont(size=13), anchor="w", text_color="#ff1744"
        )
        err.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Select a folder to analyze")
        if folder:
            self.selected_folder = folder
            display = folder if len(folder) < 60 else "..." + folder[-57:]
            self.folder_path_var.set(display)
            self.scan_btn.configure(state="normal")
            for w in self.folder_results.winfo_children():
                w.destroy()
            self.folder_items.clear()
            self.folder_status.configure(text="")

    def _scan_folder(self):
        if not self.selected_folder:
            return

        self.scan_btn.configure(state="disabled")
        self.select_btn.configure(state="disabled")
        self.folder_progress.set(0)
        self.folder_status.configure(text="Scanning...")

        thread = threading.Thread(target=self._do_scan, daemon=True)
        thread.start()

    def _do_scan(self):
        try:
            items = get_subfolder_sizes(self.selected_folder, max_items=30)
            total_size = sum(s for _, s, _ in items)

            self.after(0, lambda: self._display_folder_results(items, total_size))
        except Exception as e:
            self.after(0, lambda: self.folder_status.configure(text=f"Error: {e}"))
        finally:
            self.after(0, lambda: self.scan_btn.configure(state="normal"))
            self.after(0, lambda: self.select_btn.configure(state="normal"))
            self.after(0, lambda: self.folder_progress.set(1))

    def _display_folder_results(self, items, total_size):
        for w in self.folder_results.winfo_children():
            w.destroy()
        self.folder_items.clear()

        self.folder_status.configure(
            text=f"Total size: {format_bytes(total_size)} across {len(items)} items"
        )

        if not items:
            return

        max_size = items[0][1] if items else 1

        for i, (name, size, path) in enumerate(items):
            frame = ctk.CTkFrame(self.folder_results, fg_color=("#e8e8e8", "#1e1e3a"))
            frame.grid(row=i, column=0, pady=2, sticky="ew")
            frame.grid_columnconfigure(1, weight=1)

            pct = (size / max_size) * 100 if max_size > 0 else 0

            label = ctk.CTkLabel(
                frame, text=name,
                font=ctk.CTkFont(size=12), anchor="w"
            )
            label.grid(row=0, column=0, padx=10, pady=4, sticky="w")

            bar = ctk.CTkProgressBar(frame, height=14, corner_radius=3)
            bar.grid(row=0, column=1, padx=8, pady=4, sticky="ew")
            bar.set(pct / 100)

            size_label = ctk.CTkLabel(
                frame, text=format_bytes(size),
                font=ctk.CTkFont(size=11), width=90, anchor="e"
            )
            size_label.grid(row=0, column=2, padx=10, pady=4)

            self.folder_items.append((frame, bar, name, size, path))

    def _build_file_analyzer_tab(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["files"] = tab

        header = ctk.CTkLabel(
            tab, text="File Type Analyzer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        desc = ctk.CTkLabel(
            tab, text="Deep-scan a directory to group files by type and manage them.",
            font=ctk.CTkFont(size=12), text_color="#888888"
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        controls.grid_columnconfigure(0, weight=1)

        self.file_folder_var = ctk.StringVar(value="No folder selected")

        folder_label = ctk.CTkLabel(
            controls, textvariable=self.file_folder_var,
            font=ctk.CTkFont(size=13), anchor="w"
        )
        folder_label.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.grid(row=0, column=1, pady=5)

        self.file_select_btn = ctk.CTkButton(
            btn_frame, text="Select Folder",
            font=ctk.CTkFont(size=13),
            command=self._select_file_folder, width=120,
        )
        self.file_select_btn.grid(row=0, column=0, padx=5)

        self.file_scan_btn = ctk.CTkButton(
            btn_frame, text="Deep Scan",
            font=ctk.CTkFont(size=13),
            command=self._deep_scan_files,
            width=100, state="disabled",
        )
        self.file_scan_btn.grid(row=0, column=1, padx=5)

        self.file_progress = ctk.CTkProgressBar(tab)
        self.file_progress.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.file_progress.set(0)

        self.file_status = ctk.CTkLabel(
            tab, text="", font=ctk.CTkFont(size=12)
        )
        self.file_status.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="w")

        self.file_results = ctk.CTkFrame(tab, fg_color="transparent")
        self.file_results.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        self.file_results.grid_columnconfigure(0, weight=1)

        self.file_group_widgets = {}
        self.selected_file_folder = None

    def _select_file_folder(self):
        folder = filedialog.askdirectory(title="Select a folder to deep-scan")
        if folder:
            self.selected_file_folder = folder
            display = folder if len(folder) < 60 else "..." + folder[-57:]
            self.file_folder_var.set(display)
            self.file_scan_btn.configure(state="normal")
            for w in self.file_results.winfo_children():
                w.destroy()
            self.file_group_widgets.clear()
            self.file_status.configure(text="")
            self.file_progress.set(0)

    def _deep_scan_files(self):
        if not self.selected_file_folder:
            return

        self.file_scan_btn.configure(state="disabled")
        self.file_select_btn.configure(state="disabled")
        self.file_progress.set(0)
        self.file_status.configure(text="Scanning... (this may take a while for large folders)")
        for w in self.file_results.winfo_children():
            w.destroy()
        self.file_group_widgets.clear()

        self.file_progress.start()

        thread = threading.Thread(target=self._do_file_scan, daemon=True)
        thread.start()

    def _do_file_scan(self):
        try:
            groups, total = scan_files_by_type(
                self.selected_file_folder,
                progress_callback=lambda n: self.after(0, lambda: self.file_status.configure(
                    text=f"Scanning... {n} files found"
                ))
            )
            self.after(0, lambda: self._display_file_groups(groups, total))
        except Exception as e:
            self.after(0, lambda: self.file_status.configure(text=f"Error: {e}"))
        finally:
            self.after(0, lambda: self.file_progress.stop())
            self.after(0, lambda: self.file_progress.set(1))
            self.after(0, lambda: self.file_scan_btn.configure(state="normal"))
            self.after(0, lambda: self.file_select_btn.configure(state="normal"))

    def _display_file_groups(self, groups, total):
        self.file_status.configure(text=f"Total: {total} files across {len(groups)} categories")

        for cat_idx, (category, cat_data) in enumerate(groups.items()):
            group_frame = ctk.CTkFrame(self.file_results, fg_color=("#e8e8e8", "#1e1e3a"))
            group_frame.grid(row=cat_idx, column=0, pady=3, sticky="ew")
            group_frame.grid_columnconfigure(1, weight=1)

            header_frame = ctk.CTkFrame(group_frame, fg_color="transparent")
            header_frame.grid(row=0, column=0, columnspan=4, padx=6, pady=4, sticky="ew")
            header_frame.grid_columnconfigure(1, weight=1)

            expand_btn = ctk.CTkButton(
                header_frame, text="▶", width=26, height=22,
                font=ctk.CTkFont(size=9),
                fg_color="#2a2a4a", hover_color="#3a3a5a",
            )
            expand_btn.grid(row=0, column=0, padx=(2, 6))

            cat_label = ctk.CTkLabel(
                header_frame, text=f"{category}  ({cat_data['total_count']} files)",
                font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
            )
            cat_label.grid(row=0, column=1, padx=2, sticky="w")

            cat_size = ctk.CTkLabel(
                header_frame, text=format_bytes(cat_data["total_size"]),
                font=ctk.CTkFont(size=13), anchor="e", width=100
            )
            cat_size.grid(row=0, column=2, padx=6)

            body_frame = ctk.CTkFrame(group_frame, fg_color="transparent")
            body_frame.grid_columnconfigure(1, weight=1)

            row_in_body = 0
            if cat_data["extensions"]:
                ext_total = sum(d["total_size"] for d in cat_data["extensions"].values())
                for ext, ext_data in cat_data["extensions"].items():
                    ext_pct = (ext_data["total_size"] / ext_total * 100) if ext_total > 0 else 0

                    ext_label = ctk.CTkLabel(
                        body_frame, text=ext,
                        font=ctk.CTkFont(size=12), width=80, anchor="w"
                    )
                    ext_label.grid(row=row_in_body, column=0, padx=(16, 4), pady=2, sticky="w")

                    ext_bar = ctk.CTkProgressBar(body_frame, height=10, corner_radius=2)
                    ext_bar.grid(row=row_in_body, column=1, padx=4, pady=2, sticky="ew")
                    ext_bar.set(ext_pct / 100)

                    ext_info = ctk.CTkLabel(
                        body_frame, text=f"{ext_data['count']} files  {format_bytes(ext_data['total_size'])}",
                        font=ctk.CTkFont(size=11), anchor="e", width=180
                    )
                    ext_info.grid(row=row_in_body, column=2, padx=8, pady=2)
                    row_in_body += 1

                    files = sorted(ext_data["files"], key=lambda x: x["size"], reverse=True)
                    for fdata in files[:50]:
                        f_pct = (fdata["size"] / ext_data["total_size"] * 100) if ext_data["total_size"] > 0 else 0
                        fname = fdata["name"] if len(fdata["name"]) < 40 else fdata["name"][:37] + "..."

                        f_label = ctk.CTkLabel(
                            body_frame, text=fname,
                            font=ctk.CTkFont(size=10), anchor="w"
                        )
                        f_label.grid(row=row_in_body, column=0, padx=(32, 4), pady=1, sticky="w")

                        f_bar = ctk.CTkProgressBar(body_frame, height=6, corner_radius=2)
                        f_bar.grid(row=row_in_body, column=1, padx=4, pady=1, sticky="ew")
                        f_bar.set(f_pct / 100)

                        f_info = ctk.CTkLabel(
                            body_frame, text=format_bytes(fdata["size"]),
                            font=ctk.CTkFont(size=10), anchor="e", width=80
                        )
                        f_info.grid(row=row_in_body, column=2, padx=(2, 2), pady=1)

                        del_btn = ctk.CTkButton(
                            body_frame, text="✕", width=22, height=18,
                            font=ctk.CTkFont(size=8),
                            fg_color="#5a2020", hover_color="#7a3030",
                            command=lambda p=fdata["path"], n=fdata["name"]: self._delete_single_file(p, n),
                        )
                        del_btn.grid(row=row_in_body, column=3, padx=2, pady=1)
                        row_in_body += 1

                    if len(files) > 50:
                        more = ctk.CTkLabel(
                            body_frame, text=f"... and {len(files) - 50} more files",
                            font=ctk.CTkFont(size=10, slant="italic"), anchor="w"
                        )
                        more.grid(row=row_in_body, column=0, padx=(32, 4), pady=1, columnspan=3, sticky="w")
                        row_in_body += 1

            expand_btn.configure(command=lambda g=group_frame, b=body_frame, e=expand_btn: self._toggle_group(g, b, e))
            body_frame.grid_remove()

            self.file_group_widgets[category] = {
                "body": body_frame,
                "expand_btn": expand_btn,
            }

        self.file_results.update_idletasks()

    def _toggle_group(self, group_frame, body_frame, expand_btn):
        if body_frame.winfo_ismapped():
            body_frame.grid_remove()
            expand_btn.configure(text="▶")
        else:
            body_frame.grid(row=1, column=0, columnspan=4, padx=6, pady=(0, 6), sticky="ew")
            expand_btn.configure(text="▼")

    def _delete_single_file(self, file_path, file_name):
        result = messagebox.askyesno(
            "Delete File",
            f"Are you sure you want to delete:\n{file_name}?\n\nThis action cannot be undone.",
            icon="warning"
        )
        if not result:
            return

        success, error = delete_file(file_path)
        if success:
            self.file_status.configure(
                text=f"Deleted: {file_name}",
                text_color="#00e676"
            )
            self.after(2000, lambda: self.file_status.configure(text_color=self._get_default_fg()))
        else:
            messagebox.showerror("Error", f"Failed to delete {file_name}:\n{error}")

        self._deep_scan_files()

    def _get_default_fg(self):
        return ("#444444", "#888888")

    def _switch_tab(self, tab_name):
        self.current_tab = tab_name
        if tab_name not in self._tabs_built:
            self._tabs_built.add(tab_name)
            if tab_name == "disk":
                self._build_disk_tab()
            elif tab_name == "network":
                self._build_network_tab()
            elif tab_name == "folders":
                self._build_folders_tab()
            elif tab_name == "files":
                self._build_file_analyzer_tab()
        for name, tab in self.tabs.items():
            tab.grid_remove()
        self.tabs[tab_name].grid(row=0, column=0, sticky="nsew")
        if tab_name == "disk" and not hasattr(self, "_disk_refreshed"):
            self._disk_refreshed = True
            self.after(100, self._refresh_disk_tab)

    def _start_monitoring(self):
        def monitor_loop():
            while self.running:
                data = self._collect_data()
                if data is not None:
                    self.after(0, lambda d=data: self._update_ui(d))
                time.sleep(self.refresh_interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _collect_data(self):
        def safe(call, default=0):
            try:
                return call()
            except Exception:
                return default
        data = {}
        cpu_stats = safe(lambda: get_cpu_stats(), (0, []))
        data["cpu"], data["per_cpu"] = cpu_stats
        data["freq"] = safe(get_cpu_freq)
        data["cores"] = safe(get_cpu_count)
        r = safe(lambda: get_ram_usage(), (0, 0, 0))
        if isinstance(r, tuple):
            data["ram_pct"], data["ram_used"], data["ram_total"] = r
        else:
            data["ram_pct"] = data["ram_used"] = data["ram_total"] = 0
        data["procs"] = safe(get_process_count)
        data["disk"] = safe(lambda: get_disk_usage("/"), {"percent": 0, "used": 0, "total": 0})
        data["uptime"] = time.time() - safe(psutil.boot_time, 0)
        data["battery"] = safe(get_battery_info)
        self._process_update_counter += 1
        if self._process_update_counter % 5 == 0:
            data["top_procs"] = safe(lambda: get_top_processes(limit=8), [])
            self._cached_processes = data["top_procs"]
        else:
            data["top_procs"] = self._cached_processes
        ns = safe(lambda: get_network_speed(), (0, 0, 0, 0))
        if isinstance(ns, tuple) and len(ns) >= 2:
            data["sent_speed"], data["recv_speed"] = ns[0], ns[1]
        else:
            data["sent_speed"] = data["recv_speed"] = 0
        if self.current_tab == "network":
            data["interfaces"] = safe(get_network_interfaces, [])
        else:
            data["interfaces"] = []
        return data

    def _update_ui(self, data):
        try:
            self.cpu_gauge.set_value(data["cpu"], f"{data['freq']:.0f} MHz")
            self.ram_gauge.set_value(data["ram_pct"], f"{format_bytes(data['ram_used'])} / {format_bytes(data['ram_total'])}")
            self.disk_gauge.set_value(data["disk"]["percent"], f"{format_bytes(data['disk']['used'])} / {format_bytes(data['disk']['total'])}")

            self.stat_cards["cpu_freq"].set_value(f"{data['freq']:.0f} MHz")
            self.stat_cards["cpu_cores"].set_value(str(data["cores"]))
            self.stat_cards["processes"].set_value(str(data["procs"]))

            uptime = data["uptime"]
            uptime_str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m"
            self.stat_cards["uptime"].set_value(uptime_str)

            bat = data["battery"]
            if bat:
                self.stat_cards["battery"].set_value(f"{bat['percent']:.0f}%{' ⚡' if bat['charging'] else ''}")
            else:
                self.stat_cards["battery"].set_value("N/A")

            self.cpu_history.append(data["cpu"])
            self.ram_history.append(data["ram_pct"])

            if hasattr(self, 'cpu_chart'):
                self.cpu_chart.set_data(self.cpu_history)
                self.ram_chart.set_data(self.ram_history)

            self._update_per_core_ui(data["per_cpu"])
            self._update_processes_ui(data["top_procs"])
            if self.current_tab == "network":
                try:
                    self._update_network_ui(data["sent_speed"], data["recv_speed"], data.get("interfaces", []))
                except Exception:
                    pass
        except Exception:
            pass

    def _update_per_core_ui(self, per_cpu):
        while len(self.percore_bars) < len(per_cpu):
            i = len(self.percore_bars)
            frame = ctk.CTkFrame(self.percore_body, fg_color=("#e8e8e8", "#1e1e3a"), width=130)
            frame.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")
            frame.grid_propagate(False)
            name_lbl = ctk.CTkLabel(
                frame, text=f"Core {i}",
                font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
            )
            name_lbl.grid(row=0, column=0, padx=6, pady=(4, 0), sticky="w")
            pbar = ctk.CTkProgressBar(frame, height=10, corner_radius=3)
            pbar.grid(row=1, column=0, padx=6, pady=2, sticky="ew")
            val_lbl = ctk.CTkLabel(
                frame, text="", font=ctk.CTkFont(size=12, weight="bold"), anchor="e",
            )
            val_lbl.grid(row=2, column=0, padx=6, pady=(0, 4), sticky="e")
            self.percore_bars.append((frame, pbar, val_lbl))
        for extra in self.percore_bars[len(per_cpu):]:
            extra[0].destroy()
        self.percore_bars = self.percore_bars[:len(per_cpu)]
        for i, pct in enumerate(per_cpu):
            if i < len(self.percore_bars):
                frame, pbar, val_lbl = self.percore_bars[i]
                pbar.set(pct / 100)
                val_lbl.configure(text=f"{pct:.0f}%")

    def _update_processes_ui(self, processes):
        children = list(self.proc_body.winfo_children())
        while len(children) < len(processes):
            light_bg = "#f0f0f0" if len(children) % 2 == 0 else "#e8e8e8"
            dark_bg = "#1e1e3a" if len(children) % 2 == 0 else "#252550"
            row = ctk.CTkFrame(self.proc_body, fg_color=(light_bg, dark_bg))
            row.grid(row=len(children), column=0, columnspan=3, pady=1, sticky="ew")
            row.grid_columnconfigure(1, weight=1)
            name_lbl = ctk.CTkLabel(row, text="", font=ctk.CTkFont(size=11), anchor="w", width=160)
            name_lbl.grid(row=0, column=0, padx=(6, 4), pady=3, sticky="w")
            cpu_bar = ctk.CTkProgressBar(row, height=10, corner_radius=2)
            cpu_bar.grid(row=0, column=1, padx=4, pady=3, sticky="ew")
            info_lbl = ctk.CTkLabel(row, text="", font=ctk.CTkFont(size=10), anchor="e", width=200)
            info_lbl.grid(row=0, column=2, padx=(4, 6), pady=3)
            children.append(row)
        for extra in children[len(processes):]:
            extra.destroy()
        for i, proc in enumerate(processes):
            row = children[i]
            name = proc["name"] if len(proc["name"]) < 28 else proc["name"][:25] + "..."
            cpu_val = proc["cpu_percent"] or 0
            mem_val = proc["memory_percent"] or 0
            row.winfo_children()[0].configure(text=name)
            row.winfo_children()[1].set(min(cpu_val / 100, 1))
            row.winfo_children()[2].configure(text=f"CPU: {cpu_val:.1f}%  MEM: {mem_val:.1f}%")

    def _update_interfaces_ui(self, interfaces):
        if not hasattr(self, 'net_interfaces_frame'):
            return
        start = 2
        while len(self.interface_widgets) < len(interfaces):
            i = len(self.interface_widgets)
            labels = []
            for col in range(5):
                lbl = ctk.CTkLabel(
                    self.net_interfaces_frame, text="",
                    font=ctk.CTkFont(size=11), anchor="w",
                )
                lbl.grid(row=i + start, column=col, padx=(6, 2), pady=2, sticky="w")
                labels.append(lbl)
            self.interface_widgets.append(labels)
        for extra in self.interface_widgets[len(interfaces):]:
            for lbl in extra:
                lbl.destroy()
        self.interface_widgets = self.interface_widgets[:len(interfaces)]
        for i, iface in enumerate(interfaces):
            labels = self.interface_widgets[i]
            labels[0].configure(text=iface["name"])
            labels[1].configure(text=iface.get("type", "Unknown"))
            labels[2].configure(text=iface.get("ip", ""))
            speed = iface.get("speed", 0)
            labels[3].configure(text=f"{speed} Mbps" if speed else "N/A")
            dot = "●"
            status = "Up" if iface["isup"] else "Down"
            clr = "#00e676" if iface["isup"] else "#ff1744"
            labels[4].configure(text=f"{dot} {status}", text_color=clr)

    def _update_network_ui(self, sent_speed, recv_speed, interfaces=None):
        if not hasattr(self, 'net_up_gauge'):
            return
        unit = self.speed_unit_combo.get() if hasattr(self, 'speed_unit_combo') else "Auto"
        unit = None if unit == "Auto" else unit
        up_text = format_speed_custom(sent_speed, unit) if unit else format_speed(sent_speed)
        down_text = format_speed_custom(recv_speed, unit) if unit else format_speed(recv_speed)
        self.net_sent_history.append(sent_speed)
        self.net_recv_history.append(recv_speed)
        up_peak = max(self.net_sent_history) or 1
        down_peak = max(self.net_recv_history) or 1
        up_pct = min(sent_speed / up_peak * 100, 100)
        down_pct = min(recv_speed / down_peak * 100, 100)
        try:
            self.net_up_gauge.set_value(up_pct, f"UL: {up_text} / DL: {down_text}", text=up_text)
        except Exception:
            pass
        try:
            self.net_down_gauge.set_value(down_pct, f"DL: {down_text} / UL: {up_text}", text=down_text)
        except Exception:
            pass
        if hasattr(self, 'net_chart'):
            peak_hist = max(max(self.net_sent_history), max(self.net_recv_history), 1)
            down_chart = [(v / peak_hist) * 100 for v in self.net_recv_history]

            self.net_chart.set_data(down_chart)
        if interfaces is not None:
            try:
                self._update_interfaces_ui(interfaces)
            except Exception:
                pass

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="🌙 Dark Mode")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="☀ Light Mode")
        self.after(350, lambda: self._refresh_gauge_colors())
        self.after(500, lambda: self._refresh_chart_colors())

    def _refresh_gauge_colors(self):
        for attr in ["cpu_gauge", "ram_gauge", "disk_gauge"]:
            gauge = getattr(self, attr, None)
            if gauge is not None:
                gauge._initial_draw()

    def _refresh_chart_colors(self):
        for attr in ["cpu_chart", "ram_chart", "net_chart"]:
            chart = getattr(self, attr, None)
            if chart is not None:
                try:
                    chart.fig.patch.set_facecolor(chart._get_fig_bg())
                    chart.ax.set_facecolor(chart._get_ax_bg())
                    chart._redraw(full_redraw=True)
                except Exception:
                    pass

    def _set_refresh_interval(self, val):
        self.refresh_interval = float(val)
        self.refresh_value_label.configure(text=f"{int(val)}s")

    def _export_csv(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export monitoring data"
            )
            if not path:
                return
            with open(path, "w") as f:
                f.write("timestamp,cpu_usage,ram_usage\n")
                import datetime
                for i in range(len(self.cpu_history)):
                    ts = datetime.datetime.now().isoformat()
                    cpu_val = self.cpu_history[i] if i < len(self.cpu_history) else ""
                    ram_val = self.ram_history[i] if i < len(self.ram_history) else ""
                    f.write(f"{ts},{cpu_val},{ram_val}\n")
            messagebox.showinfo("Export", f"Data exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _on_close(self):
        self.running = False
        self.destroy()
