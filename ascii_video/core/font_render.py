"""Shared monospace glyph rasterizer used by preview_canvas.py and video_export.py.

Pre-renders each (character, color) once into a small cached bitmap, then
blits per grid cell into a full frame -- much cheaper than calling
ImageDraw.text once per character per frame.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .grid import FrameGrid

_FALLBACK_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
    "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/adwaita-mono-fonts/AdwaitaMono-Regular.ttf",
]


def find_monospace_font() -> str | None:
    fc_match = shutil.which("fc-match")
    if fc_match:
        try:
            result = subprocess.run(
                [fc_match, "-f", "%{file}", "monospace"],
                capture_output=True, text=True, timeout=5,
            )
            path = result.stdout.strip()
            if path and Path(path).exists():
                return path
        except (subprocess.SubprocessError, OSError):
            pass
    for path in _FALLBACK_FONT_PATHS:
        if Path(path).exists():
            return path
    return None


class GlyphAtlas:
    def __init__(
        self,
        font_size: int = 16,
        font_path: str | None = None,
        bg: tuple[int, int, int] = (0, 0, 0),
        default_fg: tuple[int, int, int] = (0, 230, 0),
    ):
        resolved = font_path or find_monospace_font()
        self.font = ImageFont.truetype(resolved, font_size) if resolved else ImageFont.load_default(size=font_size)
        bbox = self.font.getbbox("M")
        self.cell_w = max(1, bbox[2] - bbox[0]) + 1
        self.cell_h = max(1, int(font_size * 1.2))
        self.bg = bg
        self.default_fg = default_fg
        self._cache: dict[tuple[str, tuple[int, int, int]], Image.Image] = {}

    def _glyph(self, ch: str, fg: tuple[int, int, int]) -> Image.Image:
        key = (ch, fg)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        img = Image.new("RGB", (self.cell_w, self.cell_h), self.bg)
        if ch != " ":
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), ch, font=self.font, fill=fg)
        self._cache[key] = img
        return img

    def render(self, grid: FrameGrid) -> Image.Image:
        out = Image.new("RGB", (grid.cols * self.cell_w, grid.rows * self.cell_h), self.bg)
        for y in range(grid.rows):
            for x in range(grid.cols):
                ch = str(grid.chars[y, x])
                if ch == " ":
                    continue
                fg = tuple(int(v) for v in grid.colors[y, x]) if grid.colors is not None else self.default_fg
                out.paste(self._glyph(ch, fg), (x * self.cell_w, y * self.cell_h))
        return out
