"""Modal 'preparing preview' dialog shown while the full frame cache is
being (re)built in the background, so Play always reads from a ready cache
instead of live-converting frame by frame."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk


class PrerenderDialog(ctk.CTkToplevel):
    def __init__(self, master, total_frames: int, on_cancel: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.title("Preparing preview")
        self.geometry("380x140")
        self.resizable(False, False)
        self._on_cancel = on_cancel
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        ctk.CTkLabel(self, text="Rendering frames for smooth playback...").pack(padx=16, pady=(20, 8))
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=4)
        self.status_label = ctk.CTkLabel(self, text=f"0 / {total_frames}")
        self.status_label.pack(pady=(0, 10))
        ctk.CTkButton(self, text="Cancel", command=self._cancel, width=90).pack(pady=(0, 10))

        self.transient(master)
        self.grab_set()

    def set_progress(self, done: int, total: int) -> None:
        if total:
            self.progress.set(done / total)
        self.status_label.configure(text=f"{done} / {total}")

    def _cancel(self) -> None:
        self._on_cancel()
