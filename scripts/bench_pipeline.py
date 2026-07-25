#!/usr/bin/env python3
"""CLI perf/correctness harness for the core pipeline, no UI needed.

Usage:
    python scripts/bench_pipeline.py video.mp4 --cols 80 --print-frame 10
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ascii_video.core.pipeline import PipelineParams, compute_rows, render_frame
from ascii_video.core.video_source import VideoSource

# Module-level so it's picklable for ProcessPoolExecutor.
_worker_params: PipelineParams | None = None
_worker_cols: int = 0
_worker_rows: int = 0
_worker_path: str = ""


def _pool_init(path: str, cols: int, rows: int, params: PipelineParams) -> None:
    global _worker_params, _worker_cols, _worker_rows, _worker_path
    _worker_params = params
    _worker_cols = cols
    _worker_rows = rows
    _worker_path = path


def _pool_render(index: int):
    src = VideoSource(_worker_path)
    frame = src.get_frame(index)
    grid = render_frame(frame, _worker_cols, _worker_rows, _worker_params)
    src.close()
    return grid.to_text()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--cols", type=int, default=80)
    ap.add_argument("--print-frame", type=int, default=0)
    ap.add_argument("--bench-frames", type=int, default=30)
    ap.add_argument("--color", action="store_true")
    ap.add_argument("--dither", action="store_true")
    ap.add_argument("--edge-threshold", type=float, default=0.35)
    args = ap.parse_args()

    src = VideoSource(args.video)
    rows = compute_rows(src.width, src.height, args.cols)
    params = PipelineParams(edge_threshold=args.edge_threshold, color=args.color, dither=args.dither)

    print(f"video: {args.video}")
    print(f"source: {src.width}x{src.height} @ {src.fps:.2f}fps, {src.frame_count} frames, has_audio={src.has_audio()}")
    print(f"grid: {args.cols}x{rows}")

    frame = src.get_frame(args.print_frame)
    grid = render_frame(frame, args.cols, rows, params)
    print(f"\n--- frame {args.print_frame} ---")
    print(grid.to_text())
    print("--- end frame ---\n")

    n = min(args.bench_frames, src.frame_count)

    t0 = time.perf_counter()
    for i in range(n):
        f = src.get_frame(i)
        render_frame(f, args.cols, rows, params)
    t1 = time.perf_counter()
    single_ms = (t1 - t0) / n * 1000
    print(f"single-process: {single_ms:.2f} ms/frame over {n} frames")

    t0 = time.perf_counter()
    with ProcessPoolExecutor(initializer=_pool_init, initargs=(args.video, args.cols, rows, params)) as pool:
        list(pool.map(_pool_render, range(n)))
    t1 = time.perf_counter()
    pool_ms = (t1 - t0) / n * 1000
    print(f"process-pool:   {pool_ms:.2f} ms/frame over {n} frames (wall-clock incl. pool overhead)")

    src.close()


if __name__ == "__main__":
    main()
