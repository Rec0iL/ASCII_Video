"""CTk root window: wires source selection, parameter controls, and playback
to the live preview. render_frame()/generator .fn() are the single source of
truth for both video-scrub and generator-preview rendering."""
from __future__ import annotations

import threading
from pathlib import Path

import customtkinter as ctk

from ascii_video.core.font_render import GlyphAtlas
from ascii_video.core.grid import FrameGrid
from ascii_video.core.pipeline import PipelineParams, compute_rows, render_frame
from ascii_video.core.video_source import VideoSource
from ascii_video.generators import GENERATORS

from . import presets
from .controls_panel import GeneratorControlsPanel, VideoControlsPanel
from .export_dialog import ExportDialog
from .playback_bar import PlaybackBar
from .prerender_dialog import PrerenderDialog
from .preview_canvas import PreviewCanvas
from .source_panel import SourcePanel

PLAY_FPS_CAP = 15          # our own redraw-tick rate cap; speed is achieved by
                            # varying step size / interval around this, not by
                            # exceeding it (Tk redraw cost stays bounded)
DEBOUNCE_MS = 30            # quick single-frame feedback while dragging a control
PRERENDER_DEBOUNCE_MS = 700  # settle time before rebuilding the full frame cache

try:
    from tkinterdnd2 import TkinterDnD

    _BASE_CLASSES = (ctk.CTk, TkinterDnD.DnDWrapper)
except ImportError:
    _BASE_CLASSES = (ctk.CTk,)


