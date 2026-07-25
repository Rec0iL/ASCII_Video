"""Export dialog: format selection, options, progress bar + cancel.

Runs the chosen exporter on a background thread so the UI stays responsive;
progress/cancel flow through a threading.Event and a progress_cb marshaled
back to the Tk main thread via .after().
"""
from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from ascii_video.exporters import ansi_export, asciimation_export, text_export, video_export

FORMAT_CHOICES: dict[str, tuple[str, str]] = {
    "GIF (no ffmpeg needed)": ("gif", ".gif"),
    "MP4 video": ("mp4", ".mp4"),
    "Plain text dump": ("text", ".txt"),
    "ANSI terminal player": ("ansi", ".py"),
    "ASCIImation JSON": ("asciimation", ".json"),
}

_EXPORTERS = {
    "gif": video_export.export,
    "mp4": video_export.export,
    "text": text_export.export,
    "ansi": ansi_export.export,
    "asciimation": asciimation_export.export,
}


class ExportDialog(ctk.CTkToplevel):
    def __init__(self, master, frame_source: Callable[[int], tuple], **kwargs):
        """frame_source(fps) -> (frames_iterable, total_frames, default_name, audio_source_path_or_None)"""
        super().__init__(master, **kwargs)
        self.title("Export")
        self.geometry("440x300")
        self.frame_source = frame_source
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None

        self.format_var = ctk.StringVar(value=list(FORMAT_CHOICES.keys())[0])
        ctk.CTkLabel(self, text="Export format").pack(anchor="w", padx=12, pady=(12, 0))
        ctk.CTkOptionMenu(
            self, values=list(FORMAT_CHOICES.keys()), variable=self.format_var, command=self._on_format_change
        ).pack(fill="x", padx=12)

        self.fps_var = ctk.IntVar(value=12)
        self.fps_row = ctk.CTkFrame(self, fg_color="transparent")
        self.fps_row.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(self.fps_row, text="Export FPS", width=90, anchor="w").pack(side="left")
        self.fps_value_label = ctk.CTkLabel(self.fps_row, text=str(self.fps_var.get()), width=30)
        ctk.CTkSlider(self.fps_row, from_=1, to=30, command=self._on_fps_slide).pack(
            side="left", fill="x", expand=True, padx=8
        )
        self.fps_value_label.pack(side="left")

        self.audio_var = ctk.BooleanVar(value=True)
        self.audio_switch = ctk.CTkSwitch(self, text="Keep original audio (MP4 only)", variable=self.audio_var)
        self.audio_switch.pack(anchor="w", padx=12, pady=(10, 0))

        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=12, pady=(18, 4))
        self.status_label = ctk.CTkLabel(self, text="", anchor="w")
        self.status_label.pack(fill="x", padx=12)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=12, side="bottom")
        self.export_button = ctk.CTkButton(btn_row, text="Export...", command=self._start_export)
        self.export_button.pack(side="left")
        self.cancel_button = ctk.CTkButton(btn_row, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)

        self._on_format_change(self.format_var.get())

    def _on_fps_slide(self, v: str) -> None:
        val = int(float(v))
        self.fps_var.set(val)
        self.fps_value_label.configure(text=str(val))

    def _on_format_change(self, label: str) -> None:
        kind, _ = FORMAT_CHOICES[label]
        needs_fps = kind in ("gif", "mp4", "ansi", "asciimation")
        for w in self.fps_row.winfo_children():
            w.configure(state="normal" if needs_fps else "disabled")
        self.audio_switch.configure(state="normal" if kind == "mp4" else "disabled")

    def _start_export(self) -> None:
        label = self.format_var.get()
        kind, ext = FORMAT_CHOICES[label]

        out_path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"export{ext}")
        if not out_path:
            return
        out_path = Path(out_path)

        fps = self.fps_var.get()
        frames, total, default_name, audio_source = self.frame_source(fps)

        options = {
            "total_frames": total,
            "name": out_path.stem or default_name,
            "fps": fps,
            "format": kind,
        }
        if kind == "mp4" and self.audio_var.get() and audio_source:
            options["audio_source_path"] = audio_source

        self._cancel_event = threading.Event()
        self.export_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.set(0)
        self.status_label.configure(text="Exporting...")

        def progress_cb(done: int, tot: int) -> None:
            self.after(0, lambda: self._update_progress(done, tot))

        def run() -> None:
            try:
                _EXPORTERS[kind](frames, out_path, options, progress_cb, self._cancel_event)
                cancelled = self._cancel_event.is_set()
                self.after(0, lambda: self._finish(success=True, cancelled=cancelled))
            except Exception as exc:  # noqa: BLE001 -- surfaced to the user, not swallowed
                self.after(0, lambda exc=exc: self._finish(success=False, error=str(exc)))

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def _update_progress(self, done: int, total: int) -> None:
        if total:
            self.progress.set(done / total)
        self.status_label.configure(text=f"{done} / {total}")

    def _cancel(self) -> None:
        self._cancel_event.set()
        self.status_label.configure(text="Cancelling...")

    def _finish(self, success: bool, cancelled: bool = False, error: str | None = None) -> None:
        self.export_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        if not success:
            self.status_label.configure(text=f"Error: {error}")
        elif cancelled:
            self.status_label.configure(text="Cancelled.")
        else:
            self.progress.set(1)
            self.status_label.configure(text="Done.")
