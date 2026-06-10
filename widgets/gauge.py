import customtkinter as ctk
import math


class CircularGauge(ctk.CTkFrame):
    def __init__(self, master, title="", max_value=100, units="%", **kwargs):
        super().__init__(master, **kwargs)
        self.title = title
        self.max_value = max_value
        self.units = units
        self.current_value = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.label_title = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=14, weight="bold")
        )
        self.label_title.grid(row=0, column=0, pady=(10, 0))

        self.canvas_size = 180
        self.canvas = ctk.CTkCanvas(
            self,
            width=self.canvas_size,
            height=self.canvas_size,
            highlightthickness=0,
            bg=self._get_bg_color(),
        )
        self.canvas.grid(row=1, column=0, pady=5)

        self.label_value = ctk.CTkLabel(
            self, text="0%", font=ctk.CTkFont(size=28, weight="bold")
        )
        self.label_value.grid(row=2, column=0, pady=(0, 5))

        self.label_detail = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12)
        )
        self.label_detail.grid(row=3, column=0, pady=(0, 10))

        self.bind("<Configure>", lambda e: self.draw())
        self.after(100, self._initial_draw)

    def _get_bg_color(self):
        theme = ctk.get_appearance_mode()
        return "#1a1a2e" if theme == "Dark" else "#f0f0f0"

    def _initial_draw(self):
        self.canvas.config(bg=self._get_bg_color())
        self.draw()

    def set_value(self, value, detail="", text=None):
        self.current_value = min(value, self.max_value)
        pct = (self.current_value / self.max_value) * 100 if self.max_value > 0 else 0
        if text is not None:
            self.label_value.configure(text=text)
        else:
            self.label_value.configure(text=f"{pct:.1f}{self.units}")
        self.label_detail.configure(text=detail)
        self.draw()

    def get_color(self, pct):
        if pct < 50:
            return "#00e676"
        elif pct < 80:
            return "#ffab00"
        return "#ff1744"

    def draw(self):
        self.canvas.delete("all")
        w = self.canvas_size
        cx, cy = w // 2, w // 2
        r = 70
        line_width = 12

        pct = (self.current_value / self.max_value) * 100 if self.max_value > 0 else 0
        angle = (pct / 100) * 360

        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline="#333355", width=line_width, tags="bg"
        )

        color = self.get_color(pct)

        if angle > 0:
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=90, extent=-angle,
                outline=color, width=line_width,
                style="arc", tags="arc"
            )

        self.canvas.create_oval(
            cx - 20, cy - 20, cx + 20, cy + 20,
            fill=self._get_bg_color(), outline=color, width=2
        )


class ProgressBarWidget(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, **kwargs)
        self.title = title

        self.grid_columnconfigure(1, weight=1)

        self.label = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=13), width=120, anchor="w"
        )
        self.label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.progress = ctk.CTkProgressBar(self, height=16, corner_radius=4)
        self.progress.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.progress.set(0)

        self.value_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), width=140, anchor="e"
        )
        self.value_label.grid(row=0, column=2, padx=(5, 10), pady=5)

    def set(self, value, text=""):
        self.progress.set(value / 100)
        self.value_label.configure(text=text)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title="", value="", icon="", **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.label_title = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=12), anchor="w"
        )
        self.label_title.grid(row=0, column=0, padx=15, pady=(15, 0), sticky="w")

        self.label_value = ctk.CTkLabel(
            self, text=value, font=ctk.CTkFont(size=24, weight="bold"), anchor="w"
        )
        self.label_value.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

    def set_value(self, value):
        self.label_value.configure(text=value)
