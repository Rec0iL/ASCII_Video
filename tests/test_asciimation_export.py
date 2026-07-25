import json
import re

import numpy as np

from ascii_video.core.grid import FrameGrid
from ascii_video.exporters import asciimation_export

ESC = "\x1b"
_ANSI_RE = re.compile(re.escape(ESC) + r"\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _grid(rows_text: list[str]) -> FrameGrid:
    import numpy as np

    cols = len(rows_text[0])
    chars = np.array([list(r) for r in rows_text], dtype="<U1")
    return FrameGrid(cols=cols, rows=len(rows_text), chars=chars)


def test_asciimation_export_shape_matches_contract(tmp_path):
    frames = [
        (100, _grid(["ab", "cd"])),
        (100, _grid(["ef", "gh"])),
    ]
    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter(frames), out_path, {"name": "Test Anim", "total_frames": 2})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["name"] == "Test Anim"
    assert payload["frames"] == [[100, "ab\ncd"], [100, "ef\ngh"]]


def test_asciimation_export_sets_tick_ms_to_one_by_default(tmp_path):
    # Our delay values are already real per-frame milliseconds (computed
    # upstream from the export fps), not abstract "ticks" -- tickMs must be 1
    # or the sibling app's default 66.67ms/tick would multiply every delay
    # by ~67x and make every export play back at the wrong speed.
    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter([(83, _grid(["ab"]))]), out_path, {"name": "Tick", "total_frames": 1})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["tickMs"] == 1
    assert payload["frames"][0][0] == 83


def test_asciimation_export_rejects_empty_name(tmp_path):
    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter([(50, _grid(["a"]))]), out_path, {"name": "", "total_frames": 1})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["name"]  # must be non-empty -- an empty name gets the file silently skipped


def test_asciimation_export_never_emits_a_non_positive_delay(tmp_path):
    # A single bad delay (0/None/NaN) breaks the whole animation's playback
    # timer on the QML side, not just that one frame -- every delay must
    # come out as a real positive number no matter what a caller hands us.
    frames = [(0, _grid(["a"])), (None, _grid(["b"])), (float("nan"), _grid(["c"])), (-5, _grid(["d"]))]
    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter(frames), out_path, {"name": "Bad Delays", "total_frames": 4})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    for delay, _ in payload["frames"]:
        assert isinstance(delay, (int, float)) and delay > 0


def test_asciimation_export_pads_short_lines(tmp_path):
    # A frame narrower than the canvas established by the first frame must
    # be ljust-padded, matching the sibling project's starwars.txt loader.
    import numpy as np

    wide = FrameGrid(cols=4, rows=1, chars=np.array([list("abcd")], dtype="<U1"))
    narrow = FrameGrid(cols=4, rows=1, chars=np.array([list("xy  ")], dtype="<U1"))
    frames = [(50, wide), (50, narrow)]

    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter(frames), out_path, {"name": "Pad Test", "total_frames": 2})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    for delay, text in payload["frames"]:
        for line in text.split("\n"):
            assert len(line) == 4


def test_asciimation_export_progress_and_cancel(tmp_path):
    import numpy as np
    from threading import Event

    frames = [(50, FrameGrid(cols=1, rows=1, chars=np.array([["#"]], dtype="<U1")))] * 5
    calls = []
    cancel = Event()

    def progress_cb(done, total):
        calls.append((done, total))
        if done == 2:
            cancel.set()

    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter(frames), out_path, {"name": "X", "total_frames": 5}, progress_cb, cancel)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload["frames"]) == 2
    assert calls == [(1, 5), (2, 5)]


def test_asciimation_export_monochrome_has_no_ansi_codes(tmp_path):
    grid = _grid(["ab", "cd"])
    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter([(100, grid)]), out_path, {"name": "Mono", "total_frames": 1})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    text = payload["frames"][0][1]
    assert ESC + "[" not in text
    assert text == "ab\ncd"


def test_asciimation_export_color_embeds_truecolor_ansi_codes(tmp_path):
    # Matches the sibling ASCIImation project's ansi.js parser: it looks for
    # ESC + "[" (hasAnsiCodes) and, when found, only understands foreground
    # 38;2;R;G;B (plus 16/256-color and reset) -- so colored grids must be
    # exported using exactly that truecolor escape shape.
    chars = np.array([["a", "b"]], dtype="<U1")
    colors = np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8)
    grid = FrameGrid(cols=2, rows=1, chars=chars, colors=colors)

    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter([(80, grid)]), out_path, {"name": "Color", "total_frames": 1})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    text = payload["frames"][0][1]

    assert ESC + "[" in text  # what the QML side's hasAnsiCodes() checks for
    assert "\x1b[38;2;255;0;0m" in text
    assert "\x1b[38;2;0;255;0m" in text
    # Stripping every SGR code back out must reproduce the plain characters,
    # so alignment/content in the wallpaper's canvas is unaffected by color.
    assert _strip_ansi(text) == "ab"


def test_asciimation_export_color_frames_keep_canvas_width(tmp_path):
    # Multiple colored frames sharing one export run must all decode back to
    # the same visible width, matching the fixed-canvas contract.
    chars = np.array([["x", "y", "z"]], dtype="<U1")
    colors = np.array([[[10, 20, 30], [10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    grid1 = FrameGrid(cols=3, rows=1, chars=chars, colors=colors)
    grid2 = FrameGrid(cols=3, rows=1, chars=chars, colors=colors)

    out_path = tmp_path / "anim.json"
    asciimation_export.export(iter([(80, grid1), (80, grid2)]), out_path, {"name": "W", "total_frames": 2})

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    for _, text in payload["frames"]:
        assert len(_strip_ansi(text)) == 3
