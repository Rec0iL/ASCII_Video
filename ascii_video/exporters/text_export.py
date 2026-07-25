"""Plain text frame dump."""
from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Callable

from .base import FrameStream


def export(
    frames: FrameStream,
    out_path: Path,
    options: dict,
    progress_cb: Callable[[int, int], None] | None = None,
    cancel_event: Event | None = None,
) -> None:
    out_path = Path(out_path)
    total = options.get("total_frames", 0)
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (delay_ms, grid) in enumerate(frames):
            if cancel_event is not None and cancel_event.is_set():
                break
            f.write(f"# frame {i} delay_ms={delay_ms}\n")
            f.write(grid.to_text())
            f.write("\n\n")
            if progress_cb is not None:
                progress_cb(i + 1, total)
