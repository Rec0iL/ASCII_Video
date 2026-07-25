import json

import numpy as np

from ascii_video.core.grid import FrameGrid
from ascii_video.exporters import ansi_export, text_export


def _mono_grid() -> FrameGrid:
    return FrameGrid(cols=2, rows=2, chars=np.array([["a", "b"], ["c", "d"]], dtype="<U1"))


def _color_grid() -> FrameGrid:
    chars = np.array([["a", "b"]], dtype="<U1")
    colors = np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8)
    return FrameGrid(cols=2, rows=1, chars=chars, colors=colors)


def test_text_export_writes_all_frames(tmp_path):
    frames = [(100, _mono_grid()), (100, _mono_grid())]
    out_path = tmp_path / "out.txt"
    text_export.export(iter(frames), out_path, {"total_frames": 2})
    content = out_path.read_text(encoding="utf-8")
    assert content.count("ab\ncd") == 2


def test_grid_to_ansi_monochrome_has_no_color_codes():
    text = ansi_export.grid_to_ansi(_mono_grid())
    assert "\x1b[38;2;" not in text
    assert "ab" in text.replace("\x1b[0m", "")


def test_grid_to_ansi_color_emits_truecolor_codes():
    text = ansi_export.grid_to_ansi(_color_grid())
    assert "\x1b[38;2;255;0;0m" in text
    assert "\x1b[38;2;0;255;0m" in text


def test_grid_to_ansi_space_cells_never_get_a_color_code():
    # A colored cell that's actually a space is invisible either way, so it
    # must not force a color escape -- keeps blank runs/backgrounds cheap and
    # lets them fall back to the renderer's ambient color instead of a flat
    # painted-black rectangle.
    chars = np.array([["a", " ", "b"]], dtype="<U1")
    colors = np.array([[[255, 0, 0], [10, 20, 30], [0, 255, 0]]], dtype=np.uint8)
    grid = FrameGrid(cols=3, rows=1, chars=chars, colors=colors)
    text = ansi_export.grid_to_ansi(grid)
    assert "\x1b[38;2;10;20;30m" not in text


def test_ansi_export_writes_player_script_and_data(tmp_path):
    frames = [(80, _mono_grid())]
    out_path = tmp_path / "player.py"
    ansi_export.export(iter(frames), out_path, {"total_frames": 1})

    assert out_path.exists()
    data_path = out_path.with_suffix(".frames.json")
    assert data_path.exists()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0][0] == 80
    assert "DATA_FILE" in out_path.read_text(encoding="utf-8")
