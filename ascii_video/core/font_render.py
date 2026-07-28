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

# Most monospace fonts (DejaVu Sans Mono, Noto Sans Mono, ...) only cover
# Latin -- CJK glyphs (e.g. the half-width katakana matrix_rain uses) fall
# back to a ".notdef" tofu box without a dedicated CJK font.
_CJK_FALLBACK_FONT_PATHS = [
    "/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansMonoCJK-Regular.ttc",
]

# Characters at or above this codepoint route through the CJK fallback font
# instead of the primary one. Chosen above U+2500-259F (box drawing / block
# elements, which the primary font already covers) and below Hiragana/
# Katakana (U+3040+) and half-width Katakana (U+FF66+).
_CJK_THRESHOLD = 0x3000


def _fc_match_path(query: str) -> str | None:
    fc_match = shutil.which("fc-match")
    if not fc_match:
        return None
    try:
        result = subprocess.run(
            [fc_match, "-f", "%{file}", query],
            capture_output=True, text=True, timeout=5,
        )
        path = result.stdout.strip()
        if path and Path(path).exists():
            return path
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def find_monospace_font() -> str | None:
    path = _fc_match_path("monospace")
    if path:
        return path
    for path in _FALLBACK_FONT_PATHS:
        if Path(path).exists():
            return path
    return None


def find_cjk_font() -> str | None:
    # Prefer a known monospace CJK font outright -- fontconfig's "monospace"
    # alias combined with a :charset constraint doesn't reliably resolve to
    # an actual monospace family, so it isn't a good first choice here.
    for path in _CJK_FALLBACK_FONT_PATHS:
        if Path(path).exists():
            return path
    # ":charset=30a2" asks fontconfig for any font that actually covers
    # katakana (U+30A2, "ア"); may resolve to a proportional CJK font.
    return _fc_match_path(":charset=30a2")


class GlyphAtlas:
    def __init__(
        self,
        font_size: int = 16,
        font_path: str | None = None,
        cjk_font_path: str | None = None,
        bg: tuple[int, int, int] = (0, 0, 0),
        default_fg: tuple[int, int, int] = (0, 230, 0),
    ):
        resolved = font_path or find_monospace_font()
        self.font = ImageFont.truetype(resolved, font_size) if resolved else ImageFont.load_default(size=font_size)

        cjk_resolved = cjk_font_path or find_cjk_font()
        self.cjk_font = ImageFont.truetype(cjk_resolved, font_size) if cjk_resolved else None

        bbox = self.font.getbbox("M")
        self.cell_w = max(1, bbox[2] - bbox[0]) + 1
        self.cell_h = max(1, int(font_size * 1.2))
        self.bg = bg
        self.default_fg = default_fg
        self._cache: dict[tuple[str, tuple[int, int, int]], Image.Image] = {}

    def _font_for(self, ch: str) -> ImageFont.ImageFont:
        if self.cjk_font is not None and ord(ch) >= _CJK_THRESHOLD:
            return self.cjk_font
        return self.font

    def _glyph(self, ch: str, fg: tuple[int, int, int]) -> Image.Image:
        key = (ch, fg)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        img = Image.new("RGB", (self.cell_w, self.cell_h), self.bg)
        if ch != " ":
            draw = ImageDraw.Draw(img)
            font = self._font_for(ch)
            # Half-width CJK glyphs are usually a bit narrower than the
            # primary font's advance width -- center them in the cell
            # instead of left-aligning, so they don't look squeezed left.
            if font is self.cjk_font:
                glyph_bbox = font.getbbox(ch)
                glyph_w = glyph_bbox[2] - glyph_bbox[0]
                x_off = max(0, (self.cell_w - glyph_w) // 2) - glyph_bbox[0]
                draw.text((x_off, 0), ch, font=font, fill=fg)
            else:
                draw.text((0, 0), ch, font=font, fill=fg)
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
