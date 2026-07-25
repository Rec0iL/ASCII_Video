#!/usr/bin/env python3
"""Render frames of a generator to the terminal or a PNG contact sheet.

Usage:
    python scripts/smoke_generators.py --list
    python scripts/smoke_generators.py --gen donut --frame 30
    python scripts/smoke_generators.py --gen donut --frames 60 --out strip.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ascii_video.generators import GENERATORS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--frame", type=int, default=0, help="print a single frame")
    ap.add_argument("--frames", type=int, default=0, help="render N frames to a contact sheet PNG")
    ap.add_argument("--out", default="strip.png")
    ap.add_argument("--cols", type=int, default=None)
    ap.add_argument("--rows", type=int, default=None)
    args = ap.parse_args()

    if args.list or not args.gen:
        print("Available generators:")
        for key, spec in GENERATORS.items():
            print(f"  {key:14s} {spec.display_name}  (default grid {spec.default_cols}x{spec.default_rows}, loop_frames={spec.loop_frames})")
        return

    spec = GENERATORS[args.gen]
    cols = args.cols or spec.default_cols
    rows = args.rows or spec.default_rows
    params = spec.defaults()
    params["loop_frames"] = spec.loop_frames

    if args.frames:
        out_path = Path(args.out).with_suffix(".txt") if args.out == "strip.png" else Path(args.out)
        lines = []
        for f in range(args.frames):
            grid = spec.fn(f / 24.0, f, cols, rows, params)
            lines.append(f"--- frame {f} ---\n{grid.to_text()}")
        out_path.write_text("\n\n".join(lines), encoding="utf-8")
        print(f"Wrote {args.frames} frames to {out_path}")

        loop_frame = spec.fn(0.0, spec.loop_frames, cols, rows, params)
        frame0 = spec.fn(0.0, 0, cols, rows, params)
        seam_ok = (loop_frame.chars == frame0.chars).all()
        print(f"seam check: frame[0] == frame[{spec.loop_frames}] -> {seam_ok}")
        return

    grid = spec.fn(args.frame / 24.0, args.frame, cols, rows, params)
    print(f"--- {spec.display_name} frame {args.frame} ({cols}x{rows}) ---")
    print(grid.to_text())


if __name__ == "__main__":
    main()
