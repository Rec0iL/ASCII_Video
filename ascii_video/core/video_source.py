"""cv2.VideoCapture wrapper: seek, frame iteration, fps/duration/audio detection."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


class VideoSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Video file not found: {self.path}")
        self._cap = cv2.VideoCapture(str(self.path))
        if not self._cap.isOpened():
            raise ValueError(f"Could not open video: {self.path}")

        self.frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 25.0
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.frame_count / self.fps if self.fps else 0.0
        self._has_audio: bool | None = None

    def get_frame(self, index: int) -> np.ndarray:
        index = max(0, min(index, self.frame_count - 1))
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self._cap.read()
        if not ok:
            raise IOError(f"Failed to read frame {index} from {self.path}")
        return frame

    def iter_frames(self, start: int = 0, end: int | None = None, step: int = 1) -> Iterator[tuple[int, np.ndarray]]:
        end = self.frame_count if end is None else min(end, self.frame_count)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        idx = start
        while idx < end:
            ok, frame = self._cap.read()
            if not ok:
                break
            yield idx, frame
            idx += 1
            if step > 1:
                for _ in range(step - 1):
                    if not self._cap.grab():
                        return
                idx += step - 1

    def has_audio(self) -> bool:
        if self._has_audio is not None:
            return self._has_audio
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            self._has_audio = False
            return False
        try:
            result = subprocess.run(
                [
                    ffprobe, "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=index", "-of", "csv=p=0",
                    str(self.path),
                ],
                capture_output=True, text=True, timeout=10,
            )
            self._has_audio = bool(result.stdout.strip())
        except (subprocess.SubprocessError, OSError):
            self._has_audio = False
        return self._has_audio

    def close(self) -> None:
        self._cap.release()

    def __enter__(self) -> "VideoSource":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
