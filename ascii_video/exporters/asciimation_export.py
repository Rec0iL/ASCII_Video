"""Export to the sibling ASCIImation project's animation format:
{"name": str, "tickMs": number, "frames": [[delay, frame_text], ...]},
frame_text being each frame's rows joined with "\\n".

Schema requirements (per that project's loader):
- name must be non-empty, or the whole file is silently skipped.
- frames must be non-empty; each entry's delay must be a real positive
  number -- a bad value (0/None/NaN) breaks that animation's playback timer
  entirely, not just the one frame.
- tickMs is how many ms one delay unit represents (default 66.67, the
  classic 15fps asciimation tick). We already compute a real per-frame
  duration in milliseconds upstream (main_window's fps-based delay_ms), so
  we set tickMs=1 and pass that ms value straight through as delay, rather
  than making the caller reverse-engineer 66.67ms ticks.
- Lines must use bare "\\n" (no "\\r"), padded to a consistent width per
  frame and across the whole animation -- the renderer sizes its text box to
  each frame's longest line and left-aligns within it, so a narrower frame
  visually drifts/recenters otherwise.

That project's QML renderer (org.kde.plasma.starwars/contents/ui/code/ansi.js
+ main.qml) auto-detects real ANSI SGR escape codes in frame_text via
Ansi.hasAnsiCodes() and, if present, renders per-character truecolor via
Ansi.ansiToHtml() instead of the single global phosphor tint. It only honors
foreground codes: 16-color (30-37/90-97), 256-color (38;5;N) and 24-bit
truecolor (38;2;R;G;B) -- so for colored FrameGrids we embed 38;2;R;G;B runs
(matching ansi_export.grid_to_ansi's row-run-length-grouped renderer exactly).
Monochrome grids are still emitted as plain text with no escape codes at all,
so they keep rendering via the classic phosphor-tint path unchanged.

The user drops the resulting JSON into org.kde.plasma.starwars/contents/animations/
-- this exporter never touches that repo directly.
"""
from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from threading import Event
from typing import Callable

from .ansi_export import grid_to_ansi
from .base import FrameStream

DEFAULT_TICK_MS = 1
FALLBACK_DELAY = 1  # used only if a caller ever hands us a bad delay


def export(
    frames: FrameStream,
    out_path: Path,
    options: dict,
    progress_cb: Callable[[int, int], None] | None = None,
    cancel_event: Event | None = None,
) -> None:
    out_path = Path(out_path)
    name = options.get("name") or "Untitled"
    tick_ms = options.get("tick_ms", DEFAULT_TICK_MS)
    total = options.get("total_frames", 0)

    out_frames = []
    canvas_width = None
    for i, (delay_ms, grid) in enumerate(frames):
        if cancel_event is not None and cancel_event.is_set():
            break
        if canvas_width is None:
            canvas_width = grid.cols

        # Guaranteed real positive number: a null/zero/NaN delay breaks the
        # whole animation's playback timer on the QML side, not just this frame.
        delay = delay_ms if isinstance(delay_ms, Real) and delay_ms > 0 else FALLBACK_DELAY

        if grid.colors is not None:
            # grid_to_ansi already walks exactly grid.cols characters per row
            # (a fixed-size array), so it's already canvas_width wide -- no
            # separate ljust pass here, since padding *inside* an escape-coded
            # line would have to skip over escape bytes to land in the right
            # place, and every frame in one export run shares the same grid
            # size anyway (there is nothing to pad against in practice).
            text = grid_to_ansi(grid)
        else:
            # Structural padding safety net: every source grid should already
            # be exactly grid.cols wide (it's a fixed-size array), but ljust
            # guards against a stray mismatched frame the way the sibling
            # project's own legacy starwars.txt loader does.
            lines = ["".join(row).ljust(canvas_width) for row in grid.chars]
            text = "\n".join(lines)

        out_frames.append([delay, text])
        if progress_cb is not None:
            progress_cb(i + 1, total)

    payload = {"name": name, "tickMs": tick_ms, "frames": out_frames}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
