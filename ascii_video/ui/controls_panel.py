"""Parameter controls: video pipeline sliders/switches, and a dynamic panel
for generator params built from each GeneratorSpec's param_schema."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ascii_video.core.ramp import RAMP_PRESETS
from ascii_video.generators.base import GeneratorSpec


class VideoControlsPanel(ctk.CTkFrame):
    def __init__(self, master, on_change: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self._sliders: dict[str, tuple[ctk.CTkSlider, ctk.Variable, ctk.CTkLabel, bool]] = {}

        self.cols_var = ctk.IntVar(value=90)
        self.threshold_var = ctk.DoubleVar(value=0.35)
        self.ramp_var = ctk.StringVar(value="classic")
        self.invert_var = ctk.BooleanVar(value=False)
        self.dither_var = ctk.BooleanVar(value=False)
        self.color_var = ctk.BooleanVar(value=False)

        ctk.CTkLabel(self, text="Video controls", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 4))
        self._slider_row("cols", "Columns", self.cols_var, 20, 220, is_int=True)
        self._slider_row("edge_threshold", "Edge threshold", self.threshold_var, 0.05, 0.95)

        ramp_row = ctk.CTkFrame(self, fg_color="transparent")
        ramp_row.pack(fill="x", pady=2)
        ctk.CTkLabel(ramp_row, text="Charset", width=110, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            ramp_row, values=list(RAMP_PRESETS.keys()), variable=self.ramp_var,
            command=lambda _=None: self.on_change(),
        ).pack(side="left", fill="x", expand=True)

        switches = ctk.CTkFrame(self, fg_color="transparent")
        switches.pack(fill="x", pady=(6, 2))
        ctk.CTkSwitch(switches, text="Invert", variable=self.invert_var, command=self.on_change).pack(anchor="w", pady=2)
        ctk.CTkSwitch(switches, text="Dither", variable=self.dither_var, command=self.on_change).pack(anchor="w", pady=2)
        ctk.CTkSwitch(switches, text="Color", variable=self.color_var, command=self.on_change).pack(anchor="w", pady=2)

    def _slider_row(self, key: str, label: str, var: ctk.Variable, lo: float, hi: float, is_int: bool = False) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=110, anchor="w").pack(side="left")
        value_label = ctk.CTkLabel(row, text=str(var.get()), width=50)

        def _on_slide(v: str) -> None:
            val = int(float(v)) if is_int else round(float(v), 2)
            var.set(val)
            value_label.configure(text=str(val))
            self.on_change()

        slider = ctk.CTkSlider(row, from_=lo, to=hi, command=_on_slide)
        slider.set(var.get())
        slider.pack(side="left", fill="x", expand=True, padx=8)
        value_label.pack(side="left")
        self._sliders[key] = (slider, var, value_label, is_int)

    def ramp_string(self) -> str:
        return RAMP_PRESETS.get(self.ramp_var.get(), RAMP_PRESETS["classic"])

    def get_state(self) -> dict:
        return {
            "cols": self.cols_var.get(),
            "edge_threshold": self.threshold_var.get(),
            "ramp": self.ramp_var.get(),
            "invert": self.invert_var.get(),
            "dither": self.dither_var.get(),
            "color": self.color_var.get(),
        }

    def apply_state(self, state: dict) -> None:
        for key in ("cols", "edge_threshold"):
            if key in state and key in self._sliders:
                slider, var, value_label, is_int = self._sliders[key]
                val = int(state[key]) if is_int else round(float(state[key]), 2)
                var.set(val)
                slider.set(val)
                value_label.configure(text=str(val))
        if "ramp" in state:
            self.ramp_var.set(state["ramp"])
        if "invert" in state:
            self.invert_var.set(state["invert"])
        if "dither" in state:
            self.dither_var.set(state["dither"])
        if "color" in state:
            self.color_var.set(state["color"])
        self.on_change()


class GeneratorControlsPanel(ctk.CTkFrame):
    def __init__(self, master, on_change: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.vars: dict[str, ctk.Variable] = {}
        self._sliders: dict[str, tuple[ctk.CTkSlider, ctk.CTkLabel, bool]] = {}
        self._title = ctk.CTkLabel(self, text="Generator controls", font=ctk.CTkFont(weight="bold"))
        self._title.pack(anchor="w", pady=(0, 4))
        self._widgets_frame: ctk.CTkFrame | None = None

    def build_for(self, spec: GeneratorSpec) -> None:
        if self._widgets_frame is not None:
            self._widgets_frame.destroy()
        self._widgets_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._widgets_frame.pack(fill="x")
        self.vars = {}
        self._sliders = {}

        for p in spec.params:
            if p.kind == "bool":
                var = ctk.BooleanVar(value=p.default)
                ctk.CTkSwitch(self._widgets_frame, text=p.label, variable=var, command=self.on_change).pack(anchor="w", pady=2)
            elif p.kind == "choice":
                var = ctk.StringVar(value=p.default)
                row = ctk.CTkFrame(self._widgets_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=p.label, width=90, anchor="w").pack(side="left")
                ctk.CTkOptionMenu(
                    row, values=list(p.choices or []), variable=var,
                    command=lambda _=None: self.on_change(),
                ).pack(side="left", fill="x", expand=True)
            elif p.kind in ("float", "int"):
                var = ctk.DoubleVar(value=p.default) if p.kind == "float" else ctk.IntVar(value=p.default)
                row = ctk.CTkFrame(self._widgets_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=p.label, width=90, anchor="w").pack(side="left")
                value_label = ctk.CTkLabel(row, text=str(p.default), width=50)
                is_int = p.kind == "int"

                def _on_slide(v: str, var=var, value_label=value_label, is_int=is_int) -> None:
                    val = int(float(v)) if is_int else round(float(v), 2)
                    var.set(val)
                    value_label.configure(text=str(val))
                    self.on_change()

                slider = ctk.CTkSlider(row, from_=p.min, to=p.max, command=_on_slide)
                slider.set(p.default)
                slider.pack(side="left", fill="x", expand=True, padx=8)
                value_label.pack(side="left")
                self._sliders[p.key] = (slider, value_label, is_int)
            else:
                continue
            self.vars[p.key] = var

    def values(self) -> dict:
        return {k: v.get() for k, v in self.vars.items()}

    def apply_state(self, state: dict) -> None:
        for key, value in state.items():
            if key not in self.vars:
                continue
            var = self.vars[key]
            if key in self._sliders:
                slider, value_label, is_int = self._sliders[key]
                val = int(value) if is_int else round(float(value), 2)
                var.set(val)
                slider.set(val)
                value_label.configure(text=str(val))
            else:
                var.set(value)
        self.on_change()
