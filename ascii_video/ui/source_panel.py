"""Video file picker + generator picker, with drag-and-drop import."""
from __future__ import annotations

import re
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from ascii_video.generators import GENERATORS

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".gif"}


def _parse_dnd_paths(data: str) -> list[str]:
    """tkinterdnd2 wraps paths containing spaces in {}; multiple files are
    space-separated otherwise."""
    return [m.strip("{}") for m in re.findall(r"\{[^}]*\}|\S+", data)]


class SourcePanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_video_selected: Callable[[str], None],
        on_generator_selected: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_video_selected = on_video_selected
        self.on_generator_selected = on_generator_selected
        self._gen_keys = list(GENERATORS.keys())
        gen_names = [GENERATORS[k].display_name for k in self._gen_keys]

        video_row = ctk.CTkFrame(self, fg_color="transparent")
        video_row.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(video_row, text="Import Video...", command=self._browse_video).pack(side="left")
        self.video_label = ctk.CTkLabel(video_row, text="No video loaded (or drag a video file here)")
        self.video_label.pack(side="left", padx=8)

        self._enable_drag_and_drop()

        gen_row = ctk.CTkFrame(self, fg_color="transparent")
        gen_row.pack(fill="x")
        ctk.CTkLabel(gen_row, text="Or generate a pattern:").pack(side="left")
        self.gen_var = ctk.StringVar(value=gen_names[0] if gen_names else "")
        self.gen_menu = ctk.CTkOptionMenu(
            gen_row, values=gen_names, variable=self.gen_var, command=self._on_gen_change
        )
        self.gen_menu.pack(side="left", padx=8)

    def _browse_video(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")]
        )
        if path:
            self.video_label.configure(text=Path(path).name)
            self.on_video_selected(path)

    def _on_gen_change(self, display_name: str) -> None:
        names = [GENERATORS[k].display_name for k in self._gen_keys]
        idx = names.index(display_name)
        self.on_generator_selected(self._gen_keys[idx])

    def _enable_drag_and_drop(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass  # tkdnd not available at the Tk level; file-dialog import still works

    def _on_drop(self, event) -> None:
        paths = _parse_dnd_paths(event.data)
        for path in paths:
            if Path(path).suffix.lower() in VIDEO_EXTENSIONS:
                self.video_label.configure(text=Path(path).name)
                self.on_video_selected(path)
                return
