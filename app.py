import customtkinter as ctk
import threading
import time
import os
from tkinter import filedialog, messagebox

import psutil

from monitors.system_info import (
    get_cpu_usage, get_cpu_freq, get_cpu_count,
    get_ram_usage, get_disk_partitions, get_disk_usage,
    get_subfolder_sizes, format_bytes, get_process_count,
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

        self.cpu_history = []
        self.ram_history = []
        self.running = True

        self._setup_ui()
        self._start_monitoring()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="Resource\nMonitor",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="center"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        nav_buttons = [
            ("Dashboard", "dashboard"),
            ("Disk Usage", "disk"),
            ("Folder Analyzer", "folders"),
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
                hover_color="#2a2a4a",
                command=lambda k=key: self._switch_tab(k),
            )
            btn.grid(row=i + 1, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons.append(btn)

        self.version_label = ctk.CTkLabel(
            self.sidebar, text="v1.0.0", font=ctk.CTkFont(size=11),
            text_color="#555555"
        )
        self.version_label.grid(row=5, column=0, pady=10)

        self.main_area = ctk.CTkFrame(self, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

        self.tabs = {}
        self._build_dashboard()
        self._build_disk_tab()
        self._build_folders_tab()

        self._switch_tab("dashboard")

    def _build_dashboard(self):
        tab = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        tab.grid_columnconfigure(0, weight=1)
        self.tabs["dashboard"] = tab

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
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)

        self.stat_cards = {}
        stat_data = [
            ("cpu_freq", "CPU Frequency"),
            ("cpu_cores", "CPU Cores"),
            ("processes", "Processes"),
            ("uptime", "Uptime"),
        ]
        for i, (key, title) in enumerate(stat_data):
            card = StatCard(
                stats_frame, title=title, value="---",
                fg_color=("#e8e8e8", "#1e1e3a"),
            )
            card.grid(row=0, column=i, padx=5, sticky="ew")
            self.stat_cards[key] = card

        charts_frame = ctk.CTkFrame(tab, fg_color="transparent")
        charts_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        self.cpu_chart = LineChart(
            charts_frame, title="CPU Usage History",
            max_points=60, height=200,
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.cpu_chart.grid(row=0, column=0, padx=5, sticky="nsew")

        self.ram_chart = LineChart(
            charts_frame, title="Memory Usage History",
            max_points=60, height=200,
            fg_color=("#e8e8e8", "#1e1e3a"),
        )
        self.ram_chart.grid(row=0, column=1, padx=5, sticky="nsew")

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

        self._refresh_disk_tab()

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

        partitions = get_disk_partitions()
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

    def _switch_tab(self, tab_name):
        for name, tab in self.tabs.items():
            tab.grid_remove()
        self.tabs[tab_name].grid(row=0, column=0, sticky="nsew")

    def _update_dashboard(self):
        try:
            cpu = get_cpu_usage()
            freq = get_cpu_freq()
            cores = get_cpu_count()
            ram_pct, ram_used, ram_total = get_ram_usage()
            procs = get_process_count()
            disk = get_disk_usage("/")

            self.cpu_gauge.set_value(cpu, f"{freq:.0f} MHz")
            self.ram_gauge.set_value(ram_pct, f"{format_bytes(ram_used)} / {format_bytes(ram_total)}")
            self.disk_gauge.set_value(disk["percent"], f"{format_bytes(disk['used'])} / {format_bytes(disk['total'])}")

            self.stat_cards["cpu_freq"].set_value(f"{freq:.0f} MHz")
            self.stat_cards["cpu_cores"].set_value(str(cores))
            self.stat_cards["processes"].set_value(str(procs))

            uptime_sec = time.time() - psutil.boot_time()
            uptime_str = f"{int(uptime_sec // 86400)}d {int((uptime_sec % 86400) // 3600)}h {int((uptime_sec % 3600) // 60)}m"
            self.stat_cards["uptime"].set_value(uptime_str)

            self.cpu_history.append(cpu)
            if len(self.cpu_history) > 60:
                self.cpu_history.pop(0)
            self.ram_history.append(ram_pct)
            if len(self.ram_history) > 60:
                self.ram_history.pop(0)

            self.cpu_chart.set_data(self.cpu_history)
            self.ram_chart.set_data(self.ram_history)
        except Exception:
            pass

    def _start_monitoring(self):
        def monitor_loop():
            while self.running:
                self.after(0, self._update_dashboard)
                time.sleep(2)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _on_close(self):
        self.running = False
        self.destroy()
