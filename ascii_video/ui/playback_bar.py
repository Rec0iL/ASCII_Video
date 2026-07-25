"""Scrub slider, play/pause, playback speed, before/after toggle."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

MIN_SPEED = 0.25
MAX_SPEED = 4.0
SPEED_STEP = 0.25


class PlaybackBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_scrub: Callable[[int], None],
        on_play_toggle: Callable[[bool], None],
        on_before_after: Callable[[bool], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_scrub = on_scrub
        self.on_play_toggle = on_play_toggle
        self.on_before_after = on_before_after
        self._playing = False

        scrub_row = ctk.CTkFrame(self, fg_color="transparent")
        scrub_row.pack(fill="x")

        self.play_button = ctk.CTkButton(scrub_row, text="Play", width=70, command=self._toggle_play)
        self.play_button.pack(side="left", padx=(0, 8))

        self.frame_label = ctk.CTkLabel(scrub_row, text="0 / 0", width=90)
        self.frame_label.pack(side="left", padx=(0, 8))

        self.slider = ctk.CTkSlider(scrub_row, from_=0, to=1, command=self._on_slider)
        self.slider.set(0)
        self.slider.pack(side="left", fill="x", expand=True, padx=8)

        self.before_after_var = ctk.BooleanVar(value=False)
        self.before_after_switch = ctk.CTkSwitch(
            scrub_row, text="Show original", variable=self.before_after_var, command=self._on_toggle_before_after
        )
        self.before_after_switch.pack(side="left", padx=(8, 0))

        speed_row = ctk.CTkFrame(self, fg_color="transparent")
        speed_row.pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(speed_row, text="Playback speed", width=110, anchor="w").pack(side="left", padx=(0, 8))
        self.speed_var = ctk.DoubleVar(value=1.0)
        self.speed_label = ctk.CTkLabel(speed_row, text="1.0x", width=50)
        self.speed_slider = ctk.CTkSlider(
            speed_row, from_=MIN_SPEED, to=MAX_SPEED,
            number_of_steps=round((MAX_SPEED - MIN_SPEED) / SPEED_STEP),
            command=self._on_speed_slide,
        )
        self.speed_slider.set(1.0)
        self.speed_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.speed_label.pack(side="left", padx=(0, 8))
        ctk.CTkButton(speed_row, text="Reset", width=60, command=self._reset_speed).pack(side="left")

    def _on_slider(self, v: str) -> None:
        self.on_scrub(int(float(v)))

    def _on_speed_slide(self, v: str) -> None:
        val = round(float(v) / SPEED_STEP) * SPEED_STEP
        self.speed_var.set(val)
        self.speed_label.configure(text=f"{val:g}x")

    def _reset_speed(self) -> None:
        self.speed_var.set(1.0)
        self.speed_slider.set(1.0)
        self.speed_label.configure(text="1.0x")

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        self.play_button.configure(text="Pause" if self._playing else "Play")
        self.on_play_toggle(self._playing)

    def _on_toggle_before_after(self) -> None:
        self.on_before_after(self.before_after_var.get())

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self.play_button.configure(text="Pause" if playing else "Play")

    def set_range(self, max_frame: int) -> None:
        self.slider.configure(from_=0, to=max(1, max_frame))

    def set_position(self, frame_idx: int, max_frame: int) -> None:
        self.slider.set(frame_idx)
        self.frame_label.configure(text=f"{frame_idx} / {max_frame}")

    def set_before_after_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.before_after_switch.configure(state=state)
        if not enabled:
            self.before_after_var.set(False)
