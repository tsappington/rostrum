"""Render Ted's captured handwriting at page scale — the fair test.

The capture tool's thin preview at canvas size is the least flattering
rendering possible. This puts the starred "3 × 4 = 12" take through the
real pipeline: smoothed, pressure-from-speed ink, scaled ~9x down onto
the actual Do Now blank, next to the synthetic take for comparison.

  python -m tools.spike_capture still     # comparison PNG
  python -m tools.spike_capture video     # his take writing itself
"""

from __future__ import annotations

import sys
import time

from PIL import Image, ImageDraw

from rostrum import capture
from rostrum.render import Rostrum, write_video
from tools.spike_ink import CAP_PT, ORIGIN, REGION, build as build_synthetic

DATA = "assets/strokes/capture_ted_v2.json"


def build_captured(t0: float = 0.8):
    data = capture.load(DATA)
    w = capture.take_width_pt(data, "eq", CAP_PT)
    print(f"captured eq take: {w:.1f}pt wide on a 164pt blank")
    return capture.to_timed(data, "eq", ORIGIN, CAP_PT, t0=t0)


def still_pair() -> None:
    """Synthetic (top) vs captured (bottom), same page region."""
    tiles = []
    for label, timed in (("synthetic strokes", build_synthetic()),
                         ("your hand, page scale", build_captured())):
        cam = Rostrum(0, REGION, (1920, 1080))
        end = max(pt.t for s in timed for pt in s)
        cam.ink.draw_until(timed, end + 1)
        # crop the equation row band out of the frame for a tight stack
        frame = cam.frame()
        band = frame.crop((0, 240, 1920, 560))
        d = ImageDraw.Draw(band)
        d.text((24, 16), label, fill=(56, 70, 82))
        tiles.append(band)
    out = Image.new("RGB", (1920, sum(t.height for t in tiles)))
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.height
    out.save("out/capture_vs_synthetic.png")
    print("out/capture_vs_synthetic.png")


def video() -> None:
    timed = build_captured()
    end = max(pt.t for s in timed for pt in s)
    cam = Rostrum(0, REGION, (1920, 1080))
    fps, total = 60, end + 1.4
    n = int(total * fps)
    t_start = time.time()

    def frames():
        for i in range(n):
            cam.ink.draw_until(timed, i / fps)
            yield cam.frame()

    path = write_video("out/spike_capture.mp4", frames(), fps=fps)
    print(f"{path}  {total:.1f}s clip, rendered in {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    (still_pair if (sys.argv[1:] or ["still"])[0] == "still" else video)()
