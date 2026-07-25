"""Rendered video export (GIF via Pillow, no ffmpeg needed; MP4 via system ffmpeg)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import Event
from typing import Callable

from ascii_video.core.font_render import GlyphAtlas

from .base import FrameStream


def export(
    frames: FrameStream,
    out_path: Path,
    options: dict,
    progress_cb: Callable[[int, int], None] | None = None,
    cancel_event: Event | None = None,
) -> None:
    out_path = Path(out_path)
    fmt = options.get("format", "gif")  # "gif" | "mp4"
    fps = options.get("fps", 12)
    total = options.get("total_frames", 0)
    atlas: GlyphAtlas = options.get("glyph_atlas") or GlyphAtlas(font_size=options.get("font_size", 16))

    if fmt == "gif":
        _export_gif(frames, out_path, atlas, fps, total, progress_cb, cancel_event)
    elif fmt == "mp4":
        _export_mp4(frames, out_path, atlas, fps, total, options.get("audio_source_path"), progress_cb, cancel_event)
    else:
        raise ValueError(f"Unknown video export format: {fmt}")


def _export_gif(frames, out_path, atlas, fps, total, progress_cb, cancel_event) -> None:
    images = []
    for i, (delay_ms, grid) in enumerate(frames):
        if cancel_event is not None and cancel_event.is_set():
            return
        images.append(atlas.render(grid))
        if progress_cb is not None:
            progress_cb(i + 1, total)

    if not images:
        raise ValueError("No frames to export")

    duration_ms = int(1000 / fps)
    images[0].save(out_path, save_all=True, append_images=images[1:], duration=duration_ms, loop=0)


def _export_mp4(frames, out_path, atlas, fps, total, audio_source, progress_cb, cancel_event) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH. MP4 export requires system ffmpeg; GIF export does not.")

    with tempfile.TemporaryDirectory(prefix="ascii_video_export_") as tmpdir:
        tmp = Path(tmpdir)
        count = 0
        for i, (delay_ms, grid) in enumerate(frames):
            if cancel_event is not None and cancel_event.is_set():
                return
            img = atlas.render(grid)
            img.save(tmp / f"frame_{i:06d}.png")
            count += 1
            if progress_cb is not None:
                progress_cb(i + 1, total)

        if count == 0:
            raise ValueError("No frames to export")

        cmd = [ffmpeg, "-y", "-framerate", str(fps), "-i", str(tmp / "frame_%06d.png")]
        if audio_source:
            cmd += ["-i", str(audio_source), "-map", "0:v", "-map", "1:a", "-shortest"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")
