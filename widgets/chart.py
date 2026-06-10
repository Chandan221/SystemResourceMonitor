import customtkinter as ctk


class LineChart(ctk.CTkFrame):
    def __init__(self, master, title="", max_points=60, height=200, **kwargs):
        super().__init__(master, **kwargs)
        self.title = title
        self.max_points = max_points
        self.data = []

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        import matplotlib
        matplotlib.use("Agg")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label_title = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=14, weight="bold")
        )
        self.label_title.grid(row=0, column=0, pady=(8, 0))

        self.fig = Figure(figsize=(6, 2.2), dpi=100)
        self.fig.patch.set_facecolor(self._get_fig_bg())
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self._get_ax_bg())
        self.ax.tick_params(colors="#888888", labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color("#333355")
            spine.set_linewidth(0.5)
        self.ax.set_xlim(0, max_points)
        self.ax.set_ylim(0, 100)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def _get_fig_bg(self):
        return "#1a1a2e" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"

    def _get_ax_bg(self):
        return "#16213e" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0"

    def add_point(self, value):
        self.data.append(value)
        if len(self.data) > self.max_points:
            self.data.pop(0)
        self._redraw()

    def set_data(self, data):
        self.data = list(data)
        if len(self.data) > self.max_points:
            self.data = self.data[-self.max_points:]
        self._redraw()

    def _redraw(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        spine_color = "#333355" if is_dark else "#cccccc"
        grid_color = "#333355" if is_dark else "#cccccc"
        tick_color = "#888888"
        self.ax.clear()
        self.ax.set_facecolor(self._get_ax_bg())
        self.ax.tick_params(colors=tick_color, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(spine_color)
            spine.set_linewidth(0.5)
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, color=grid_color, linewidth=0.3, alpha=0.5)

        if self.data:
            line_color = self._get_line_color()
            self.ax.plot(
                range(len(self.data)), self.data,
                color=line_color, linewidth=1.8, alpha=0.9
            )
            self.ax.fill_between(
                range(len(self.data)), self.data, 0,
                color=line_color, alpha=0.08
            )

        self.fig.tight_layout(pad=0.8)
        self.canvas.draw()

    def _get_line_color(self):
        return "#4fc3f7"