class MainWindow(*_BASE_CLASSES):
    def __init__(self):
        super().__init__()
        if len(_BASE_CLASSES) > 1:
            # Required once, before any child widget calls drop_target_register,
            # so the Tk interpreter has the tkdnd extension loaded.
            self.TkdndVersion = TkinterDnD._require(self)

        self.title("ASCII Video")
        self.geometry("1250x800")

        self.glyph_atlas = GlyphAtlas(font_size=12)

        self.video_source: VideoSource | None = None
        self.video_frame_idx = 0
        self.generator_key: str | None = None
        self.generator_frame_idx = 0

        self._playing = False
        self._play_after_id: str | None = None
        self._debounce_after_id: str | None = None
        self._show_original = False

        # Frame cache: once populated (by a background prerender pass), Play
        # and scrubbing read pre-rendered FrameGrids instead of running the
        # pipeline live every tick. cache_ready flips False the instant a
        # param changes and only flips True again once a matching prerender
        # finishes, so a stale cache is never displayed.
        self._frame_cache: dict[int, FrameGrid] = {}
        self._cache_ready = False
        self._cache_generation = 0
        self._prerender_after_id: str | None = None
        self._prerender_dialog: PrerenderDialog | None = None
        self._prerender_cancel_event: threading.Event | None = None

        self._build_layout()

    # -- layout -----------------------------------------------------------
    def _build_layout(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 0))
        self.source_panel = SourcePanel(
            top, on_video_selected=self._load_video, on_generator_selected=self._load_generator
        )
        self.source_panel.pack(side="left", fill="x", expand=True)
        self.export_button = ctk.CTkButton(top, text="Export...", command=self._open_export_dialog, width=100)
        self.export_button.pack(side="right", anchor="n", padx=(10, 0))

        self.status_label = ctk.CTkLabel(self, text="Load a video or pick a generator to preview.", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(6, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        controls_container = ctk.CTkFrame(body, width=340)
        controls_container.pack(side="left", fill="y", padx=(0, 10))
        controls_container.pack_propagate(False)

        self.preset_bar = presets.PresetBar(
            controls_container, on_save=self._save_preset, on_load=self._load_preset, on_delete=self._delete_preset
        )
        self.preset_bar.pack(side="bottom", fill="x", pady=(10, 0))

        self.video_controls = VideoControlsPanel(controls_container, on_change=self._schedule_render)
        self.generator_controls = GeneratorControlsPanel(controls_container, on_change=self._schedule_render)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self.preview = PreviewCanvas(right, glyph_atlas=self.glyph_atlas)
        self.preview.pack(fill="both", expand=True)

        self.playback_bar = PlaybackBar(
            right,
            on_scrub=self._on_scrub,
            on_play_toggle=self._on_play_toggle,
            on_before_after=self._on_before_after,
        )
        self.playback_bar.pack(fill="x", pady=(8, 0))
        self.playback_bar.set_before_after_enabled(False)

    # -- source loading -----------------------------------------------------
    def _load_video(self, path: str) -> None:
        self._stop_playback()
        try:
            new_source = VideoSource(path)
        except (FileNotFoundError, ValueError) as exc:
            self.status_label.configure(text=f"Error: {exc}")
            return

        if self.video_source is not None:
            self.video_source.close()
        self.video_source = new_source
        self.generator_key = None
        self.video_frame_idx = 0

        self.generator_controls.pack_forget()
        self.video_controls.pack(fill="both", expand=True)

        self.playback_bar.set_range(self.video_source.frame_count - 1)
        self.playback_bar.set_before_after_enabled(True)
        self._cache_ready = False
        self._render_current()
        self._schedule_prerender(immediate=True)

    def _load_generator(self, key: str) -> None:
        self._stop_playback()
        self.video_source = None
        self.generator_key = key
        self.generator_frame_idx = 0

        self.video_controls.pack_forget()
        self.generator_controls.pack(fill="both", expand=True)
        self.generator_controls.build_for(GENERATORS[key])

        spec = GENERATORS[key]
        self.playback_bar.set_range(spec.loop_frames)
        self.playback_bar.set_before_after_enabled(False)
        self._cache_ready = False
        self._render_current()
        self._schedule_prerender(immediate=True)

    # -- parameter change debounce ------------------------------------------
    def _schedule_render(self) -> None:
        self._cache_ready = False
        if self._debounce_after_id is not None:
            self.after_cancel(self._debounce_after_id)
        self._debounce_after_id = self.after(DEBOUNCE_MS, self._render_current)
        self._schedule_prerender()

    # -- rendering -----------------------------------------------------------
    def _render_current(self) -> None:
        self._debounce_after_id = None
        if self.video_source is not None:
            self._render_video_frame()
        elif self.generator_key is not None:
            self._render_generator_frame()

    def _current_pipeline_params(self) -> PipelineParams:
        vc = self.video_controls
        return PipelineParams(
            edge_threshold=vc.threshold_var.get(),
            ramp=vc.ramp_string(),
            invert=vc.invert_var.get(),
            dither=vc.dither_var.get(),
            color=vc.color_var.get(),
        )

    def _render_video_frame(self) -> None:
        assert self.video_source is not None
        cols = self.video_controls.cols_var.get()
        params = self._current_pipeline_params()
        rows = compute_rows(self.video_source.width, self.video_source.height, cols, params.char_aspect)

        if self._show_original:
            raw_frame = self.video_source.get_frame(self.video_frame_idx)
            self.preview.set_raw_image(raw_frame, target_width=cols * self.glyph_atlas.cell_w)
        elif self._cache_ready and self.video_frame_idx in self._frame_cache:
            self.preview.set_frame_grid(self._frame_cache[self.video_frame_idx])
        else:
            raw_frame = self.video_source.get_frame(self.video_frame_idx)
            grid = render_frame(raw_frame, cols, rows, params)
            self.preview.set_frame_grid(grid)

        self.playback_bar.set_position(self.video_frame_idx, self.video_source.frame_count - 1)
        cache_note = "" if self._show_original else (" [cached]" if self._cache_ready else " [live]")
        self.status_label.configure(
            text=(
                f"Video: {self.video_source.width}x{self.video_source.height} @ "
                f"{self.video_source.fps:.1f}fps, grid {cols}x{rows}, "
                f"frame {self.video_frame_idx}/{self.video_source.frame_count - 1}{cache_note}"
            )
        )

    def _render_generator_frame(self) -> None:
        assert self.generator_key is not None
        spec = GENERATORS[self.generator_key]

        if self._cache_ready and self.generator_frame_idx in self._frame_cache:
            grid = self._frame_cache[self.generator_frame_idx]
        else:
            params = spec.defaults()
            params.update(self.generator_controls.values())
            params["loop_frames"] = spec.loop_frames
            grid = spec.fn(
                self.generator_frame_idx / 24.0, self.generator_frame_idx, spec.default_cols, spec.default_rows, params
            )

        self.preview.set_frame_grid(grid)
        self.playback_bar.set_position(self.generator_frame_idx, spec.loop_frames)
        self.status_label.configure(
            text=f"Generator: {spec.display_name}, frame {self.generator_frame_idx}, loop={spec.loop_frames}"
        )

    # -- playback controls ----------------------------------------------------
    def _on_scrub(self, frame_idx: int) -> None:
        if self.video_source is not None:
            self.video_frame_idx = max(0, min(frame_idx, self.video_source.frame_count - 1))
        elif self.generator_key is not None:
            self.generator_frame_idx = frame_idx
        self._render_current()

    def _on_before_after(self, show_original: bool) -> None:
        self._show_original = show_original
        self._render_current()

    def _on_play_toggle(self, playing: bool) -> None:
        self._playing = playing
        if playing:
            self._play_tick()
        else:
            self._stop_playback()

    def _stop_playback(self) -> None:
        self._playing = False
        if self._play_after_id is not None:
            self.after_cancel(self._play_after_id)
            self._play_after_id = None
        self.playback_bar.set_playing(False)

    def _step_and_interval(self, native_fps: float) -> tuple[int, int]:
        """Given the source's native fps and the user's speed multiplier,
        returns (frames_to_advance, tick_interval_ms). Below PLAY_FPS_CAP we
        slow the tick rate itself (smooth slow motion); above it we skip
        frames per tick instead (redraw cost stays bounded)."""
        speed = self.playback_bar.speed_var.get()
        effective_fps = max(0.05, native_fps * speed)
        if effective_fps <= PLAY_FPS_CAP:
            return 1, max(1, int(1000 / effective_fps))
        step = max(1, round(effective_fps / PLAY_FPS_CAP))
        return step, int(1000 / PLAY_FPS_CAP)

    def _play_tick(self) -> None:
        if not self._playing:
            return

        if self.video_source is not None:
            step, interval_ms = self._step_and_interval(self.video_source.fps)
            self.video_frame_idx += step
            if self.video_frame_idx >= self.video_source.frame_count:
                self.video_frame_idx = 0
        elif self.generator_key is not None:
            step, interval_ms = self._step_and_interval(PLAY_FPS_CAP)
            loop_frames = GENERATORS[self.generator_key].loop_frames
            self.generator_frame_idx = (self.generator_frame_idx + step) % max(1, loop_frames)
        else:
            self._stop_playback()
            return

        self._render_current()
        self._play_after_id = self.after(interval_ms, self._play_tick)

    # -- prerendering (background frame cache) ----------------------------------
    def _schedule_prerender(self, immediate: bool = False) -> None:
        if self._prerender_after_id is not None:
            self.after_cancel(self._prerender_after_id)
            self._prerender_after_id = None
        if immediate:
            self._start_prerender()
        else:
            self._prerender_after_id = self.after(PRERENDER_DEBOUNCE_MS, self._start_prerender)

    def _start_prerender(self) -> None:
        self._prerender_after_id = None
        if self.video_source is not None:
            self._start_video_prerender()
        elif self.generator_key is not None:
            self._start_generator_prerender()

    def _start_video_prerender(self) -> None:
        assert self.video_source is not None
        vs = self.video_source
        cols = self.video_controls.cols_var.get()
        params = self._current_pipeline_params()
        rows = compute_rows(vs.width, vs.height, cols, params.char_aspect)
        total = vs.frame_count
        video_path = vs.path

        self._cache_generation += 1
        generation = self._cache_generation
        self._cache_ready = False

        cancel_event = threading.Event()
        self._prerender_cancel_event = cancel_event
        if self._prerender_dialog is not None:
            self._prerender_dialog.destroy()
        self._prerender_dialog = PrerenderDialog(self, total_frames=total, on_cancel=cancel_event.set)

        def progress_cb(done: int, tot: int) -> None:
            self.after(0, lambda: self._on_prerender_progress(generation, done, tot))

        def run() -> None:
            result: dict[int, FrameGrid] = {}
            src = VideoSource(video_path)
            try:
                for idx in range(total):
                    if cancel_event.is_set():
                        break
                    frame = src.get_frame(idx)
                    result[idx] = render_frame(frame, cols, rows, params)
                    progress_cb(idx + 1, total)
            finally:
                src.close()
            self.after(0, lambda: self._on_prerender_done(generation, result, cancel_event.is_set()))

        threading.Thread(target=run, daemon=True).start()

    def _start_generator_prerender(self) -> None:
        # Generators are cheap (a few hundred frames of closed-form math at
        # most) -- rebuild synchronously rather than spinning up a thread and
        # modal dialog for what's normally a sub-second operation.
        assert self.generator_key is not None
        self._cache_generation += 1
        spec = GENERATORS[self.generator_key]
        params = spec.defaults()
        params.update(self.generator_controls.values())
        params["loop_frames"] = spec.loop_frames

        cache: dict[int, FrameGrid] = {}
        for f in range(spec.loop_frames):
            cache[f] = spec.fn(f / 24.0, f, spec.default_cols, spec.default_rows, params)

        self._frame_cache = cache
        self._cache_ready = True
        self._render_current()

    def _on_prerender_progress(self, generation: int, done: int, total: int) -> None:
        if generation != self._cache_generation or self._prerender_dialog is None:
            return
        self._prerender_dialog.set_progress(done, total)

    def _on_prerender_done(self, generation: int, result: dict, cancelled: bool) -> None:
        if generation != self._cache_generation:
            return
        if self._prerender_dialog is not None:
            self._prerender_dialog.destroy()
            self._prerender_dialog = None
        if not cancelled:
            self._frame_cache = result
            self._cache_ready = True
            self._render_current()

    # -- export ----------------------------------------------------------------
    def _open_export_dialog(self) -> None:
        if self.video_source is None and self.generator_key is None:
            self.status_label.configure(text="Load a video or pick a generator before exporting.")
            return
        self._stop_playback()
        ExportDialog(self, frame_source=self._build_export_frame_source)

    def _build_export_frame_source(self, fps: int):
        """Returns (frames_iterable, total_frames, default_name, audio_source_path)."""
        if self.video_source is not None:
            vs = self.video_source
            cols = self.video_controls.cols_var.get()
            params = self._current_pipeline_params()
            rows = compute_rows(vs.width, vs.height, cols, params.char_aspect)
            step = max(1, round(vs.fps / fps))
            indices = list(range(0, vs.frame_count, step))
            delay_ms = int(1000 / fps)

            def gen():
                for idx in indices:
                    frame = vs.get_frame(idx)
                    yield delay_ms, render_frame(frame, cols, rows, params)

            default_name = Path(vs.path).stem
            audio_source = str(vs.path) if vs.has_audio() else None
            return gen(), len(indices), default_name, audio_source

        if self.generator_key is not None:
            spec = GENERATORS[self.generator_key]
            gen_params = spec.defaults()
            gen_params.update(self.generator_controls.values())
            gen_params["loop_frames"] = spec.loop_frames
            delay_ms = int(1000 / fps)

            def gen():
                for f in range(spec.loop_frames):
                    yield delay_ms, spec.fn(f / fps, f, spec.default_cols, spec.default_rows, gen_params)

            return gen(), spec.loop_frames, spec.key, None

        return iter(()), 0, "export", None

    # -- presets -----------------------------------------------------------------
    def _save_preset(self, name: str) -> None:
        data: dict = {"video": self.video_controls.get_state()}
        if self.generator_key is not None:
            data["generator_key"] = self.generator_key
            data["generator_params"] = self.generator_controls.values()
        presets.save_preset(name, data)
        self.status_label.configure(text=f"Saved preset '{name}'.")

    def _load_preset(self, name: str) -> None:
        try:
            data = presets.load_preset(name)
        except (FileNotFoundError, ValueError, OSError) as exc:
            self.status_label.configure(text=f"Error loading preset '{name}': {exc}")
            return

        if "video" in data:
            self.video_controls.apply_state(data["video"])

        gen_key = data.get("generator_key")
        if gen_key and gen_key in GENERATORS:
            if self.generator_key != gen_key:
                self._load_generator(gen_key)
            if "generator_params" in data:
                self.generator_controls.apply_state(data["generator_params"])

        self.status_label.configure(text=f"Loaded preset '{name}'.")

    def _delete_preset(self, name: str) -> None:
        presets.delete_preset(name)
        self.status_label.configure(text=f"Deleted preset '{name}'.")
