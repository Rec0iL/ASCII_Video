"""Live preview widget: one Canvas image blit per frame, not per-cell items."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

from ascii_video.core.font_render import GlyphAtlas
from ascii_video.core.grid import FrameGrid


class PreviewCanvas(ctk.CTkFrame):
    def __init__(self, master, glyph_atlas: GlyphAtlas, **kwargs):
        super().__init__(master, **kwargs)
        self.glyph_atlas = glyph_atlas
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._photo: ImageTk.PhotoImage | None = None
        self._image_id: int | None = None

    def set_frame_grid(self, grid: FrameGrid) -> None:
        self._set_image(self.glyph_atlas.render(grid))

    def set_raw_image(self, bgr_frame, target_width: int) -> None:
        """Display a source video frame (BGR numpy array) directly, for the
        before/after 'show original' toggle."""
        h, w = bgr_frame.shape[:2]
        target_height = max(1, int(h * (target_width / w)))
        pil_img = Image.fromarray(bgr_frame[..., ::-1]).resize((target_width, target_height))
        self._set_image(pil_img)

    def _set_image(self, pil_img: Image.Image) -> None:
        self._photo = ImageTk.PhotoImage(pil_img)
        if self._image_id is None:
            self._image_id = self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.canvas.itemconfig(self._image_id, image=self._photo)
        self.canvas.config(scrollregion=(0, 0, pil_img.width, pil_img.height))
