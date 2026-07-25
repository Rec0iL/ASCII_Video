"""Common exporter shape.

Every exporter is a plain function:
    export(frames, out_path, options, progress_cb=None, cancel_event=None)

frames: Iterable[(delay_ms: int, FrameGrid)]
options: dict, exporter-specific (fps, name, format, audio_source_path, ...)
progress_cb: called as progress_cb(done, total) from the exporting thread
cancel_event: threading.Event; exporters check it between frames and stop early
"""
from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Callable, Iterable, Protocol

from ascii_video.core.grid import FrameGrid

ProgressCallback = Callable[[int, int], None]
FrameStream = Iterable[tuple[int, FrameGrid]]


class ExportFn(Protocol):
    def __call__(
        self,
        frames: FrameStream,
        out_path: Path,
        options: dict,
        progress_cb: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> None: ...
